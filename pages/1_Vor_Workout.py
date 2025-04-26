import streamlit as st
import pandas as pd
import requests
import os
import gpxpy
import re
from datetime import timedelta

# --- Nutritionix API Setup ---
APP_ID = os.getenv("NUTRITIONIX_APP_ID", "9810d473")
APP_KEY = os.getenv("NUTRITIONIX_APP_KEY", "f9668e402b5a79eaee8028e4aac19a04")
API_URL = "https://trackapi.nutritionix.com/v2/natural/nutrients"

@st.cache_data
def fetch_nutrition(product_name):
    headers = {'x-app-id': APP_ID, 'x-app-key': APP_KEY, 'Content-Type': 'application/json'}
    data = {'query': product_name}
    r = requests.post(API_URL, headers=headers, json=data)
    r.raise_for_status()
    first = r.json().get('foods', [])[0]
    return {
        'name': first['food_name'],
        'calories': first['nf_calories'],
        'serving_qty': first['serving_qty'],
        'serving_unit': first['serving_unit']
    }

CANDIDATE_SNACKS = ['Clif Bar', 'Honey Stinger Gel', 'Gatorade']
@st.cache_data
def recommend_snack(cal_needed):
    options = [fetch_nutrition(snack) for snack in CANDIDATE_SNACKS]
    above = [o for o in options if o['calories'] >= cal_needed]
    return min(above, key=lambda x: x['calories']) if above else max(options, key=lambda x: x['calories'])

# --- App Title ---
st.title("⚡ Vor-Workout Planung")

# --- Ensure user data exists ---
if "gewicht" not in st.session_state:
    st.warning("Bitte gib zuerst deine Körperdaten auf der Startseite ein.")
    st.stop()

gewicht = st.session_state.gewicht
grundumsatz = st.session_state.grundumsatz
fluessigkeit_tag = st.session_state.fluessigkeit

sportart = st.selectbox("Sportart", ["Laufen", "Radfahren", "Schwimmen", "Triathlon"])

# --- GPX parsing helper ---
def parse_gpx(gpx_text):
    gpx = gpxpy.parse(gpx_text)
    duration = gpx.get_duration() or 0
    dist = (gpx.length_3d() or 0) / 1000
    return duration / 60, dist

# --- Input: GPX link or file ---
st.markdown("### GPX-Link, HTML-Snippet oder Datei eingeben")
route_input = st.text_area("Füge hier Komoot/Strava-Link, iframe oder Anchor-Tag ein:")
uploaded_file = st.file_uploader("Oder lade eine GPX-Datei hoch", type="gpx")

duration, distanz = None, None
if route_input:
    # Try extract URL from HTML snippet
    href = None
    if '<' in route_input and '>' in route_input:
        # first look for src in iframe
        m = re.search(r'src=["\']([^"\']+)["\']', route_input)
        if m:
            href = m.group(1)
        else:
            # fallback to href
            m = re.search(r'href=["\']([^"\']+)["\']', route_input)
            if m:
                href = m.group(1)
    url = href or route_input.strip()
    try:
        # Direct GPX URL or webpage URL
        resp = requests.get(url)
        resp.raise_for_status()
        # If URL points to a page, try detect Komoot tour id
        if 'komoot.com' in url and not url.endswith('.gpx'):
            id_match = re.search(r"/tour/(\d+)", url)
            token_match = re.search(r"share_token=([^&]+)", url)
            if id_match:
                tour_id = id_match.group(1)
                token = token_match.group(1) if token_match else None
                # Komoot API endpoint
                api_url = f"https://www.komoot.com/api/v007/tours/{tour_id}.gpx"
                if token:
                    api_url += f"?share_token={token}"
                resp = requests.get(api_url)
                resp.raise_for_status()
        duration, distanz = parse_gpx(resp.text)
        st.success(f"GPX geladen: {duration:.0f} min, {distanz:.2f} km")
    except requests.HTTPError as e:
        if e.response.status_code == 403:
            st.error("Komoot blockiert den Download. Bitte exportiere manuell und lade hoch.")
        else:
            st.error(f"Fehler beim Laden/Parsen der GPX-URL: {e}")
        st.stop()
elif uploaded_file:
    try:
        txt = uploaded_file.read().decode("utf-8")
        duration, distanz = parse_gpx(txt)
        st.success(f"GPX-Datei geladen: {duration:.0f} min, {distanz:.2f} km")
    except Exception as e:
        st.error(f"Fehler beim Parsen der Datei: {e}")
        st.stop()
else:
    st.markdown("### Oder manuell eingeben")
    duration = st.slider("Dauer (Min)", 15, 300, 60)
    distanz = st.number_input("Distanz (km)", 0.0, 100.0, 10.0)

# synchronize variable
dauer = duration

# --- Select intensity ---
intensity = st.select_slider("Intensität", ["Leicht", "Mittel", "Hart"])

# --- Compute metrics ---
factors = {
    "Laufen": {"Leicht": 7, "Mittel": 9, "Hart": 12},
    "Radfahren": {"Leicht": 5, "Mittel": 7, "Hart": 10},
    "Schwimmen": {"Leicht": 6, "Mittel": 8, "Hart": 11},
    "Triathlon": {"Leicht": 6, "Mittel": 9, "Hart": 13},
}
cal_per_hr = factors[sportart][intensity] * gewicht
cal_burn = cal_per_hr * (dauer / 60)
fluid_loss = 0.7 * (dauer / 60)

# --- Display metrics ---
st.markdown("---")
st.subheader("📈 Deine Berechnungen")
st.write(f"Trainingskalorien: {int(cal_burn)} kcal")
st.write(f"Flüssigkeitsbedarf: {fluid_loss:.2f} L")

# --- Snack recommendation ---
st.markdown("---")
st.subheader("🍌 Snack vor Training")
pre_cal = cal_burn * 0.3
sn = recommend_snack(pre_cal)
st.write(f"{sn['name']}: {sn['serving_qty']} {sn['serving_unit']} (~{int(sn['calories'])} kcal)")

# --- Chart ---
st.markdown("---")
st.subheader("📊 Verlauf während Training")
mins = list(range(0, int(dauer) + 1))
cal_min = cal_per_hr / 60
fluid_min = 0.7 / 60
df = pd.DataFrame({
    'Minute': mins,
    'Kalorien': [cal_min * m for m in mins],
    'Flüssigkeit': [fluid_min * m for m in mins]
}).set_index('Minute')
st.line_chart(df)

st.info("Kalorien- und Flüssigkeitsverlauf")
