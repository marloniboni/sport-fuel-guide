import streamlit as st
import pandas as pd
import requests
import os
import gpxpy
import folium
import re
from streamlit_folium import st_folium
import gpxpy.gpx as gpx_module
import altair as alt

# --- Nutritionix API Setup ---
APP_ID = os.getenv("NUTRITIONIX_APP_ID", "9810d473")
APP_KEY = os.getenv("NUTRITIONIX_APP_KEY", "f9668e402b5a79eaee8028e4aac19a04")
NUTRIX_SEARCH_URL = "https://trackapi.nutritionix.com/v2/search/instant"
NUTRIX_NUTRIENTS_URL = "https://trackapi.nutritionix.com/v2/natural/nutrients"
headers = {'x-app-id': APP_ID, 'x-app-key': APP_KEY}

@st.cache_data
def search_snacks(query: str = "sports nutrition", limit: int = 20):
    params = {'query': query, 'branded': 'true'}
    response = requests.get(NUTRIX_SEARCH_URL, headers=headers, params=params)
    response.raise_for_status()
    return response.json().get('branded', [])[:limit]

@st.cache_data
def fetch_nutrition(name: str):
    payload = {'query': name}
    resp = requests.post(NUTRIX_NUTRIENTS_URL, headers={**headers, 'Content-Type': 'application/json'}, json=payload)
    resp.raise_for_status()
    foods = resp.json().get('foods', [])
    return foods[0] if foods else None

# --- App Title & Data Check ---
st.title("⚡ Vor-Workout Planung")
if 'gewicht' not in st.session_state:
    st.warning("Bitte gib zuerst deine Körperdaten auf der Startseite ein.")
    st.stop()
gewicht = st.session_state.gewicht
grundumsatz = st.session_state.grundumsatz
fluessigkeit_tag = st.session_state.fluessigkeit
sportart = st.selectbox("Sportart", ["Laufen","Radfahren","Schwimmen","Triathlon"])

# --- GPX Parsing Helper ---
def parse_gpx(text):
    g = gpxpy.parse(text)
    secs = g.get_duration() or 0
    dist = (g.length_3d() or 0) / 1000
    pts = [(pt.latitude, pt.longitude) for tr in g.tracks for seg in tr.segments for pt in seg.points]
    return secs/60, dist, pts, g

# --- Input Mode: File or Manual ---
mode = st.radio("Datenquelle", ["GPX-Datei", "Manuelle Eingabe"])
if mode == "GPX-Datei":
    up = st.file_uploader("GPX-Datei hochladen", type='gpx')
    if not up:
        st.error("Bitte lade eine GPX-Datei hoch.")
        st.stop()
    dauer, distanz, coords, gpx_obj = parse_gpx(up.read().decode())
else:
    dauer = st.slider("Dauer (Min)", 15, 300, 60)
    distanz = st.number_input("Distanz (km)", 0.0, 100.0, 10.0)
    coords = []
st.write(f"Dauer: {dauer} Min, Distanz: {distanz} km")

# --- Compute metrics ---
intensity = st.select_slider("Intensität", ["Leicht","Mittel","Hart"])
facts = {"Laufen":{"Leicht":7,"Mittel":9,"Hart":12},"Radfahren":{"Leicht":5,"Mittel":7,"Hart":10},
         "Schwimmen":{"Leicht":6,"Mittel":8,"Hart":11},"Triathlon":{"Leicht":6,"Mittel":9,"Hart":13}}
cal_hr = facts[sportart][intensity] * gewicht
cal_tot = cal_hr * (dauer/60)
flu_tot = 0.7 * (dauer/60)

# --- Schedule Intake ---
if dauer <= 60:
    eat_i = 20
elif dauer <= 120:
    eat_i = 30
elif dauer <= 180:
    eat_i = 45
else:
    eat_i = 60
drink_i = 15
events = sorted(set(range(eat_i, int(dauer)+1, eat_i)) | set(range(drink_i, int(dauer)+1, drink_i)))

# --- FastSecret API Setup for Macro Breakdown ---
FAST_ID = os.getenv("FASTSECRET_CLIENT_ID")
FAST_SECRET = os.getenv("FASTSECRET_CLIENT_SECRET")
@st.cache_data
def fetch_fastsecret_token():
    # Obtain OAuth token
    token_resp = requests.post(
        "https://api.fastsecret.com/oauth/token", 
        data={'grant_type':'client_credentials'},
        auth=(FAST_ID, FAST_SECRET)
    )
    token_resp.raise_for_status()
    return token_resp.json().get('access_token')

@st.cache_data
def fetch_food_macros(product_name):
    token = fetch_fastsecret_token()
    hdr = {'Authorization': f"Bearer {token}", 'Content-Type':'application/json'}
    resp = requests.get(
        f"https://api.fastsecret.com/v1/foods/search?query={urllib.parse.quote(product_name)}", 
        headers=hdr
    )
    resp.raise_for_status()
    items = resp.json().get('foods', [])
    if not items:
        return {}
    # Take first match, get detailed info
    food_id = items[0]['id']
    detail = requests.get(f"https://api.fastsecret.com/v1/foods/{food_id}", headers=hdr)
    detail.raise_for_status()
    data = detail.json()
    # Return macros
    return { 'fat': data['fat_g'], 'protein': data['protein_g'], 'carbs': data['carbohydrates_g'] }

