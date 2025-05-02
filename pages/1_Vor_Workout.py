import streamlit as st #Imports stremlit as a module and reduces streamlit functions to st.
import pandas as pd #Used for Data visualization (schedule)
import requests #used to request USDA API (https://streamlit.io/components)
import gpxpy #import to parse gpx data (used in upload gpx data so it can parse it
import folium #used to draw the route and highligts on map
from streamlit_folium import st_folium #import of folium card to integrate in Streamlit
import altair as alt #loads Altair for data visualization and gives abbreviation alt (used in snack-macro-barchart + Intake/consumption table)

# Title for page
st.set_page_config(page_title="Vor-Workout Planung", layout="wide")

# Title and User interaction
st.title("Vor-Workout Planung")
if 'gewicht' not in st.session_state:#examines if weight is in session state as sample to examine if user has put in their metrics
    st.warning("Bitte gib zuerst deine Körperdaten auf der Startseite ein.")
    st.stop()
gewicht = st.session_state.gewicht
sportart = st.selectbox("Sportart", ["Laufen","Radfahren","Schwimmen"])

# GPX Parsing for uploaded Data
def parse_gpx(text: str): #https://stackoverflow.com/questions/11105663/how-to-extract-gpx-data-with-python/11105679#11105679
    g = gpxpy.parse(text) #
    duration_sec = g.get_duration() or 0
    distance_km  = (g.length_3d() or 0) / 1000
    coords = [(pt.latitude, pt.longitude) for tr in g.tracks for seg in tr.segments for pt in seg.points]
    return duration_sec/60, distance_km, coords, g

#Input: GPX or Manual
#Input: GPX-Datei oder Manuelle Eingabe
mode = st.radio("Datenquelle wählen", ["GPX-Datei hochladen","Manuelle Eingabe"])
if mode == "GPX-Datei hochladen":
    uploaded_file = st.file_uploader("GPX-Datei hochladen", type="gpx")
    if uploaded_file:
        try:
            txt = uploaded_file.read().decode()e
            dauer, distanz, coords, gpx_obj = parse_gpx(txt)
        except Exception:
            st.error("Fehler beim Parsen der hochgeladenen GPX-Datei.")
            st.stop()
    else:
        st.error("Bitte eine GPX-Datei hochladen.")
        st.stop()
else:
    dauer   = st.slider("Dauer (Min)", 15, 300, 60)
    distanz = st.number_input("Distanz (km)", 0.0, 100.0, 10.0)
    coords  = []

st.markdown(f"**Dauer:** {dauer:.0f} Min  •  **Distanz:** {distanz:.2f} km")

# --- Compute Calories & Fluid ---
factors    = {"Laufen":7, "Radfahren":5, "Schwimmen":6, "Triathlon":6}
cal_burn   = factors[sportart] * gewicht * (dauer/60)
fluid_loss = 0.7 * (dauer/60)
# save for Nach-Workout  
st.session_state['planned_calories'] = cal_burn  
st.session_state['fluessigkeit']    = fluid_loss

st.subheader("Deine persönlichen Berechnungen")
st.write(f"Kalorienverbrauch: **{int(cal_burn)} kcal**  •  Flüssigkeitsverlust: **{fluid_loss:.2f} L**")

# --- Intake Schedule ---
eat_interval   = st.select_slider("Essen alle (Min)", [15,20,30,45,60], value=30)
drink_interval = st.select_slider("Trinken alle (Min)", [10,15,20,30], value=15)
events         = sorted(set(range(eat_interval, int(dauer)+1, eat_interval)) | set(range(drink_interval, int(dauer)+1, drink_interval)))
req_cal        = cal_burn / len(events) if events else 0

schedule = []
for t in events:
    row = {'Minute': t}
    if t % eat_interval == 0:
        row['Essen (kcal)'] = req_cal
    if t % drink_interval == 0:
        row['Trinken (L)'] = round(fluid_loss / len(events), 2)
    schedule.append(row)
df_schedule = pd.DataFrame(schedule).set_index('Minute')

st.subheader("Dein persönlicher Intake-Plan")
st.table(df_schedule)

# --- USDA FDC Snack API & Images ---
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
def fetch_image(desc):
    return "https://via.placeholder.com/80?text={desc[:6]}"
