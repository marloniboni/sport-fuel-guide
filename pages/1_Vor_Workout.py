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
    return {'name': first['food_name'], 'calories': first['nf_calories'], 'serving_qty': first['serving_qty'], 'serving_unit': first['serving_unit']}

CANDIDATE_SNACKS = ['Clif Bar', 'Honey Stinger Gel', 'Gatorade']
@st.cache_data
def recommend_snack(cal_needed):
    options = [fetch_nutrition(snack) for snack in CANDIDATE_SNACKS]
    above = [o for o in options if o['calories'] >= cal_needed]
    return min(above, key=lambda x: x['calories']) if above else max(options, key=lambda x: x['calories'])

# --- App Title ---
st.title("⚡ Vor-Workout Planung")

# --- Session State check ---
if "gewicht" not in st.session_state:
    st.warning("Bitte gib zuerst deine Körperdaten auf der Startseite ein.")
    st.stop()

gewicht = st.session_state.gewicht
grundumsatz = st.session_state.grundumsatz
fluessigkeit_tag = st.session_state.fluessigkeit

sportart = st.selectbox("Sportart", ["Laufen", "Radfahren", "Schwimmen", "Triathlon"])

# --- Parse GPX text into duration & distance ---
def parse_gpx(gpx_text):
    gpx = gpxpy.parse(gpx_text)
    total_seconds = gpx.get_duration() or 0
    dauer = total_seconds / 60
    distanz = (gpx.length_3d() or 0) / 1000
    return dauer, distanz

# --- GPX-Link or file upload ---
st.markdown("### GPX-Link oder Datei")
route_url = st.text_input("GPX-Link zur Aktivität (Komoot Embed oder direkter GPX)")
uploaded_file = st.file_uploader("Oder lade eine GPX-Datei hoch", type="gpx")

if route_url:
    try:
        # Handle Komoot embed links by constructing .gpx endpoint
        if "komoot.com" in route_url and "/tour/" in route_url:
            id_match = re.search(r"/tour/(\d+)", route_url)
            token_match = re.search(r"share_token=([^&]+)", route_url)
            if id_match and token_match:
                tour_id = id_match.group(1)
                token = token_match.group(1)
                # Use .gpx endpoint instead of download path
                download_url = f"https://www.komoot.com/tour/{tour_id}.gpx?share_token={token}"
                resp = requests.get(download_url)
            else:
                resp = requests.get(route_url)
        else:
            resp = requests.get(route_url)
        resp.raise_for_status()
        dauer, distanz = parse_gpx(resp.text)
        st.success(f"Route geladen: Dauer {dauer:.0f} min, Distanz {distanz:.2f} km")
    except Exception as e:
        st.error(f"Fehler beim Laden/Parsieren der GPX-URL: {e}")
        st.stop()
elif uploaded_file:
    try:
        text = uploaded_file.read().decode("utf-8")
        dauer, distanz = parse_gpx(text)
        st.success(f"GPX-Datei erkannt: Dauer {dauer:.0f} min, Distanz {distanz:.2f} km")
    except Exception as e:
        st.error(f"Fehler beim Parsen der hochgeladenen GPX-Datei: {e}")
        st.stop()
else:
    st.markdown("### 🏋️ Was hast du geplant?")
    dauer = st.slider("Dauer des Trainings (in Minuten)", 15, 300, 60, step=5)
    distanz = st.number_input("Geplante Distanz (in km)", min_value=0.0, value=10.0)

# --- Select intensity ---
intensitaet = st.select_slider("Intensität", ["Leicht", "Mittel", "Hart"])

# --- Estimate calories burned ---
faktoren = {
    "Laufen": {"Leicht": 7, "Mittel": 9, "Hart": 12},
    "Radfahren": {"Leicht": 5, "Mittel": 7, "Hart": 10},
    "Schwimmen": {"Leicht": 6, "Mittel": 8, "Hart": 11},
    "Triathlon": {"Leicht": 6, "Mittel": 9, "Hart": 13},
}
kalorien_pro_stunde = faktoren[sportart][intensitaet] * gewicht
kalorien_training = kalorien_pro_stunde * (dauer / 60)

# --- Estimate fluid loss ---
fluessigkeit_training = (0.7 / 60) * dauer

# --- Total needs ---
kalorien_gesamt = grundumsatz + kalorien_training
fluessigkeit_gesamt = fluessigkeit_tag + fluessigkeit_training

# --- Display metrics ---
st.markdown("---")
st.subheader("📈 Deine Berechnungen:")
st.write(f"**Trainingskalorien:** {int(kalorien_training)} kcal")
st.write(f"**Flüssigkeitsbedarf Training:** {fluessigkeit_training:.2f} L")

# --- Snack recommendation ---
st.markdown("---")
st.subheader("🍌 Snack-Empfehlung vor dem Training:")
vorkalorien = kalorien_training * 0.3
snack = recommend_snack(vorkalorien)
st.write(f"**{snack['name']}**: {snack['serving_qty']} {snack['serving_unit']} (~{int(snack['calories'])} kcal)")

# --- Visualize progression ---
st.markdown("---")
st.subheader("📊 Verlauf von Kalorien und Flüssigkeit während des Trainings")
minutes = list(range(0, int(dauer) + 1))
cal_per_min = kalorien_pro_stunde / 60
fluid_per_min = 0.7 / 60

data = {
    'Minute': minutes,
    'Kalorien kumulativ': [cal_per_min * m for m in minutes],
    'Flüssigkeit kumulativ': [fluid_per_min * m for m in minutes]
}
df = pd.DataFrame(data).set_index('Minute')
st.line_chart(df)

st.info("Der Chart zeigt Kalorien- und Flüssigkeitsanspruch im Zeitverlauf.")
