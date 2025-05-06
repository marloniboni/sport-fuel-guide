import os
import streamlit as st
import pandas as pd
import requests
import gpxpy
import folium
from streamlit_folium import st_folium
import altair as alt

# ─────────────────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Sport-Fuel Guide", layout="wide")

# ─────────────────────────────────────────────────────────────────────────────
# 1) Vor-Workout Planung
# ─────────────────────────────────────────────────────────────────────────────
if 'gewicht' not in st.session_state:
    st.warning("Bitte gib zuerst deine Körperdaten auf der Startseite ein.")
    st.stop()
gewicht = st.session_state.gewicht

sportart = st.selectbox("Sportart", ["Laufen", "Radfahren", "Schwimmen"])
mode     = st.radio("Datenquelle wählen", ["GPX-Datei hochladen", "Manuelle Eingabe"])

if mode == "GPX-Datei hochladen":
    uploaded = st.file_uploader("GPX-Datei hochladen", type="gpx")
    if not uploaded:
        st.error("Bitte eine GPX-Datei hochladen.")
        st.stop()
    try:
        gpx          = gpxpy.parse(uploaded.getvalue().decode())
        duration_sec = gpx.get_duration() or 0
        dauer        = duration_sec / 60
        distanz      = (gpx.length_3d() or 0) / 1000
        coords       = [
            (pt.latitude, pt.longitude)
            for tr in gpx.tracks
            for seg in tr.segments
            for pt in seg.points
        ]
    except Exception as e:
        st.error(f"Fehler beim Parsen der GPX-Datei: {e}")
        st.stop()
else:
    dauer   = st.slider("Dauer (Min)", 15, 300, 60)
    distanz = st.number_input("Distanz (km)", 0.0, 100.0, 10.0)
    coords  = []

st.markdown(f"**Dauer:** {dauer:.0f} Min • **Distanz:** {distanz:.2f} km")

faktoren   = {"Laufen": 7, "Radfahren": 5, "Schwimmen": 6}
cal_burn   = faktoren[sportart] * gewicht * (dauer / 60)
fluid_loss = 0.7 * (dauer / 60)

st.session_state['planned_calories'] = cal_burn
st.session_state['fluessigkeit']     = fluid_loss

st.subheader("Deine persönlichen Berechnungen")
st.write(f"Kalorienverbrauch: **{int(cal_burn)} kcal** • Flüssigkeitsverlust: **{fluid_loss:.2f} L**")

eat_int   = st.select_slider("Essen alle (Min)",   [15,20,30,45,60], 30)
drink_int = st.select_slider("Trinken alle (Min)", [10,15,20,30],   15)

events    = sorted(
    set(range(eat_int,   int(dauer)+1, eat_int  )) |
    set(range(drink_int, int(dauer)+1, drink_int))
)
req_cal   = cal_burn / len(events) if events else 0
req_fluid = fluid_loss / len(events) if events else 0

schedule = []
for t in events:
    row = {"Minute": t}
    if t % eat_int   == 0: row["Essen (kcal)"] = round(req_cal,   1)
    if t % drink_int == 0: row["Trinken (L)"]  = round(req_fluid, 3)
    schedule.append(row)

df_schedule = pd.DataFrame(schedule).set_index("Minute")
st.subheader("Dein persönlicher Intake-Plan")
st.table(df_schedule)

# ─────────────────────────────────────────────────────────────────────────────
# 2) Snack-Finder (USDA) mit Accumulativer Liste & Bar-Chart
# ─────────────────────────────────────────────────────────────────────────────
FDC_API_KEY = "XDzSn37cJ5NRjskCXvg2lmlYUYptpq8tT68mPmPP"

@st.cache_data
def search_foods(query: str, limit: int=5):
    r = requests.get(
        "https://api.nal.usda.gov/fdc/v1/foods/search",
        params={'api_key':FDC_API_KEY,'query':query,'pageSize':limit}
    )
    r.raise_for_status()
    return r.json().get("foods", [])

@st.cache_data
def get_food_details(fdc_id: int):
    r = requests.get(
        f"https://api.nal.usda.gov/fdc/v1/food/{fdc_id}",
        params={'api_key':FDC_API_KEY}
    )
    r.raise_for_status()
    return r.json()

if "cart" not in st.session_state:
    st.session_state.cart = []

st.subheader("🍌 Snack-Empfehlungen via USDA")
snack_query = st.text_input("Snack suchen (Schlagwort)", "")

