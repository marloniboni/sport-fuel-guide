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

# --- GPX Parsing ---
def parse_gpx(text: str):
    g = gpxpy.parse(text)
    secs = g.get_duration() or 0
    dist = (g.length_3d() or 0)/1000
    coords = [(pt.latitude, pt.longitude)
              for tr in g.tracks for seg in tr.segments for pt in seg.points]
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
    coords=[]
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

# --- Snack Vorschläge ---
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
        fat100=nutrients.get('Total lipid (fat)') or nutrients.get('Fat') or 0
        prot100=nutrients.get('Protein') or 0
        carb100=nutrients.get('Carbohydrate, by difference') or nutrients.get('Carbs') or 0
        grams=required_cal*100/cal100 if cal100 else 0
        fat= fat100*grams/100
        prot= prot100*grams/100
        carb= carb100*grams/100
        col1,col2=st.columns([2,1])
        if img_url:
            col1.image(img_url,width=80)
        col1.markdown(f"**{name}**: {cal100:.0f} kcal/100g · **{grams:.0f} g**")
                                # Prepare data including sugar, fiber, saturated/unsaturated fat, protein
        sat_fat100 = nutrients.get('Fatty acids, total saturated') or 0
        mono_fat100 = nutrients.get('Fatty acids, total monounsaturated') or 0
        poly_fat100 = nutrients.get('Fatty acids, total polyunsaturated') or 0
        fiber100 = nutrients.get('Fiber, total dietary') or nutrients.get('Dietary fiber') or 0
        sugar100 = nutrients.get('Sugars, total including NLEA') or nutrients.get('Sugar, total') or nutrients.get('Sugars') or 0
        prot100 = nutrients.get('Protein') or 0
        # scale per needed grams
        sat_fat = sat_fat100 * grams/100
        mono_fat = mono_fat100 * grams/100
        poly_fat = poly_fat100 * grams/100
        fiber = fiber100 * grams/100
        sugar = sugar100 * grams/100
        prot = prot100 * grams/100
        # DataFrames for two spiders
        df_macro = pd.DataFrame({
            'Makronährstoff': ['gesättigte Fette','einfach ungesättigte Fette','mehrfach ungesättigte Fette','Ballaststoffe','Zucker','Protein'],
            'Gramm': [sat_fat, mono_fat, poly_fat, fiber, sugar, prot]
        })
        # select micro nutrients: vitamins & minerals
        vit_keys = ['Vitamin C, total ascorbic acid','Vitamin A, IU','Vitamin D (D2 + D3)','Vitamin E (alpha-tocopherol)','Calcium, Ca','Iron, Fe','Magnesium, Mg','Potassium, K']
        micro = []
        for k in vit_keys:
            val = nutrients.get(k) or 0
            micro.append({'Nährstoff': k, 'Menge': val})
        df_micro = pd.DataFrame(micro)
        # draw two spiders side by side
        area1 = alt.Chart(df_macro).mark_area(interpolate='linear', opacity=0.3).encode(
            theta=alt.Theta('Makronährstoff:N', sort=df_macro['Makronährstoff'].tolist()),
            radius=alt.Radius('Gramm:Q'),
            color=alt.Color('Makronährstoff:N', legend=None)
        )
        line1 = alt.Chart(df_macro).mark_line(point=True).encode(
            theta=alt.Theta('Makronährstoff:N', sort=df_macro['Makronährstoff'].tolist()),
            radius=alt.Radius('Gramm:Q'),
            color=alt.Color('Makronährstoff:N', legend=None),
            tooltip=['Makronährstoff','Gramm']
        ).interactive()
        spider1 = alt.layer(area1, line1).properties(width=200, height=200, title='Makronährstoffe')

        area2 = alt.Chart(df_micro).mark_area(interpolate='linear', opacity=0.3).encode(
            theta=alt.Theta('Nährstoff:N', sort=vit_keys),
            radius=alt.Radius('Menge:Q'),
            color=alt.Color('Nährstoff:N', legend=None)
        )
        line2 = alt.Chart(df_micro).mark_line(point=True).encode(
            theta=alt.Theta('Nährstoff:N', sort=vit_keys),
            radius=alt.Radius('Menge:Q'),
            color=alt.Color('Nährstoff:N', legend=None),
            tooltip=['Nährstoff','Menge']
        ).interactive()
                # Debug: show micro and macro data
        col2.write("Makro-Datenframe:")
        col2.write(df_macro)
        col2.write("Mikro-Datenframe:")
        col2.write(df_micro)
        # create interactive spiders
        spider1 = alt.layer(area1, line1).properties(width=200, height=200, title='Makronährstoffe').interactive()
        spider2 = alt.layer(area2, line2).properties(width=200, height=200, title='Vitamine & Mineralstoffe').interactive()(width=200, height=200, title='Vitamine & Mineralstoffe')

        col2.altair_chart(alt.hconcat(spider1, spider2), use_container_width=False)

