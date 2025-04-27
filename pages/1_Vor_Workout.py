import streamlit as st
import pandas as pd
import requests
import gpxpy
import gpxpy.gpx as gpx_module
import folium
from streamlit_folium import st_folium
import altair as alt
import os
import re

# --- App Configuration ---
st.set_page_config(page_title="Vor-Workout Planung", layout="wide")

# --- Title and User Data ---
st.title("⚡ Vor-Workout Planung")
if 'gewicht' not in st.session_state:
    st.warning("Bitte gib zuerst deine Körperdaten auf der Startseite ein.")
    st.stop()
gewicht       = st.session_state.gewicht
sportart      = st.selectbox("Sportart", ["Laufen","Radfahren","Schwimmen","Triathlon"])

# --- GPX Parsing Helper ---
def parse_gpx(text: str):
    g = gpxpy.parse(text)
    duration_sec = g.get_duration() or 0
    distance_km  = (g.length_3d() or 0) / 1000
    coords = [(pt.latitude, pt.longitude) for tr in g.tracks for seg in tr.segments for pt in seg.points]
    return duration_sec/60, distance_km, coords, g

# --- Input: GPX or Manual ---
mode = st.radio("Datenquelle wählen", ["GPX-Datei/Link","Manuelle Eingabe"])
if mode == "GPX-Datei/Link":
    route_input = st.text_area("GPX-Link oder HTML Snippet:")
    uploaded_file = st.file_uploader("Oder GPX-Datei hochladen", type="gpx")
    if route_input:
        m = re.search(r'src=["\']([^"\']+)["\']', route_input)
        url = m.group(1) if m else route_input.strip()
        try:
            resp = requests.get(url)
            resp.raise_for_status()
            if 'komoot.com' in url and not url.lower().endswith('.gpx'):
                idm = re.search(r"/tour/(\d+)", url)
                tok = re.search(r"share_token=([^&]+)", url)
                if idm:
                    api = f"https://www.komoot.com/tour/{idm.group(1)}.gpx"
                    if tok: api += f"?share_token={tok.group(1)}"
                    resp = requests.get(api)
                    resp.raise_for_status()
            dauer, distanz, coords, gpx_obj = parse_gpx(resp.text)
        except Exception:
            st.error("Fehler beim Laden/Parsen der GPX-Route.")
            st.stop()
    elif uploaded_file:
        try:
            txt = uploaded_file.read().decode()
            dauer, distanz, coords, gpx_obj = parse_gpx(txt)
        except Exception:
            st.error("Fehler beim Parsen der GPX-Datei.")
            st.stop()
    else:
        st.error("Bitte GPX-Link oder Datei angeben.")
        st.stop()
else:
    dauer  = st.slider("Dauer (Min)", 15, 300, 60)
    distanz = st.number_input("Distanz (km)", 0.0, 100.0, 10.0)
    coords = []

st.markdown(f"**Dauer:** {dauer:.0f} Min  •  **Distanz:** {distanz:.2f} km")

# --- Compute Calories & Fluid ---
factors = {"Laufen":7, "Radfahren":5, "Schwimmen":6, "Triathlon":6}
cal_burn    = factors[sportart] * gewicht * (dauer/60)
fluid_loss  = 0.7 * (dauer/60)

st.subheader("📈 Berechnungen")
st.write(f"Kalorienverbrauch: **{int(cal_burn)} kcal**  •  Flüssigkeitsverlust: **{fluid_loss:.2f} L**")

# --- Intake Schedule ---
eat_interval   = st.select_slider("Essen alle (Min)", [15,20,30,45,60], value=30)
drink_interval = st.select_slider("Trinken alle (Min)", [10,15,20,30], value=15)
events = sorted(set(range(eat_interval, int(dauer)+1, eat_interval)) | set(range(drink_interval, int(dauer)+1, drink_interval)))

schedule = []
for t in events:
    row = {'Minute': t}
    if t % eat_interval == 0:
        row['Essen (kcal)'] = req_cal
    if t % drink_interval == 0:
        row['Trinken (L)'] = round(fluid_loss / (dauer/drink_interval), 2)
    schedule.append(row)
df_schedule = pd.DataFrame(schedule).set_index('Minute')
st.subheader("⏰ Intake-Plan")
st.table(df_schedule)

# --- USDA FDC Snack API ---
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

# Berechne Kalorien pro Snack-Ereignis einmalig
req_cal = cal_burn / len(events) if events else 0

# Nutritionix für Bilder
NX_APP_ID  = os.getenv("NUTRITIONIX_APP_ID", "9810d473")
NX_APP_KEY = os.getenv("NUTRITIONIX_APP_KEY", "f9668e402b5a79eaee8028e4aac19a04")
@st.cache_data
def fetch_image(item: str):
    headers = {'x-app-id': NX_APP_ID, 'x-app-key': NX_APP_KEY}
    params  = {'query': item, 'branded': 'true'}
    r = requests.get("https://trackapi.nutritionix.com/v2/search/instant", headers=headers, params=params)
    r.raise_for_status()
    b = r.json().get('branded', [])
    return b[0]['photo']['thumb'] if b else None

