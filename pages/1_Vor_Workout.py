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
from datetime import timedelta

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
    return secs / 60, dist, pts, g

# --- GPX File Upload ---
st.markdown("### GPX-Datei hochladen")
up = st.file_uploader("GPX-Datei", type='gpx')
if not up:
    st.error("Bitte lade eine GPX-Datei hoch, um die Route zu analysieren.")
    st.stop()
txt = up.read().decode()
dauer, distanz, coords, gpx_obj = parse_gpx(txt)
st.success(f"GPX-Datei geladen: {dauer:.0f} Min, {distanz:.2f} km")

# --- Compute metrics ---
intens = st.select_slider("Intensität", ["Leicht","Mittel","Hart"])
facts = {"Laufen":{"Leicht":7,"Mittel":9,"Hart":12},"Radfahren":{"Leicht":5,"Mittel":7,"Hart":10},
         "Schwimmen":{"Leicht":6,"Mittel":8,"Hart":11},"Triathlon":{"Leicht":6,"Mittel":9,"Hart":13}}
cal_hr = facts[sportart][intens] * gewicht
cal_tot = cal_hr * (dauer / 60)
flu_tot = 0.7 * (dauer / 60)

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

events = sorted(set(list(range(eat_i, int(dauer)+1, eat_i)) + list(range(drink_i, int(dauer)+1, drink_i))))
sched = []
for t in events:
    row = {'Minute': t}
    if t % eat_i == 0:
        sn = recommend_snack(cal_tot / (dauer / eat_i))
        row['Essen'] = f"{sn['name']} ({int(sn['calories'])} kcal)"
    if t % drink_i == 0:
        row['Trinken'] = f"Wasser"
    sched.append(row)
df_sched = pd.DataFrame(sched).set_index('Minute')

st.markdown("---")
st.subheader("⏰ Intake-Plan: Essen & Trinken")
st.table(df_sched)

# --- Visualize Consumption + Intake ---
mins = list(range(0, int(dauer)+1))
cal_curve = [cal_hr/60 * m for m in mins]
flu_curve = [0.7/60 * m for m in mins]
plot_df = pd.DataFrame({'Minute': mins,
                         'Kalorienverbrauch (kcal)': cal_curve,
                         'Flüssigkeitsverlust (L)': flu_curve})

# Calorie Chart with intake markers
cal_chart = alt.Chart(plot_df).mark_line().encode(
    x='Minute:Q', y='Kalorienverbrauch (kcal):Q'
)
cal_points = alt.Chart(df_sched.reset_index()).mark_point(color='red', size=50).encode(
    x='Minute:Q', y=alt.value(0), tooltip=['Essen', 'Trinken']
)
st.markdown("---")
st.subheader("📊 Kalorienverbrauch & Intake")
st.altair_chart(cal_chart + cal_points, use_container_width=True)

# Fluid Chart with drink markers
flu_chart = alt.Chart(plot_df).mark_line(color='green').encode(
    x='Minute:Q', y='Flüssigkeitsverlust (L):Q'
)
flu_points = alt.Chart(df_sched.reset_index()).mark_point(color='blue', size=50).encode(
    x='Minute:Q', y=alt.value(0), tooltip=['Trinken']
)
st.markdown("---")
st.subheader("📊 Flüssigkeitsverlust & Intake")
st.altair_chart(flu_chart + flu_points, use_container_width=True)

# --- Interactive Map with Intake Points ---
if coords:
    st.markdown("---")
    st.subheader("🗺️ Route & Intake-Punkte")
    m = folium.Map(location=coords[0], zoom_start=13)
    folium.PolyLine(coords, color='blue', weight=3).add_to(m)
    for t in events:
        idx = min(int(t / dauer * len(coords)), len(coords)-1)
        lat, lon = coords[idx]
        folium.CircleMarker(location=(lat, lon), radius=6,
                            popup=f"{t} min", color='red', fill=True).add_to(m)
    st_folium(m, width=700, height=500)

# --- GPX Export ---
if gpx_obj:
    st.download_button(
        "Download GPX mit Intake-Punkten",
        data=(lambda: (lambda g: g.to_xml())(
            (lambda exp: (exp.tracks.append((trk := gpx_module.GPXTrack())) or trk.segments.append((seg := gpx_module.GPXTrackSegment())) or [seg.points.append(gpx_module.GPXTrackPoint(lat, lon)) for lat, lon in coords] or [exp.waypoints.append(gpx_module.GPXWaypoint(*coords[min(int(t / dauer * len(coords)), len(coords)-1)], name=f"{t} min")) for t in events] or exp)(gpx_module.GPX())
        ))(),
        file_name="route_intake.gpx",
        mime="application/gpx+xml"
    )

st.info("Separate Charts mit Intake-Punkten und exportierbare GPX-Datei.")