# --- Kumulative Charts ---
mins=list(range(int(dauer)+1))
cal_cons=[cal_hr/60*m for m in mins]
flu_cons=[0.7/60*m for m in mins]
cal_int=[sum(df_sched.loc[:m,['Essen (kcal)']].fillna(0).values.flatten()) for m in mins]
flu_int=[sum(df_sched.loc[:m,['Trinken (L)']].fillna(0).values.flatten()) for m in mins]
chart_df=pd.DataFrame({'Minute':mins,'Cal consumption':cal_cons,'Cal intake':cal_int,'Flu consumption':flu_cons,'Flu intake':flu_int})
st.markdown("---")
st.subheader("📊 Verbrauch vs. Zufuhr")
cal_base=alt.Chart(chart_df).encode(x='Minute:Q')
cal_line=cal_base.mark_line(color='orange').encode(y='Cal consumption:Q')
cal_int_line=cal_base.mark_line(color='red',strokeDash=[4,2]).encode(y='Cal intake:Q')
flu_base=alt.Chart(chart_df).encode(x='Minute:Q')
flu_line=flu_base.mark_line(color='blue').encode(y='Flu consumption:Q')
flu_int_line=flu_base.mark_line(color='cyan',strokeDash=[4,2]).encode(y='Flu intake:Q')
st.altair_chart(alt.hconcat(cal_line+cal_int_line,flu_line+flu_int_line),use_container_width=True)

# --- Map & GPX Export ---
st.markdown("---")
st.subheader("🗺️ Route & Intake-Punkte")
m=folium.Map(location=coords[0] if coords else [0,0],zoom_start=13)
if coords:
    folium.PolyLine(coords,color='blue',weight=3).add_to(m)
    for t in events:
        idx=min(int(t/dauer*len(coords)),len(coords)-1)
        lat,lon=coords[idx]
        c='orange' if t%eat_i==0 else 'cyan'
        folium.CircleMarker((lat,lon),radius=6,popup=f"{t} Min",color=c,fill=True).add_to(m)
st_folium(m,width=700,height=500)

if 'gpx_obj' in locals():
    export=gpx_module.GPX();trk=gpx_module.GPXTrack();export.tracks.append(trk)
    seg=gpx_module.GPXTrackSegment();trk.segments.append(seg)
    for lat,lon in coords: seg.points.append(gpx_module.GPXTrackPoint(lat,lon))
    for t in events:
        idx=min(int(t/dauer*len(coords)),len(coords)-1)
        lat,lon=coords[idx]
        export.waypoints.append(gpx_module.GPXWaypoint(lat,lon,name=f"{t} Min"))
    st.download_button("Download GPX mit Intake-Punkten",export.to_xml(),file_name="route_intake.gpx",mime="application/gpx+xml")

st.info("USDA-FDC basierte Snack-Suche mit Bild & interaktiver Smart-Spider.")
