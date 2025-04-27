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
sportart = st.selectbox("Sportart", ["Laufen","Radfahren","Schwimmen","Triathlon"])

# --- GPX parsing helper ---
def parse_gpx(text: str):
    g = gpxpy.parse(text)
    duration = g.get_duration() or 0
    dist = (g.length_3d() or 0)/1000
    coords = [(pt.latitude, pt.longitude) for tr in g.tracks for seg in tr.segments for pt in seg.points]
    return duration/60, dist, coords, g

# --- GPX Input ---
route_input = st.text_area("GPX-Link oder HTML-Snippet:")
uploaded_file = st.file_uploader("Oder GPX-Datei hochladen", type="gpx")
if route_input:
    m = re.search(r'src=["\']([^"\']+)["\']', route_input)
    url = m.group(1) if m else route_input.strip()
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        duration, distanz, coords, gpx_obj = parse_gpx(resp.text)
    except:
        st.error("Fehler beim Laden der GPX-Route.")
        st.stop()
elif uploaded_file:
    text = uploaded_file.read().decode()
    duration, distanz, coords, gpx_obj = parse_gpx(text)
else:
    duration = st.slider("Dauer (Min)",15,300,60)
    distanz = st.number_input("Distanz (km)",0.0,100.0,10.0)
    coords = []

dauer = duration
st.write(f"Dauer: {dauer:.0f} Min, Distanz: {distanz:.2f} km")

# --- Compute metrics ---
facts={"Laufen":7,"Radfahren":5,"Schwimmen":6,"Triathlon":6}
cal_burn = facts[sportart]*gewicht*(dauer/60)
fluid_loss = 0.7*(dauer/60)
st.markdown("---")
st.subheader("📈 Berechnungen:")
st.write(f"Kalorien: {int(cal_burn)} kcal | Flüssigkeit: {fluid_loss:.2f} L")

# --- Intake Plan ---
interval_eat = 30
interval_drink = 15
events = sorted(set(range(interval_eat,int(dauer)+1,interval_eat)) | set(range(interval_drink,int(dauer)+1,interval_drink)))
sched=[]
for t in events:
    row={'Minute':t}
    if t%interval_eat==0: row['Essen (kcal)']=int(cal_burn/len(events))
    if t%interval_drink==0: row['Trinken (L)']=round(fluid_loss/len(events),2)
    sched.append(row)
df_sched=pd.DataFrame(sched).set_index('Minute')
st.markdown("---")
st.subheader("⏰ Intake-Plan")
st.table(df_sched)

# --- USDA FDC Snack API statt Nutritionix ---
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

st.markdown("---")
st.subheader("🍌 Snack-Empfehlung (USDA FDC)")
query = st.text_input("Snack suchen","Banana")
foods = search_foods(query, limit=3)
for food in foods:
    name = food.get('description')
    fdc_id = food.get('fdcId')
    details = get_food_details(fdc_id)
    # extrahiere Makros
    nut = {n['nutrient']['name']: n['amount'] for n in details.get('foodNutrients', []) if 'nutrient' in n}
    cal100   = nut.get('Energy') or nut.get('Calories') or 0
    fat100   = nut.get('Total lipid (fat)') or 0
    prot100  = nut.get('Protein') or 0
    carb100  = nut.get('Carbohydrate, by difference') or 0
    sugar100 = nut.get('Sugars, total including NLEA') or nut.get('Sugars') or 0

    req_cal = cal_burn/len(events)
    grams = req_cal*100/cal100 if cal100 else 0
    fat   = fat100 * grams/100
    prot  = prot100 * grams/100
    carb  = carb100 * grams/100
    sugar = sugar100 * grams/100

    df = pd.DataFrame({
        'Makro': ['Fat','Protein','Carb','Sugar'],
        'g':     [fat,prot,carb,sugar]
    })
    # close loop
    df2 = pd.concat([df, df.iloc[[0]]], ignore_index=True)
    max_val = df['g'].max()

    st.write(f"**{name}** — {grams:.0f} g für {req_cal:.0f} kcal")
    area = alt.Chart(df2).mark_area(opacity=0.4).encode(
        theta=alt.Theta('Makro:N'),
        radius=alt.Radius('g:Q', scale=alt.Scale(domain=[0,max_val])),
        color=alt.Color('Makro:N', legend=None)
    )
    line = alt.Chart(df2).mark_line(point=True).encode(
        theta=alt.Theta('Makro:N'),
        radius=alt.Radius('g:Q', scale=alt.Scale(domain=[0,max_val])),
        tooltip=['Makro','g']
    ).interactive()
    st.altair_chart(area+line, use_container_width=False)")

# --- Chart Kalorien & Flüssigkeit ---
st.markdown("---")
st.subheader("📊 Verlauf")
mins=list(range(int(dauer)+1))
cal_series=[cal_burn/dauer*m for m in mins]
fluid_series=[fluid_loss/dauer*m for m in mins]
df_chart=pd.DataFrame({'Minute':mins,'Kalorien':cal_series,'Flüssigkeit':fluid_series}).set_index('Minute')
st.line_chart(df_chart)

# --- Map & GPX Export ---
st.markdown("---")
st.subheader("🗺️ Route & Download GPX")
if coords:
    m=folium.Map(location=coords[0],zoom_start=13)
    folium.PolyLine(coords,color='blue').add_to(m)
    for t in events:
        idx=min(int(t/dauer*len(coords)),len(coords)-1)
        lat,lon=coords[idx]
        col='red' if t%interval_eat==0 else 'blue'
        folium.CircleMarker((lat,lon),radius=5,color=col,fill=True).add_to(m)
    st_folium(m,width=700,height=400)
    xml=gpx_obj.to_xml()
    st.download_button("GPX herunterladen",xml,file_name="route.gpx",mime="application/gpx+xml")

st.info("App läuft mit Nutritionix, nicht USDA API.")
