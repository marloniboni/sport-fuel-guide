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
            txt = uploaded_file.read().decode()
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

"""
streamlit_snacks_fatsecret.py

A Streamlit app that lets users search for snacks via the FatSecret API
and visualizes how many grams you need to hit target calories.

Dependencies:
  - streamlit
  - pandas
  - altair
  -requests
  -requests-oauthlib
"""
import streamlit as st
import pandas as pd
import altair as alt
from requests_oauthlib import OAuth1Session

# ─────────────────────────────────────────────────────────────────────────────
# Configuration: your FatSecret API credentials
# ─────────────────────────────────────────────────────────────────────────────
FATSECRET_KEY    = "76a1a1599f224ec48ab0bd88a5f3de8d"
FATSECRET_SECRET = "cc664ae84bf341ff8a22e7abe5cff3f8"

# Base URL for all FatSecret API calls
API_URL = "https://platform.fatsecret.com/rest/server.api"

# ─────────────────────────────────────────────────────────────────────────────
# Cached API calls (no fatsecret package needed)
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data
def fs_search(query: str, limit: int = 5) -> list[dict]:
    """
    Search FatSecret for foods matching `query`.
    Args:
        query (str): Keyword to search for (e.g. "chips").
        limit (int): Maximum number of items to return.
    
    Returns:
        A list of food dicts from the FatSecret API.
    """
    oauth = OAuth1Session(FATSECRET_KEY, client_secret=FATSECRET_SECRET)
    params = {
        'method':            'foods.search',
        'search_expression': query,
        'format':            'json',
        'max_results':       limit
    }
    r = oauth.get(API_URL, params=params)
    r.raise_for_status()
    return r.json().get('foods', {}).get('food', [])

@st.cache_data
def fs_get_details(food_id: str) -> dict:
    """
    Fetch detailed info (including servings/nutrients) for a given food_id.
    
    Args:
        food_id (str): The FatSecret food_id.
    
    Returns:
        A dict containing the 'food' object.
    """
    oauth = OAuth1Session(FATSECRET_KEY, client_secret=FATSECRET_SECRET)
    params = {
        'method':  'food.get',
        'food_id': food_id,
        'format':  'json'
    }
    r = oauth.get(API_URL, params=params)
    r.raise_for_status()
    return r.json().get('food', {})

# ─────────────────────────────────────────────────────────────────────────────
# App UI
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Snack Finder (FatSecret)", layout="wide")
st.title("🍿 Snack-Empfehlungen mit FatSecret")

# Sidebar inputs for target calories and search term
req_cal     = st.sidebar.number_input(
    "Ziel-Kalorien pro Portion", min_value=50, max_value=2000, value=200, step=10
)
snack_query = st.sidebar.text_input("Suchbegriff für Snack", "")

if not snack_query:
    st.info("Bitte ein Suchbegriff eingeben, um Snacks zu suchen.")
    st.stop()

# Perform search
products = fs_search(snack_query, limit=5)
if not products:
    st.warning("Keine Produkte gefunden – bitte ein anderes Stichwort versuchen.")
else:
    for p in products:
        # ─────────────────────────────────────────────────────────────
        # Extract basic info & details
        # ─────────────────────────────────────────────────────────────
        food_id = p.get("food_id")
        name    = p.get("food_name", "Unbekanntes Produkt")
        
        details  = fs_get_details(food_id)
        servings = details.get("servings", {}).get("serving", [])
        if isinstance(servings, dict):
            servings = [servings]
        
        # Pick the first metric serving in grams (fallback to any if missing)
        serv = next(
            (s for s in servings if s.get("metric_serving_unit") == "g"),
            (servings[0] if servings else {})
        )
        
        # Nutrient values for that serving
        serv_size_g = float(serv.get("metric_serving_amount", 0))  # e.g. 100
        cal_serv    = float(serv.get("calories",             0))   # kcal
        fat_serv    = float(serv.get("fat",                  0))   # g
        prot_serv   = float(serv.get("protein",              0))   # g
        carb_serv   = float(serv.get("carbohydrate",         0))   # g
        sugar_serv  = float(serv.get("sugar",                0))   # g
        
        # Avoid division by zero
        grams = (req_cal * serv_size_g / cal_serv) if cal_serv and serv_size_g else 0
        
        # ─────────────────────────────────────────────────────────────
        # Layout & Visualization
        # ─────────────────────────────────────────────────────────────
        col1, col2 = st.columns([1, 2])
        with col1:
            # FatSecret doesn’t serve images here
            st.image("https://via.placeholder.com/80?text=No+Image", width=80)
            st.markdown(f"**{name}**")
            st.markdown(f"{grams:.0f} g → {req_cal:.0f} kcal")
        df = pd.DataFrame({
            "Macro": ["Fat", "Protein", "Carb", "Sugar"],
            "Grams": [
                fat_serv   * grams / serv_size_g,
                prot_serv  * grams / serv_size_g,
                carb_serv  * grams / serv_size_g,
                sugar_serv * grams / serv_size_g
            ]
        })
        chart = (
            alt.Chart(df)
               .mark_bar()
               .encode(
                   x="Macro:N",
                   y="Grams:Q",
                   color="Macro:N",
                   tooltip=["Macro", "Grams"]
               )
               .properties(width=300, height=200)
        )
        with col2:
            st.altair_chart(chart, use_container_width=True)

#Kalorienverbrauch vs. kumulative Aufnahme & Netto-Bilanz
import altair as alt
import pandas as pd
import streamlit as st

st.subheader("Dein Verbrauch & Aufnahme")

# Definition
dauer     = float(dauer)      # total minutes
cal_burn  = float(cal_burn)   # total kcal burned
req_cal   = float(req_cal)    # kcal per intake event
events    = set(events)       # e.g. {15, 45, 75, …}
# ------------------------------------------------
mins = list(range(int(dauer) + 1))
calv = [cal_burn / dauer * m for m in mins]
cali = [req_cal if m in events else 0 for m in mins]
df = pd.DataFrame({
    'Minute': mins,
    'Burned': calv,
    'Ingested': cali
})
df['Cum Aufnahme'] = df['Ingested'].cumsum()
df['Netto-Bilanz'] = df['Burned'] - df['Cum Aufnahme']
# 4) Build the chart
base = alt.Chart(df).encode(
    x=alt.X('Minute:Q', scale=alt.Scale(domain=[0, dauer]), axis=alt.Axis(title="Minute"))
)
burn_line = base.mark_line(strokeWidth=2).encode(
    y=alt.Y('Burned:Q', axis=alt.Axis(title='kcal verbrannt')),
    color=alt.value('#1f77b4'),
    tooltip=['Minute','Burned']
)
eat_line = base.mark_line(strokeDash=[4,2]).encode(
    y=alt.Y('Cum Aufnahme:Q', axis=alt.Axis(title='kcal kumuliert')),
    color=alt.value('#ff7f0e'),
    tooltip=['Minute','Cum Aufnahme']
)
net_line = base.mark_line(opacity=0.7).encode(
    y=alt.Y('Netto-Bilanz:Q', axis=alt.Axis(title='kcal Differenz')),
    color=alt.value('#2ca02c'),
    tooltip=['Minute','Netto-Bilanz']
)
chart = alt.layer(burn_line, eat_line, net_line).properties(
    width=700, height=400,
    title="Kalorienverbrauch vs. kumulative Aufnahme & Netto-Bilanz"
).interactive()
st.altair_chart(chart, use_container_width=True)

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
