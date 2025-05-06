import streamlit as st
import pandas as pd
import requests
import gpxpy
import folium
from streamlit_folium import st_folium
import altair as alt
from requests_oauthlib import OAuth1Session

# ─────────────────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Sport-Fuel Guide", layout="wide")

# ─────────────────────────────────────────────────────────────────────────────
#— 1) Vor-Workout Planung
# ─────────────────────────────────────────────────────────────────────────────

# Make sure user has entered their weight on the start page
if 'gewicht' not in st.session_state:
    st.warning("Bitte gib zuerst deine Körperdaten auf der Startseite ein.")
    st.stop()

gewicht = st.session_state.gewicht

sportart = st.selectbox("Sportart", ["Laufen", "Radfahren", "Schwimmen"])

mode = st.radio("Datenquelle wählen", ["GPX-Datei hochladen", "Manuelle Eingabe"])
if mode == "GPX-Datei hochladen":
    uploaded = st.file_uploader("GPX-Datei hochladen", type="gpx")
    if not uploaded:
        st.error("Bitte eine GPX-Datei hochladen.")
        st.stop()
    try:
        xml = uploaded.getvalue().decode("utf-8")
        gpx = gpxpy.parse(xml)
        td = gpx.get_duration()
        duration_sec = td.total_seconds() if td else 0
        dauer = duration_sec / 60
        distanz = (gpx.length_3d() or 0) / 1000
        coords = [
            (pt.latitude, pt.longitude)
            for tr in gpx.tracks
            for seg in tr.segments
            for pt in seg.points
        ]
    except Exception as e:
        st.error(f"Fehler beim Parsen der GPX-Datei: {e}")
        st.stop()
else:
    dauer = st.slider("Dauer (Min)", min_value=15, max_value=300, value=60)
    distanz = st.number_input("Distanz (km)", min_value=0.0, max_value=100.0, value=10.0)
    coords = []

st.markdown(f"**Dauer:** {dauer:.0f} Min • **Distanz:** {distanz:.2f} km")

# Compute burn & fluid loss
faktoren = {"Laufen": 7, "Radfahren": 5, "Schwimmen": 6}
cal_burn = faktoren[sportart] * gewicht * (dauer / 60)
fluid_loss = 0.7 * (dauer / 60)

# Save for later pages
st.session_state['planned_calories'] = cal_burn
st.session_state['fluessigkeit'] = fluid_loss

st.subheader("Deine persönlichen Berechnungen")
st.write(f"Kalorienverbrauch: **{int(cal_burn)} kcal** • Flüssigkeitsverlust: **{fluid_loss:.2f} L**")

# Build intake schedule
eat_int = st.select_slider("Essen alle (Min)", [15, 20, 30, 45, 60], value=30)
drink_int = st.select_slider("Trinken alle (Min)", [10, 15, 20, 30], value=15)

events = sorted(
    set(range(eat_int, int(dauer) + 1, eat_int))
    | set(range(drink_int, int(dauer) + 1, drink_int))
)
req_cal = cal_burn / len(events) if events else 0
req_fluid = fluid_loss / len(events) if events else 0

schedule = []
for t in events:
    row = {"Minute": t}
    if t % eat_int == 0:
        row["Essen (kcal)"] = round(req_cal, 2)
    if t % drink_int == 0:
        row["Trinken (L)"] = round(req_fluid, 3)
    schedule.append(row)

df_schedule = pd.DataFrame(schedule).set_index("Minute")

st.subheader("Dein persönlicher Intake-Plan")
st.table(df_schedule)

# ─────────────────────────────────────────────────────────────────────────────
#— 2) Snack-Finder via FatSecret
# ─────────────────────────────────────────────────────────────────────────────

FATSECRET_KEY = "YOUR_CONSUMER_KEY"
FATSECRET_SECRET = "YOUR_CONSUMER_SECRET"
API_URL = "https://platform.fatsecret.com/rest/server.api"

@st.cache_data
def fs_search(query: str, limit: int = 5):
    oauth = OAuth1Session(FATSECRET_KEY, client_secret=FATSECRET_SECRET)
    params = {
        "method": "foods.search",
        "search_expression": query,
        "format": "json",
        "max_results": limit,
    }
    r = oauth.get(API_URL, params=params)
    r.raise_for_status()
    return r.json().get("foods", {}).get("food", [])

@st.cache_data
def fs_get_details(food_id: str):
    oauth = OAuth1Session(FATSECRET_KEY, client_secret=FATSECRET_SECRET)
    params = {"method": "food.get", "food_id": food_id, "format": "json"}
    r = oauth.get(API_URL, params=params)
    r.raise_for_status()
    return r.json().get("food", {})