st.subheader("🍌 Snack-Empfehlungen (USDA + Bilder)")
snack_query = st.text_input("Snack suchen (Schlagwort)", "")
if not snack_query:
    st.info("Bitte ein Schlagwort eingeben, um Snacks aus der USDA-Datenbank zu finden.")

foods = search_foods(snack_query, limit=5)
# Loop durch die Snacks
for food in foods:
    desc = food.get('description')
    fdc  = food.get('fdcId')
    # Nährstoffe holen
    details = get_food_details(fdc)
    nut = {}
    for n in details.get('foodNutrients', []):
        if 'nutrient' in n and isinstance(n['nutrient'], dict):
            key = n['nutrient'].get('name'); val = n.get('amount',0)
        elif 'nutrientName' in n:
            key = n['nutrientName'];       val = n.get('value',0)
        else:
            continue
        nut[key] = val or 0
    cal100   = nut.get('Energy') or nut.get('Calories',0)
    fat100   = nut.get('Total lipid (fat)',0)
    prot100  = nut.get('Protein',0)
    carb100  = nut.get('Carbohydrate, by difference',0)
    sugar100 = nut.get('Sugars, total including NLEA') or nut.get('Sugars',0)
    # Berechne Gramm exakt für req_cal
    grams    = req_cal * 100 / cal100 if cal100 else 0

    # Anzeige
    # original serving size from API (wenn vorhanden)
    serving_size = details.get('servingSize') or nut.get('serving_size') or None
    serving_unit = details.get('servingSizeUnit') or ''
    img  = fetch_image(desc)
    col_img, col_chart = st.columns([1,2])
    with col_img:
        if img:
            st.image(img, width=80)
        if serving_size:
            st.write(f"**{desc}**")
            st.write(f"Portionsgröße: {serving_size} {serving_unit}")
            st.write(f"Benötigt: **{grams:.0f} g** für **{req_cal:.0f} kcal**")
        else:
            st.write(f"**{desc}** — **{grams:.0f} g** für **{req_cal:.0f} kcal**")

    # Balkendiagramm Makros
    df_sp = pd.DataFrame({
        'Macro': ['Fat','Protein','Carb','Sugar'],
        'g':     [fat100*grams/100, prot100*grams/100, carb100*grams/100, sugar100*grams/100]
    })
    maxv = df_sp['g'].max()
    bar = (
        alt.Chart(df_sp)
           .mark_bar()
           .encode(
               x='Macro:N', y='g:Q',
               color='Macro:N', tooltip=['Macro','g']
           )
           .properties(width=300, height=200)
    )
    with col_chart:
        st.altair_chart(bar, use_container_width=True)

# --- Dual Charts: Verbrauch vs Intake ---
st.subheader("⏲️ Verlauf Verbrauch & Intake")
mins = list(range(int(dauer)+1))
calv = [cal_burn/dauer*m for m in mins]
cali = [req_cal if m in events else 0 for m in mins]
fluv = [fluid_loss/dauer*m for m in mins]
flui = [fluid_loss/len(events) if m in events else 0 for m in mins]
col1, col2 = st.columns(2)
chart_cal = alt.layer(
    alt.Chart(pd.DataFrame({'Minute':mins,'verbrannt':calv})).mark_line().encode(x='Minute',y='verbrannt'),
    alt.Chart(pd.DataFrame({'Minute':mins,'intake':cali})).mark_bar(opacity=0.5).encode(x='Minute',y='intake')
).properties(width=350,height=300)
col1.altair_chart(chart_cal, use_container_width=True)
chart_flu = alt.layer(
    alt.Chart(pd.DataFrame({'Minute':mins,'verloren':fluv})).mark_line().encode(x='Minute',y='verloren'),
    alt.Chart(pd.DataFrame({'Minute':mins,'aufnahme':flui})).mark_bar(opacity=0.5).encode(x='Minute',y='aufnahme')
).properties(width=350,height=300)
col2.altair_chart(chart_flu, use_container_width=True)

# --- Map & GPX Download ---
st.subheader("🗺️ Route & GPX Download")
if coords:
    m = folium.Map(location=coords[0], zoom_start=13)
    folium.PolyLine(coords, color='blue').add_to(m)
    for t in events:
        idx = min(int(t/dauer*len(coords)), len(coords)-1)
        lat, lon = coords[idx]
        c = 'red' if t%eat_interval==0 else 'blue'
        folium.CircleMarker((lat,lon), radius=5, color=c, fill=True).add_to(m)
    st_folium(m, width=700, height=400)
    xml = gpx_obj.to_xml()
    st.download_button("GPX herunterladen", xml, file_name="route_intake.gpx", mime="application/gpx+xml")

st.info("Alle Funktionen aktiv – USDA FDC API-Key verwendet.")
