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
API_URL = "https://trackapi.nutritionix.com/v2/natural/nutrients"

@st.cache_data
def fetch_nutrition(product_name):
    headers = {'x-app-id': APP_ID, 'x-app-key': APP_KEY, 'Content-Type': 'application/json'}
    resp = requests.post(API_URL, headers=headers, json={'query': product_name})
    resp.raise_for_status()
    f = resp.json().get('foods', [])[0]
    return {'name': f['food_name'], 'calories': f['nf_calories'],
            'serving_qty': f['serving_qty'], 'serving_unit': f['serving_unit']}

CANDIDATE_SNACKS = ['Clif Bar', 'Honey Stinger Gel', 'Gatorade']
@st.cache_data
def recommend_snack(cal_needed):
    opts = [fetch_nutrition(s) for s in CANDIDATE_SNACKS]
    above = [o for o in opts if o['calories'] >= cal_needed]
    return min(above, key=lambda x: x['calories']) if above else max(opts, key=lambda x: x['calories'])

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
    pts = [(pt.latitude, pt.longitude)
           for tr in g.tracks for seg in tr.segments for pt in seg.points]
    return secs/60, dist, pts, g

# --- Input Mode: File or Manual ---
mode = st.radio("Datenquelle", ["GPX-Datei", "Manuelle Eingabe"])
if mode == "GPX-Datei":
    up = st.file_uploader("GPX-Datei hochladen", type='gpx')
    if not up:
        st.error("Bitte lade eine GPX-Datei hoch.")
        st.stop()
    txt = up.read().decode()
    dauer, distanz, coords, gpx_obj = parse_gpx(txt)
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

# --- Schedule intake ---
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
sched=[]
for t in events:
    row={'Minute':t}
    eat = (t % eat_i == 0)
    drink = (t % drink_i == 0)
    if eat:
        sn = recommend_snack(cal_tot/(dauer/eat_i))
        row['Essen'] = f"{sn['name']} ({int(sn['calories'])} kcal)"
    if drink:
        row['Trinken'] = 'Wasser'
    sched.append(row)
df_sched = pd.DataFrame(sched).set_index('Minute')

# --- Intake Table ---
st.markdown("---")
st.subheader("⏰ Intake-Plan: Essen & Trinken")
st.table(df_sched)

# --- Build time series with intake values ---
mins = list(range(0, int(dauer) + 1))
# Consumption curves
cal_cons = [cal_hr / 60 * m for m in mins]
flu_cons = [0.7 / 60 * m for m in mins]
# Determine intake events and amounts
eat_events = set(range(eat_i, int(dauer) + 1, eat_i))
drink_events = set(range(drink_i, int(dauer) + 1, drink_i))
# Amount per intake
cal_per_intake = cal_tot / len(eat_events) if eat_events else 0
fluid_per_intake = flu_tot / len(drink_events) if drink_events else 0
# Intake series
cal_int = [cal_per_intake if m in eat_events else 0 for m in mins]
flu_int = [fluid_per_intake if m in drink_events else 0 for m in mins]
# Assemble DataFrame
df_time = pd.DataFrame({
    'Minute': mins,
    'Calorie consumption': cal_cons,
    'Calorie intake': cal_int,
    'Fluid consumption': flu_cons,
    'Fluid intake': flu_int
}).set_index('Minute')

# --- Calorie chart with intake ---
st.markdown("---")
st.subheader("📊 Kalorien: Verbrauch & Aufnahme")
base = alt.Chart(df_time.reset_index()).encode(x='Minute:Q')
line1 = base.mark_line().encode(y='Calorie consumption:Q')
bar1 = base.mark_bar(opacity=0.5, color='orange').encode(y='Calorie intake:Q')
st.altair_chart(line1 + bar1, use_container_width=True)

# --- Fluid chart with intake ---
st.markdown("---")
st.subheader("📊 Flüssigkeit: Verlust & Aufnahme")
base2 = alt.Chart(df_time.reset_index()).encode(x='Minute:Q')
line2 = base2.mark_line(color='green').encode(y='Fluid consumption:Q')
bar2 = base2.mark_bar(opacity=0.5, color='blue').encode(y='Fluid intake:Q')
st.altair_chart(line2 + bar2, use_container_width=True)

# --- Interactive Map & GPX Export ---
st.markdown("---")
st.subheader("🗺️ Route & Intake-Punkte")
m = folium.Map(location=coords[0] if coords else [0,0], zoom_start=13)
if coords:
    folium.PolyLine(coords, color='blue', weight=3).add_to(m)
    for t in events:
        if coords:
            idx = min(int(t/dauer*len(coords)), len(coords)-1)
            lat,lon = coords[idx]
            color = 'orange' if (t % eat_i == 0) else 'blue'
            folium.CircleMarker(location=(lat,lon), radius=6,
                                popup=f"{t} Min", color=color, fill=True).add_to(m)
st_folium(m, width=700, height=500)

# GPX export with waypoints
if 'gpx_obj' in locals():
    export = gpx_module.GPX()
    trk = gpx_module.GPXTrack(); export.tracks.append(trk)
    seg = gpx_module.GPXTrackSegment(); trk.segments.append(seg)
    for lat,lon in coords: seg.points.append(gpx_module.GPXTrackPoint(lat,lon))
    for t in events:
        idx = min(int(t/dauer*len(coords)), len(coords)-1)
        lat,lon=coords[idx]
        export.waypoints.append(gpx_module.GPXWaypoint(lat,lon,name=f"{t} Min"))
    st.download_button("Download GPX mit Intake-Punkten", export.to_xml(),
                       file_name="route_intake.gpx", mime="application/gpx+xml")

st.info("Getrennte Charts mit Verbrauch & Aufnahme und differenzierte Map-Marker.")