if snack_query:
    foods = search_foods(snack_query, limit=5)
    if not foods:
        st.warning("Keine Produkte gefunden – versuche ein anderes Stichwort.")
    else:
        for food in foods:
            desc = food.get("description", "Unbekannt")
            fdc  = food.get("fdcId")
            details = get_food_details(fdc)

            # robust nutrient parsing
            nut = {}
            for n in details.get("foodNutrients", []):
                if "nutrient" in n and isinstance(n["nutrient"], dict):
                    key = n["nutrient"].get("name"); val = n.get("amount",0)
                elif "nutrientName" in n:
                    key = n.get("nutrientName"); val = n.get("value",0)
                else:
                    continue
                if key:
                    nut[key] = val or 0

            cal100 = nut.get("Energy") or nut.get("Calories") or 0

            servs = details.get("servings",{}).get("serving",[])
            if isinstance(servs, dict): servs=[servs]
            gs = next((s for s in servs if s.get("metricServingUnit")=="g"), servs[0] if servs else {}).get("metricServingAmount",100)
            gram_serv = float(gs)

            cal_serv = cal100 * gram_serv / 100.0

            c1, c2 = st.columns([5,1])
            with c1:
                st.markdown(f"**{desc}** — {gram_serv:.0f} g → **{cal_serv:.0f} kcal**")
            if c2.button("➕", key=f"add_{fdc}"):
                in_cart = [item["fdc"] for item in st.session_state.cart]
                if fdc not in in_cart:
                    st.session_state.cart.append({
                        "fdc": fdc,
                        "description": desc,
                        "grams": gram_serv,
                        "kcal": cal_serv
                    })

    cart = st.session_state.cart
    if cart:
        df_cart = pd.DataFrame(cart)
        df_cart["cum_kcal"] = df_cart["kcal"].cumsum()
        df_cart["step"]     = list(range(1, len(df_cart)+1))

        st.subheader("Deine ausgewählten Snacks")
        st.table(
            df_cart[["step","description","grams","kcal"]]
                   .rename(columns={"step":"#","description":"Snack"})
        )

        df_bar = pd.DataFrame({
            "step":     df_cart["step"],
            "Consumed": df_cart["cum_kcal"],
            "Burned":   df_cart["step"]/len(df_cart)*cal_burn
        }).melt("step", var_name="Type", value_name="kcal")

        st.subheader("Kumulativ: Verbrannte vs. Gegessene kcal")
        bar = (
            alt.Chart(df_bar)
               .mark_bar()
               .encode(
                   x=alt.X("step:O", title="Auswahl-Schritt"),
                   y=alt.Y("kcal:Q", title="kcal"),
                   color="Type:N",
                   column="Type:N",
                   tooltip=["Type","kcal"]
               )
               .properties(width=150, height=300)
        )
        st.altair_chart(bar, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# 3) Gesamt-Verbrauch vs. Intake über Workout-Dauer
# ─────────────────────────────────────────────────────────────────────────────
mins     = list(range(int(dauer)+1))
burned   = [cal_burn/dauer * m for m in mins]
ingested = [req_cal if m in events else 0 for m in mins]

df3 = pd.DataFrame({
    "Minute":       mins,
    "Burned":       burned,
    "Intake(kcal)": ingested
})
df3["Cum Intake"] = df3["Intake(kcal)"].cumsum()
df3["Balance"]    = df3["Burned"] - df3["Cum Intake"]

base2      = alt.Chart(df3).encode(x="Minute:Q")
burn_line2 = base2.mark_line(strokeWidth=2).encode(
    y=alt.Y("Burned:Q", title="kcal verbrannt"), color=alt.value("blue")
)
intake_line= base2.mark_line(strokeDash=[4,2]).encode(
    y=alt.Y("Cum Intake:Q", title="kumulierte kcal"), color=alt.value("orange")
)
balance_ln = base2.mark_line(opacity=0.7).encode(
    y=alt.Y("Balance:Q", title="Netto-Bilanz"), color=alt.value("green")
)

st.subheader("Workout-Verbrauch vs. kumulative Aufnahme & Bilanz")
st.altair_chart(
    alt.layer(burn_line2, intake_line, balance_ln)
       .properties(width=700, height=400),
    use_container_width=True
)

# ─────────────────────────────────────────────────────────────────────────────
# 4) Route Map & GPX-Download
# ─────────────────────────────────────────────────────────────────────────────
if coords:
    m = folium.Map(location=coords[0], zoom_start=13)
    folium.PolyLine(coords, color="blue").add_to(m)
    for t in events:
        idx = min(int(t/dauer*len(coords)), len(coords)-1)
        lat, lon = coords[idx]
        folium.CircleMarker((lat, lon),
                            radius=5,
                            color="red" if t%eat_int==0 else "yellow",
                            fill=True).add_to(m)
    st.subheader("Route & Timing auf der Karte")
    st_folium(m, width=700, height=400)
    st.download_button(
        "GPX herunterladen",
        gpx.to_xml(),
        file_name="route_intake.gpx",
        mime="application/gpx+xml"
    )
