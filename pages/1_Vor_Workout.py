import streamlit as st
import pandas as pd
import requests
import gpxpy
import folium
import altair as alt
from streamlit_folium import st_folium
import gpxpy.gpx as gpx_module
import os
import re

# --- App Config ---
st.set_page_config(page_title="Vor-Workout Planung", layout="wide")

# --- App Title & Data Check ---
st.title("⚡ Vor-Workout Planung")
if 'gewicht' not in st.session_state:
    st.warning("Bitte gib zuerst deine Körperdaten auf der Startseite ein.")
    st.stop()
gewicht = st.session_state.gewicht
grundumsatz = st.session_state.grundumsatz
fluessigkeit_tag = st.session_state.fluessigkeit
sportart = st.selectbox("Sportart", ["Laufen","Radfahren","Schwimmen","Triathlon"])

# --- GPX parsing helper ---
def parse_gpx(text: str):
    g = gpxpy.parse(text)
    duration = g.get_duration() or 0
    dist = (g.length_3d() or 0)/1000
    coords = [(pt.latitude, pt.longitude) for tr in g.tracks for seg in tr.segments for pt in seg.points]
    return duration/60, dist, coords, g

# --- Input: GPX link, HTML or file ---
route_input = st.text_area("GPX-Link, iframe oder Anchor-Tag:")
uploaded_file = st.file_uploader("Oder GPX-Datei hochladen", type="gpx")

duration = None
if route_input:
    m = re.search(r'src=["\']([^"\']+)["\']', route_input)
    url = m.group(1) if m else route_input.strip()
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        if 'komoot.com' in url and not url.endswith('.gpx'):
            idm = re.search(r"/tour/(\d+)", url)
            tokm = re.search(r"share_token=([^&]+)", url)
            if idm:
                api_url = f"https://www.komoot.com/tour/{idm.group(1)}.gpx"
                if tokm: api_url += f"?share_token={tokm.group(1)}"
                resp = requests.get(api_url)
                resp.raise_for_status()
        duration, distanz, coords, gpx_obj = parse_gpx(resp.text)
        st.success(f"GPX geladen: {duration:.0f} min, {distanz:.2f} km")
    except Exception as e:
        st.error(f"Fehler beim Laden/Parsen der GPX-URL: {e}")
        st.stop()
elif uploaded_file:
    try:
        text = uploaded_file.read().decode("utf-8")
        duration, distanz, coords, gpx_obj = parse_gpx(text)
        st.success(f"GPX-Datei geladen: {duration:.0f} min, {distanz:.2f} km")
    except Exception as e:
        st.error(f"Fehler beim Parsen der Datei: {e}")
        st.stop()
else:
    duration = st.slider("Dauer (Min)",15,300,60)
    distanz = st.number_input("Distanz (km)",0.0,100.0,10.0)
    coords = []

dauer = duration

# --- Compute metrics ---
faktoren = {"Laufen":7, "Radfahren":5, "Schwimmen":6, "Triathlon":6}
cal_burn = faktoren[sportart] * gewicht * (dauer/60)
fluid_loss = 0.7 * (dauer/60)

st.markdown("---")
st.subheader("📈 Deine Berechnungen:")
st.write(f"**Kalorien Training**: {int(cal_burn)} kcal")
st.write(f"**Flüssigkeit Training**: {fluid_loss:.2f} L")

# --- Intake Plan ---
st.markdown("---")
st.subheader("⏰ Automatischer Intake-Plan")
interval = 30 if dauer<=120 else 45 if dauer<=180 else 60
num = max(int(dauer//interval),1)
cal_each = cal_burn/num
flu_each = fluid_loss/num
schedule = []
for i in range(1,num+1):
    schedule.append({'Minute':int(i*interval),'Kcal':int(cal_each),'Flüssigkeit':round(flu_each,2)})
df_sched = pd.DataFrame(schedule).set_index('Minute')
st.table(df_sched)

# --- Snack & Nutritionix API ---
APP_ID = os.getenv("NUTRITIONIX_APP_ID","9810d473")
APP_KEY = os.getenv("NUTRITIONIX_APP_KEY","f9668e402b5a79eaee8028e4aac19a04")

@st.cache_data
def fetch_nutrition(q):
    headers={'x-app-id':APP_ID,'x-app-key':APP_KEY,'Content-Type':'application/json'}
    r = requests.post("https://trackapi.nutritionix.com/v2/natural/nutrients",json={'query':q},headers=headers)
    r.raise_for_status()
    f=r.json()['foods'][0]
    return {'name':f['food_name'],'cal':f['nf_calories'],'serving':f['serving_qty'], 'unit':f['serving_unit']}

st.markdown("---")
st.subheader("🍌 Snack-Empfehlung vor Training")
pre = fetch_nutrition(st.text_input("Snack eingeben","Banana"))
st.write(f"**{pre['name']}**: {pre['serving']} {pre['unit']} (~{pre['cal']} kcal)")

# --- Chart ---
st.markdown("---")
st.subheader("📊 Verlauf Kalorien & Flüssigkeit")
mins=list(range(int(dauer)+1))
cal_series=[cal_burn/dauer*m for m in mins]lu_series=[fluid_loss/dauer*m for m in mins]
c_df=pd.DataFrame({'Minute':mins,'Kalorien':cal_series,'Flüssigkeit':flu_series}).set_index('Minute')
st.line_chart(c_df)

# --- Map & GPX Export ---
st.markdown("---")
st.subheader("🗺️ Route & Download")
if coords:
    m=folium.Map(location=coords[0],zoom_start=13)
    folium.PolyLine(coords,color='blue').add_to(m)
    st_folium(m,width=700,height=400)
    xml=gpx_obj.to_xml()
    st.download_button("GPX herunterladen",xml,file_name="route.gpx",mime="application/gpx+xml")

st.info("Alle Funktionen wiederhergestellt.")
