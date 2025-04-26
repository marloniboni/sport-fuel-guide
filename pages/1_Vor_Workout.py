import streamlit as st
import pandas as pd
import requests
import gpxpy
import folium
import altair as alt
from streamlit_folium import st_folium
import gpxpy.gpx as gpx_module
import os

# --- USDA FoodData Central API Setup ---
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

# --- Nutritionix for Images ---
NX_APP_ID = os.getenv("NUTRITIONIX_APP_ID", "9810d473")
NX_APP_KEY = os.getenv("NUTRITIONIX_APP_KEY", "f9668e402b5a79eaee8028e4aac19a04")
NX_SEARCH_URL = "https://trackapi.nutritionix.com/v2/search/instant"

@st.cache_data
def fetch_image(query: str):
    headers = {'x-app-id': NX_APP_ID, 'x-app-key': NX_APP_KEY}
    params = {'query': query, 'branded': 'true'}
    resp = requests.get(NX_SEARCH_URL, headers=headers, params=params)
    resp.raise_for_status()
    items = resp.json().get('branded', [])
    if items:
        return items[0].get('photo', {}).get('thumb')
    return None

# --- App Title & Data Check ---
st.title("⚡ Vor-Workout Planung")
if 'gewicht' not in st.session_state:
    st.warning("Bitte gib zuerst deine Körperdaten auf der Startseite ein.")
    st.stop()
gewicht = st.session_state.gewicht
sportart = st.selectbox("Sportart", ["Laufen","Radfahren","Schwimmen","Triathlon"])

# --- GPX Parsing Helper ---
def parse_gpx(text: str):
    g = gpxpy.parse(text)
    secs = g.get_duration() or 0
    dist = (g.length_3d() or 0)/1000
    coords = [(pt.latitude, pt.longitude) for tr in g.tracks for seg in tr.segments for pt in seg.points]
    return secs/60, dist, coords, g

mode = st.radio("Datenquelle", ["GPX-Datei","Manuelle Eingabe"])
if mode=="GPX-Datei":
    up = st.file_uploader("GPX-Datei hochladen", type='gpx')
    if not up:
        st.error("Bitte lade eine GPX-Datei hoch.")
        st.stop()
    dauer, distanz, coords, gpx_obj = parse_gpx(up.read().decode())
else:
    dauer = st.slider("Dauer (Min)",15,300,60)
    distanz = st.number_input("Distanz (km)",0.0,100.0,10.0)
    coords = []
st.write(f"Dauer: {dauer:.0f} Min, Distanz: {distanz:.2f} km")

# --- Compute Metrics ---
facts={"Laufen":{"Leicht":7,"Mittel":9,"Hart":12},"Radfahren":{"Leicht":5,"Mittel":7,"Hart":10},
       "Schwimmen":{"Leicht":6,"Mittel":8,"Hart":11},"Triathlon":{"Leicht":6,"Mittel":9,"Hart":13}}
intensity = st.select_slider("Intensität", ["Leicht","Mittel","Hart"])
cal_hr = facts[sportart][intensity] * gewicht
cal_burn = cal_hr * (dauer/60)
flu_loss = 0.7 * (dauer/60)

eat_i = 20 if dauer<=60 else 30 if dauer<=120 else 45 if dauer<=180 else 60
drink_i = 15
events = sorted(set(range(eat_i,int(dauer)+1,eat_i)) | set(range(drink_i,int(dauer)+1,drink_i)))

# --- Intake Plan ---
sched=[]
for t in events:
    row={'Minute':t}
    if t%eat_i==0: row['Essen (kcal)']=int(cal_burn/(dauer/eat_i))
    if t%drink_i==0: row['Trinken (L)']=round(flu_loss/(dauer/drink_i),2)
    sched.append(row)
df_sched=pd.DataFrame(sched).set_index('Minute')
st.markdown("---")
st.subheader("⏰ Intake-Plan: Essen & Trinken")
st.table(df_sched)

# --- Snack Suggestions ---
st.markdown("---")
st.subheader("🍪 Snack-Vorschläge")
required_cal = cal_burn/(dauer/eat_i)
st.write(f"Benötigte Kalorien pro Snack: **{required_cal:.0f} kcal**")
snack_query = st.text_input("Snack suchen (optional)")
defaults=["Raw Broccoli","Banana","Almonds","Greek Yogurt","Granola Bar"]
queries=[snack_query] if snack_query.strip() else defaults

for q in queries:
    if not snack_query.strip(): st.markdown(f"**Vorschlag:** {q}")
    foods = search_foods(q,limit=5)
    if not foods:
        st.write(f"Keine Ergebnisse für '{q}'.")
        continue
    for food in foods:
        fdc_id=food.get('fdcId')
        name=food.get('description')
        img_url = fetch_image(name)
        details=get_food_details(fdc_id)
        nutrients={}
        for n in details.get('foodNutrients',[]):
            if 'nutrient' in n and isinstance(n['nutrient'],dict):
                key=n['nutrient'].get('name') or n['nutrient'].get('nutrientName')
                val=n.get('amount') or n.get('value')
            else:
                key=n.get('nutrientName')
                val=n.get('value')
            if key: nutrients[key]=val or 0
        cal100=nutrients.get('Energy') or nutrients.get('Calories') or 0
        grams=required_cal*100/cal100 if cal100 else 0
        prot100=nutrients.get('Protein') or 0
        prot=prot100*grams/100
        fiber100=nutrients.get('Fiber, total dietary') or nutrients.get('Dietary fiber') or 0
        fiber=fiber100*grams/100
        sugar100 = nutrients.get('Sugars, total including NLEA') or nutrients.get('Sugar, total') or nutrients.get('Sugars') or nutrients.get('Carbohydrate, by difference') or 0
        sugar=sugar100*grams/100
                # include fat, fiber, sugar, protein in macro spider
        fat100 = nutrients.get('Total lipid (fat)') or nutrients.get('Fat') or 0
        fat = fat100 * grams/100
        df_macro = pd.DataFrame({
            'Makronährstoff': ['Fett','Ballaststoffe','Zucker','Protein'],
            'Gramm': [fat, fiber, sugar, prot]
        })
        col1, col2 = st.columns([2,1])
        if img_url: col1.image(img_url, width=80)
        col1.markdown(f"**{name}**: {cal100:.0f} kcal/100g · **{grams:.0f} g**")
        dfm = df_macro.copy()
        # close the loop for radar
        dfm_closed = pd.concat([dfm, dfm.iloc[[0]]], ignore_index=True)
        max_val = dfm['Gramm'].max()
        col2.write(dfm_closed)
        area1 = (
            alt.Chart(dfm_closed)
               .mark_area(interpolate='linear', opacity=0.3)
               .encode(
                   theta=alt.Theta('Makronährstoff:N', sort=['Ballaststoffe','Zucker','Protein']),
                   radius=alt.Radius('Gramm:Q', scale=alt.Scale(domain=[0, max_val])),
                   color=alt.Color('Makronährstoff:N', legend=None)
               )
        )
        line1 = (
            alt.Chart(dfm_closed)
               .mark_line(point=True)
               .encode(
                   theta=alt.Theta('Makronährstoff:N', sort=['Ballaststoffe','Zucker','Protein']),
                   radius=alt.Radius('Gramm:Q', scale=alt.Scale(domain=[0, max_val])),
                   color=alt.Color('Makronährstoff:N', legend=None),
                   tooltip=['Makronährstoff','Gramm']
               )
               .interactive()
        )
        spider1 = alt.layer(area1, line1).properties(width=200, height=200, title='Makronährstoffe')
        col2.altair_chart(spider1, use_container_width=False)
