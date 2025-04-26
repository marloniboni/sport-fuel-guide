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
    if t % eat_i == 0:
        sn = recommend_snack(cal_tot/(dauer/eat_i))
        row['Essen'] = f"{sn['name']} ({int(sn['calories'])} kcal)"
    if t % drink_i == 0:
        row['Trinken'] = 'Wasser'
    sched.append(row)
df_sched = pd.DataFrame(sched).set_index('Minute')

# Intake plan table
st.markdown("---")
st.subheader("⏰ Intake-Plan: Essen & Trinken")
st.table(df_sched)

# --- Build time series with net series ---
mins = list(range(0, int(dauer)+1))
# consumption per minute
cal_cons = [cal_hr/60 for _ in mins]
flu_cons = [0.7/60 for _ in mins]
# net change per minute
df_time = pd.DataFrame({'Minute': mins})
df_time['Calorie net'] = df_time['Minute'].apply(lambda m: -cal_cons[m] + (cal_tot/(dauer/eat_i) if (m in range(eat_i, int(dauer)+1, eat_i)) else 0))
df_time['Fluid net'] = df_time['Minute'].apply(lambda m: -flu_cons[m] + (flu_tot/(dauer/drink_i) if (m in range(drink_i, int(dauer)+1, drink_i)) else 0))
# cumulative
df_time['Calorie reserve'] = df_time['Calorie net'].cumsum()
df_time['Fluid reserve'] = df_time['Fluid net'].cumsum()

# --- Visualisierung: Verbrauch & Intake Seite an Seite ---
st.markdown("---")
st.subheader("📊 Verbrauch vs. Aufnahme")
# Minuten und Intake Events
eat_events = set(range(eat_i, int(dauer)+1, eat_i))
drink_events = set(range(drink_i, int(dauer)+1, drink_i))

# DataFrame für Charts
chart_df = pd.DataFrame({
    'Minute': mins,
    'Calorie consumption': [cal_hr/60 * m for m in mins],
    'Calorie intake': [cal_tot/len(eat_events) if m in eat_events else 0 for m in mins],
    'Fluid consumption': [0.7/60 * m for m in mins],
    'Fluid intake': [flu_tot/len(drink_events) if m in drink_events else 0 for m in mins]
})

# Kalorien Chart
cal_base = alt.Chart(chart_df).encode(x='Minute:Q')
cal_line = cal_base.mark_line(color='orange').encode(y='Calorie consumption:Q')
cal_bar = cal_base.mark_bar(opacity=0.5, color='red').encode(y='Calorie intake:Q')
cal_chart = (cal_line + cal_bar).properties(width=300, height=250, title='Kalorien')

# Flüssigkeit Chart
flu_base = alt.Chart(chart_df).encode(x='Minute:Q')
flu_line = flu_base.mark_line(color='blue').encode(y='Fluid consumption:Q')
flu_bar = flu_base.mark_bar(opacity=0.5, color='cyan').encode(y='Fluid intake:Q')
flu_chart = (flu_line + flu_bar).properties(width=300, height=250, title='Flüssigkeit')

# Charts horizontal anordnen
combined = alt.hconcat(cal_chart, flu_chart)
st.altair_chart(combined, use_container_width=True)

# --- Interactive Map & GPX Export --- & GPX Export ---
st.markdown("---")
st.subheader("🗺️ Route & Intake-Punkte")
m = folium.Map(location=coords[0] if coords else [0,0], zoom_start=13)
if coords:
    folium.PolyLine(coords, color='blue', weight=3).add_to(m)
    for t in events:
        idx = min(int(t/dauer*len(coords)), len(coords)-1)
        lat,lon = coords[idx]
        color = 'orange' if (t % eat_i == 0) else 'blue'
        folium.CircleMarker(location=(lat,lon), radius=6,
                            popup=f"{t} Min", color=color, fill=True).add_to(m)
st_folium(m, width=700, height=500)

# GPX export
if 'gpx_obj' in locals():
    export = gpx_module.GPX()
    trk = gpx_module.GPXTrack(); export.tracks.append(trk)
    seg = gpx_module.GPXTrackSegment(); trk.segments.append(seg)
    for lat,lon in coords: seg.points.append(gpx_module.GPXTrackPoint(lat,lon))
    for t in events:
        idx = min(int(t/dauer*len(coords)), len(coords)-1)
        lat,lon = coords[idx]
        export.waypoints.append(gpx_module.GPXWaypoint(lat,lon,name=f"{t} Min"))
    st.download_button("Download GPX mit Intake-Punkten", export.to_xml(),
                       file_name="route_intake.gpx", mime="application/gpx+xml")

st.info("Netto-Verlauf und exportierbare GPX-Datei mit Intake-Punkten.")
