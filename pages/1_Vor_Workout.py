import os
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
        duration_sec = gpx.get_duration() or 0
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
#— 2) Snack-Finder via USDA FoodData Central
# ─────────────────────────────────────────────────────────────────────────────
# --- USDA FDC Snack API ---
FDC_API_KEY = "XDzSn37cJ5NRjskCXvg2lmlYUYptpq8tT68mPmPP"
@st.cache_data
def search_foods(query: str, limit: int = 5):
    url = "https://api.nal.usda.gov/fdc/v1/foods/search"
    params = {'api_key': FDC_API_KEY, 'query': query, 'pageSize': limit}
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    return resp.json().get('foods', [])

@st.cache_data
def get_food_details(fdc_id: int):
    url = f"https://api.nal.usda.gov/fdc/v1/food/{fdc_id}"
    params = {'api_key': FDC_API_KEY}
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    return resp.json()

# Berechne Kalorien pro Snack-Ereignis einmalig
req_cal = cal_burn / len(events) if events else 0

# Nutritionix für Bilder
NX_APP_ID  = os.getenv("NUTRITIONIX_APP_ID", "9810d473")
NX_APP_KEY = os.getenv("NUTRITIONIX_APP_KEY", "f9668e402b5a79eaee8028e4aac19a04")
@st.cache_data
def fetch_image(item: str):
    headers = {'x-app-id': NX_APP_ID, 'x-app-key': NX_APP_KEY}
    params  = {'query': item, 'branded': 'true'}
    r = requests.get("https://trackapi.nutritionix.com/v2/search/instant", headers=headers, params=params)
    r.raise_for_status()
    b = r.json().get('branded', [])
    return b[0]['photo']['thumb'] if b else None

st.subheader("🍌 Snack-Empfehlungen (USDA + Bilder)")
snack_query = st.text_input("Snack suchen (Schlagwort)", "")
if not snack_query:
    st.info("Bitte ein Schlagwort eingeben, um Snacks aus der USDA-Datenbank zu finden.")

foods = search_foods(snack_query, limit=5)
# Loop durch die Snacks
for food in foods:
    desc = food.get('description')
    fdc  = food.get('fdcId')
    # Nährstoffe holen
    details = get_food_details(fdc)
    nut = {}
    for n in details.get('foodNutrients', []):
        if 'nutrient' in n and isinstance(n['nutrient'], dict):
            key = n['nutrient'].get('name'); val = n.get('amount',0)
        elif 'nutrientName' in n:
            key = n['nutrientName'];       val = n.get('value',0)
        else:
            continue
        nut[key] = val or 0
    cal100   = nut.get('Energy') or nut.get('Calories',0)
    fat100   = nut.get('Total lipid (fat)',0)
    prot100  = nut.get('Protein',0)
    carb100  = nut.get('Carbohydrate, by difference',0)
    sugar100 = nut.get('Sugars, total including NLEA') or nut.get('Sugars',0)
    # Berechne Gramm exakt für req_cal
    grams    = req_cal * 100 / cal100 if cal100 else 0

    # Anzeige
    # original serving size from API (wenn vorhanden)
    serving_size = details.get('servingSize') or nut.get('serving_size') or None
    serving_unit = details.get('servingSizeUnit') or ''
    img  = fetch_image(desc)
    col_img, col_chart = st.columns([1,2])
    with col_img:
        if img:
            st.image(img, width=80)
        if serving_size:
            st.write(f"**{desc}**")
            st.write(f"Portionsgröße: {serving_size} {serving_unit}")
            st.write(f"Benötigt: **{grams:.0f} g** für **{req_cal:.0f} kcal**")
        else:
            st.write(f"**{desc}** — **{grams:.0f} g** für **{req_cal:.0f} kcal**")

    # Balkendiagramm Makros
    df_sp = pd.DataFrame({
        'Macro': ['Fat','Protein','Carb','Sugar'],
        'g':     [fat100*grams/100, prot100*grams/100, carb100*grams/100, sugar100*grams/100]
    })
    maxv = df_sp['g'].max()
    bar = (
        alt.Chart(df_sp)
           .mark_bar()
           .encode(
               x='Macro:N', y='g:Q',
               color='Macro:N', tooltip=['Macro','g']
           )
           .properties(width=300, height=200)
    )
    with col_chart:
        st.altair_chart(bar, use_container_width=True)
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