# --- Intake Plan Table ---
sched = []
for t in events:
    row = {'Minute': t}
    if t % eat_i == 0:
        row['Essen (kcal)'] = int(cal_tot/(dauer/eat_i))
    if t % drink_i == 0:
        row['Trinken (L)'] = round(flu_tot/(dauer/drink_i), 2)
    sched.append(row)
df_sched = pd.DataFrame(sched).set_index('Minute')
st.markdown("---")
st.subheader("⏰ Intake-Plan: Essen & Trinken")
st.table(df_sched)

# --- Snack-Optionen passend zu Intake-Kalorien ---
st.markdown("---")
st.subheader("🍪 Snacks mit exakter Kalorienzahl für jede Intake-Einheit")
# benötigte Kalorien pro Intake-Ereignis
required_cal = int(cal_tot/(dauer/eat_i))
st.write(f"Benötigte Kalorien pro Snack: **{required_cal} kcal**")
# Suche nach passenden Snacks
query = st.text_input("Suchbegriff für Snacks", "sports nutrition")
limit = st.slider("Anzahl Ergebnisse", 5, 50, 20)
try:
    snacks = search_snacks(query=query, limit=limit)
    matches = []
    for item in snacks:
        nut = fetch_nutrition(item['food_name'])
        if nut and int(nut['nf_calories']) == required_cal:
            matches.append((item['food_name'], item.get('brand_name',''), nut))
    if not matches:
        st.write("Keine Snacks gefunden, die genau diesen Kalorienwert haben.")
    else:
        for name, brand, nut in matches:
            serving = f"{nut['serving_qty']} {nut['serving_unit']}"
            st.write(f"- **{name}** ({brand}): {required_cal} kcal · {serving}")
except requests.HTTPError:
    st.warning("Snack-Optionen konnten nicht geladen werden. Bitte später erneut versuchen.")

# --- Build time series for cumulative charts ---
mins = list(range(0, int(dauer)+1))
c_rate = cal_hr/60
f_rate = 0.7/60
cal_cum_cons = [c_rate * m for m in mins]
flu_cum_cons = [f_rate * m for m in mins]
eat_events = set(range(eat_i, int(dauer)+1, eat_i))
drink_events = set(range(drink_i, int(dauer)+1, drink_i))
cal_amt = cal_tot/len(eat_events) if eat_events else 0
flu_amt = flu_tot/len(drink_events) if drink_events else 0
cum = 0
cal_cum_int = []
for m in mins:
    if m in eat_events: cum += cal_amt
    cal_cum_int.append(cum)
cum = 0
flu_cum_int = []
for m in mins:
    if m in drink_events: cum += flu_amt
    flu_cum_int.append(cum)
chart_df = pd.DataFrame({ 'Minute': mins,
    'Cal consumption': cal_cum_cons, 'Cal intake': cal_cum_int,
    'Flu consumption': flu_cum_cons, 'Flu intake': flu_cum_int })

st.markdown("---")
st.subheader("📊 Kumulative Verbrauch vs. Zufuhr")
cal_base = alt.Chart(chart_df).encode(x='Minute:Q')
cal_line = cal_base.mark_line(color='orange').encode(y='Cal consumption:Q')
cal_int_line = cal_base.mark_line(color='red', strokeDash=[4,2]).encode(y='Cal intake:Q')
flu_base = alt.Chart(chart_df).encode(x='Minute:Q')
flu_line = flu_base.mark_line(color='blue').encode(y='Flu consumption:Q')
flu_int_line = flu_base.mark_line(color='cyan', strokeDash=[4,2]).encode(y='Flu intake:Q')
st.altair_chart(alt.hconcat(
    (cal_line + cal_int_line).properties(width=300, title='Kalorien'),
    (flu_line + flu_int_line).properties(width=300, title='Flüssigkeit')
), use_container_width=True)

# --- Interactive Map & GPX Export ---
st.markdown("---")
st.subheader("🗺️ Route & Intake-Punkte")
m = folium.Map(location=coords[0] if coords else [0,0], zoom_start=13)
if coords:
    folium.PolyLine(coords, color='blue', weight=3).add_to(m)
    for t in events:
        idx = min(int(t/dauer*len(coords)), len(coords)-1)
        lat, lon = coords[idx]
        color = 'orange' if t in eat_events else 'cyan'
        folium.CircleMarker(location=(lat, lon), radius=6, popup=f"{t} Min", color=color, fill=True).add_to(m)
st_folium(m, width=700, height=500)

if 'gpx_obj' in locals():
    export = gpx_module.GPX()
    trk = gpx_module.GPXTrack(); export.tracks.append(trk)
    seg = gpx_module.GPXTrackSegment(); trk.segments.append(seg)
    for lat, lon in coords: seg.points.append(gpx_module.GPXTrackPoint(lat, lon))
    for t in events:
        idx = min(int(t/dauer*len(coords)), len(coords)-1)
        lat, lon = coords[idx]
        export.waypoints.append(gpx_module.GPXWaypoint(lat, lon, name=f"{t} Min"))
    st.download_button("Download GPX mit Intake-Punkten", export.to_xml(), file_name="route_intake.gpx", mime="application/gpx+xml")

st.info("Kompletter Workflow mit API-basierten Snack-Optionen.")