st.subheader("Deine Snack-Empfehlungen")
snack_query = st.text_input("Suche deinen lieblings-Snack (Schlüsselwort)", "")
if snack_query:
    foods = search_foods(snack_query, limit=5)
    for food in foods:
        desc = food.get('description')
        fdc  = food.get('fdcId')
        details = get_food_details(fdc)
        nut = {}
        for n in details.get('foodNutrients', []):
            if 'nutrient' in n and isinstance(n['nutrient'], dict):
                key = n['nutrient']['name']; val = n.get('amount',0)
            elif 'nutrientName' in n:
                key = n['nutrientName']; val = n.get('value',0)
            else:
                continue
            nut[key] = val or 0
        cal100   = nut.get('Energy') or nut.get('Calories',0)
        fat100   = nut.get('Total lipid (fat)',0)
        prot100  = nut.get('Protein',0)
        carb100  = nut.get('Carbohydrate, by difference',0)
        sugar100 = sum(v for k,v in nut.items() if 'sugar' in k.lower())
        grams    = req_cal * 100 / cal100 if cal100 else 0
        col_img, col_chart = st.columns([1,2])
        with col_img:
            img = fetch_image(desc)
            if img: st.image(img, width=80)
            st.write(f"**{desc}**")
            st.write(f"Benötigt: {grams:.0f} g für {req_cal:.0f} kcal")
        df_sp = pd.DataFrame({
            'Macro': ['Fat','Protein','Carb','Sugar'],
            'g':     [fat100*grams/100, prot100*grams/100, carb100*grams/100, sugar100*grams/100]
        })
        bar = (
            alt.Chart(df_sp)
               .mark_bar()
               .encode(x='Macro:N',y='g:Q',color='Macro:N',tooltip=['Macro','g'])
               .properties(width=300,height=200)
        )
        with col_chart:
            st.altair_chart(bar, use_container_width=True)
else:
    st.info("Bitte ein Schlüsselwort eingeben, um Snacks zu suchen.")

# --- Dual Charts: Verbrauch vs Intake ---
st.subheader("Dein Verbrauch & Aufnahme")
mins = list(range(int(dauer)+1))
calv = [cal_burn/dauer*m for m in mins]
cali = [req_cal if m in events else 0 for m in mins]
fluv = [fluid_loss/dauer*m for m in mins]
flui = [fluid_loss/len(events) if m in events else 0 for m in mins]
col1, col2 = st.columns(2)
chart_cal = alt.layer(
    alt.Chart(pd.DataFrame({'Minute':mins,'verbrannt':calv})).mark_line().encode(x='Minute',y='verbrannt'),
    alt.Chart(pd.DataFrame({'Minute':mins,'intake_g':cali})).mark_bar(opacity=0.5).encode(x='Minute',y='intake_g')
).properties(width=350,height=300)
col1.altair_chart(chart_cal, use_container_width=True)
chart_flu = alt.layer(
    alt.Chart(pd.DataFrame({'Minute':mins,'verloren':fluv})).mark_line().encode(x='Minute',y='verloren'),
    alt.Chart(pd.DataFrame({'Minute':mins,'aufnahme_l':flui})).mark_bar(opacity=0.5).encode(x='Minute',y='aufnahme_l')
).properties(width=350,height=300)
col2.altair_chart(chart_flu, use_container_width=True)

# --- Map & GPX Download ---
st.subheader("Lade deinen persönlichen Plan auf dein Gerät")
if coords:
    m = folium.Map(location=coords[0], zoom_start=13)
    folium.PolyLine(coords, color='blue').add_to(m)
    for t in events:
        idx = min(int(t/dauer*len(coords)), len(coords)-1)
        lat, lon = coords[idx]
        c = 'red' if t%eat_interval==0 else 'yellow'
        folium.CircleMarker((lat,lon), radius=5, color=c, fill=True).add_to(m)
    st_folium(m, width=700, height=400)
    xml = gpx_obj.to_xml()
    st.download_button("GPX herunterladen", xml, file_name="route_intake.gpx", mime="application/gpx+xml")

st.info("Alle Funktionen aktiv – USDA FDC API-Key verwendet.")
