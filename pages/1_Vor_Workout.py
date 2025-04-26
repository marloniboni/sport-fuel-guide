import streamlit as st
import pandas as pd
import requests
import os
import gpxpy
import re
import folium
from streamlit_folium import st_folium
from datetime import timedelta

# --- Nutritionix API Setup ---
APP_ID = os.getenv("NUTRITIONIX_APP_ID", "9810d473")
APP_KEY = os.getenv("NUTRITIONIX_APP_KEY", "f9668e402b5a79eaee8028e4aac19a04")
API_URL = "https://trackapi.nutritionix.com/v2/natural/nutrients"

@st.cache_data
def fetch_nutrition(product_name):
    headers = {'x-app-id': APP_ID, 'x-app-key': APP_KEY, 'Content-Type': 'application/json'}
    r = requests.post(API_URL, headers=headers, json={'query': product_name})
    r.raise_for_status()
    item = r.json().get('foods', [])[0]
    return {'name': item['food_name'], 'calories': item['nf_calories'],
            'serving_qty': item['serving_qty'], 'serving_unit': item['serving_unit']}

CANDIDATE_SNACKS = ['Clif Bar', 'Honey Stinger Gel', 'Gatorade']
@st.cache_data
def recommend_snack(cal_needed):
    opts = [fetch_nutrition(s) for s in CANDIDATE_SNACKS]
    above = [o for o in opts if o['calories'] >= cal_needed]
    return min(above, key=lambda x: x['calories']) if above else max(opts, key=lambda x: x['calories'])

# --- Title & User Data Check ---
st.title("⚡ Vor-Workout Planung")
if 'gewicht' not in st.session_state:
    st.warning("Bitte gib zuerst deine Körperdaten auf der Startseite ein.")
    st.stop()

gewicht = st.session_state.gewicht
grundumsatz = st.session_state.grundumsatz
fluessigkeit_tag = st.session_state.fluessigkeit
sportart = st.selectbox("Sportart", ["Laufen","Radfahren","Schwimmen","Triathlon"])

# --- GPX Parsing ---
def parse_gpx(text):
    g = gpxpy.parse(text)
    secs = g.get_duration() or 0
    dist = (g.length_3d() or 0)/1000
    pts = [(pt.latitude,pt.longitude)
           for tr in g.tracks for seg in tr.segments for pt in seg.points]
    return secs/60, dist, pts

st.markdown("### GPX-Link/HTML oder Datei")
inp = st.text_area("Link oder Embed-Code")
up = st.file_uploader("Oder GPX-Datei hochladen",type='gpx')

dauer=dist=0; coords=[]
if inp:
    m = re.search(r'(https?://[^"\s]+)', inp)
    url = m.group(1) if m else inp.strip()
    try:
        r = requests.get(url); r.raise_for_status()
        if 'komoot.com' in url and not url.endswith('.gpx'):
            tid = re.search(r'/tour/(\d+)',url)
            tok = re.search(r'share_token=([^&]+)',url)
            if tid:
                u = f"https://www.komoot.com/tour/{tid.group(1)}.gpx"
                if tok: u+=f"?share_token={tok.group(1)}"
                r = requests.get(u); r.raise_for_status()
        dauer, dist, coords = parse_gpx(r.text)
    except:
        st.error("GPX laden fehlgeschlagen. Bitte manuell exportieren & hochladen.")
        st.stop()
elif up:
    txt=up.read().decode(); dauer, dist, coords=parse_gpx(txt)
else:
    dauer = st.slider("Dauer (Min)",15,300,60)
    dist = st.number_input("Distanz (km)",0.0,100.0,10.0)

intens = st.select_slider("Intensität",["Leicht","Mittel","Hart"])
facts={'Laufen':{'Leicht':7,'Mittel':9,'Hart':12},'Radfahren':{'Leicht':5,'Mittel':7,'Hart':10},
       'Schwimmen':{'Leicht':6,'Mittel':8,'Hart':11},'Triathlon':{'Leicht':6,'Mittel':9,'Hart':13}}
cal_hr=facts[sportart][intens]*gewicht
cal_tot=cal_hr*(dauer/60)
flu_tot=0.7*(dauer/60)

# --- Schedule Intake ---
if dauer<=60: eat_i=20
elif dauer<=120: eat_i=30
elif dauer<=180: eat_i=45
else: eat_i=60
drink_i=15

events=sorted(set(list(range(eat_i,int(dauer)+1,eat_i))+list(range(drink_i,int(dauer)+1,drink_i))))
sched=[]
for t in events:
    row={'Minute':t}
    if t%eat_i==0:
        sn=recommend_snack(cal_tot/ (dauer/eat_i))
        row['Essen']=sn['name']
    if t%drink_i==0:
        row['Trinken']='Wasser'
    sched.append(row)
df_sched=pd.DataFrame(sched).set_index('Minute')
st.markdown("---")
st.subheader("⏰ Intake-Plan: Wann essen / trinken")
st.table(df_sched)

# --- Dual Visualization ---
mins=list(range(0,int(dauer)+1))
cal_curve=[cal_hr/60*m for m in mins]
flu_curve=[0.7/60*m for m in mins]
plot_cal=pd.DataFrame({'Minute':mins,'Kalorien (kcal)':cal_curve}).set_index('Minute')
plot_flu=pd.DataFrame({'Minute':mins,'Flüssigkeit (L)':flu_curve}).set_index('Minute')

st.markdown("---")
st.subheader("📊 Kalorienverlauf")
st.line_chart(plot_cal)

st.markdown("---")
st.subheader("📊 Flüssigkeitsverlauf")
st.line_chart(plot_flu)

# --- Map with Intake Markers ---
if coords:
    st.markdown("---")
    st.subheader("🗺️ Route und Intake-Punkte")
    m=folium.Map(location=coords[0],zoom_start=13)
    folium.PolyLine(coords,color='blue',weight=3).add_to(m)
    for t in events:
        idx=int(t/dauer*len(coords))
        lat,lon=coords[idx]
        folium.CircleMarker(location=(lat,lon),radius=6,
            popup=f"{t} min",color='red',fill=True).add_to(m)
    st_folium(m,width=700,height=500)

st.info("Getrennte Charts und markierte Intake-Zeiten auf der Karte.")