st.subheader("🍿 Snack-Empfehlungen mit FatSecret")

snack_query = st.text_input("Suchbegriff für Snack", "")
if snack_query:
    products = fs_search(snack_query, limit=5)
    if not products:
        st.warning("Keine Produkte gefunden – versuche ein anderes Stichwort.")
    else:
        # how many kcal per snack-portion?
        req_cal_snack = st.slider("Ziel-Kalorien für Snack", 50, 500, 200)
        for p in products:
            food_id = p["food_id"]
            name = p.get("food_name", "Unbekannt")
            details = fs_get_details(food_id)
            servings = details.get("servings", {}).get("serving", [])
            if isinstance(servings, dict):
                servings = [servings]
            # pick the first gram-based serving
            serv = next(
                (s for s in servings if s.get("metric_serving_unit") == "g"),
                (servings[0] if servings else {}),
            )
            size_g = float(serv.get("metric_serving_amount", 0))
            kcal100 = float(serv.get("calories", 0))
            fat100 = float(serv.get("fat", 0))
            prot100 = float(serv.get("protein", 0))
            carb100 = float(serv.get("carbohydrate", 0))
            sugar100 = float(serv.get("sugar", 0))
            grams_needed = (req_cal_snack * size_g / kcal100) if kcal100 else 0

            col1, col2 = st.columns([1, 2])
            with col1:
                st.image("https://via.placeholder.com/80?text=Snack", width=80)
                st.markdown(f"**{name}**")
                st.markdown(f"{grams_needed:.0f} g → {req_cal_snack} kcal")
            df = pd.DataFrame({
                "Macro": ["Fat", "Protein", "Carb", "Sugar"],
                "Grams": [
                    fat100 * grams_needed / size_g,
                    prot100 * grams_needed / size_g,
                    carb100 * grams_needed / size_g,
                    sugar100 * grams_needed / size_g,
                ],
            })
            chart = (
                alt.Chart(df)
                .mark_bar()
                .encode(
                    x="Macro:N",
                    y="Grams:Q",
                    color="Macro:N",
                    tooltip=["Macro", "Grams"],
                )
                .properties(width=300, height=200)
            )
            with col2:
                st.altair_chart(chart, use_container_width=True)
else:
    st.info("Bitte ein Suchbegriff eingeben, um Snacks zu suchen.")

# ─────────────────────────────────────────────────────────────────────────────
#— 3) Verbrauch vs. Aufnahme-Chart
# ─────────────────────────────────────────────────────────────────────────────

minutes = list(range(int(dauer) + 1))
burned = [cal_burn / dauer * m for m in minutes]
ingested = [req_cal if m in events else 0 for m in minutes]
df2 = pd.DataFrame({
    "Minute": minutes,
    "Burned": burned,
    "Ingested": ingested,
})
df2["Cum Aufnahme"] = df2["Ingested"].cumsum()
df2["Netto"] = df2["Burned"] - df2["Cum Aufnahme"]

base = alt.Chart(df2).encode(x=alt.X("Minute:Q", axis=alt.Axis(title="Minute")))
burn_line = base.mark_line(strokeWidth=2).encode(
    y=alt.Y("Burned:Q", axis=alt.Axis(title="kcal verbrannt")), color=alt.value("blue")
)
eat_line = base.mark_line(strokeDash=[4,2]).encode(
    y=alt.Y("Cum Aufnahme:Q", axis=alt.Axis(title="kcal kumuliert")), color=alt.value("orange")
)
net_line = base.mark_line(opacity=0.7).encode(
    y=alt.Y("Netto:Q", axis=alt.Axis(title="kcal Differenz")), color=alt.value("green")
)
st.subheader("Verbrauch vs. kumulierte Aufnahme & Netto-Bilanz")
st.altair_chart(alt.layer(burn_line, eat_line, net_line).properties(width=700, height=400), use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
#— 4) Route Map & GPX-Download
# ─────────────────────────────────────────────────────────────────────────────
if coords:
    m = folium.Map(location=coords[0], zoom_start=13)
    folium.PolyLine(coords, color="blue").add_to(m)
    for t in events:
        idx = min(int(t / dauer * len(coords)), len(coords) - 1)
        lat, lon = coords[idx]
        color = "red" if t % eat_int == 0 else "yellow"
        folium.CircleMarker((lat, lon), radius=5, color=color, fill=True).add_to(m)
    st.subheader("Route & Timing auf der Karte")
    st_folium(m, width=700, height=400)
    gpx_str = gpx.to_xml()
    st.download_button("GPX herunterladen", gpx_str, file_name="route_intake.gpx", mime="application/gpx+xml")
