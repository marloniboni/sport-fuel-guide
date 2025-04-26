git add requirements.txt
git commit -m "Add requirements.txt for Streamlit app dependencies"
git push origin main


import streamlit as st
import pandas as pd
import gpxpy
import io
import requests
import os
from datetime import timedelta

# --- Nutritionix API Setup ---
APP_ID = os.getenv("NUTRITIONIX_APP_ID", "9810d473")
APP_KEY = os.getenv("NUTRITIONIX_APP_KEY", "f9668e402b5a79eaee8028e4aac19a04")
API_URL = "https://trackapi.nutritionix.com/v2/natural/nutrients"

# Fetch nutrition info from Nutritionix
@st.cache_data
def fetch_nutrition(product_name):
    headers = {
        'x-app-id': APP_ID,
        'x-app-key': APP_KEY,
        'Content-Type': 'application/json'
    }
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

# Recommend a snack to meet calorie goal
CANDIDATE_SNACKS = ['Clif Bar', 'Honey Stinger Gel', 'Gatorade']
@st.cache_data
def recommend_snack(cal_needed):
    options = []
    for snack in CANDIDATE_SNACKS:
        info = fetch_nutrition(snack)
        options.append(info)
    above = [o for o in options if o['calories'] >= cal_needed]
    return min(above, key=lambda x: x['calories']) if above else max(options, key=lambda x: x['calories'])

st.title("⚡ Vor-Workout Planung")
st.write("Hier planst du deine Kohlenhydratzufuhr und Flüssigkeitsaufnahme **vor dem Training oder Wettkampf**.")

# --- Voraussetzung: Grunddaten aus Home vorhanden? ---
if "gewicht" not in st.session_state:
    st.warning("Bitte gib zuerst deine Körperdaten auf der Startseite ein.")
    st.stop()

gewicht = st.session_state.gewicht
grundumsatz = st.session_state.grundumsatz
fluessigkeit_tag = st.session_state.fluessigkeit

# --- Trainingsdaten abfragen ---
st.markdown("### 🏋️ Was hast du geplant?")

sportart = st.selectbox("Sportart", ["Laufen", "Radfahren", "Schwimmen", "Triathlon"])
dauer = st.slider("Dauer des Trainings (in Minuten)", 15, 300, 60, step=5)
distanz = st.number_input("Geplante Distanz (in km)", min_value=0.0, value=10.0)
intensität = st.select_slider("Intensität", ["Leicht", "Mittel", "Hart"])

# --- Kalorienverbrauch schätzen ---
faktoren = {
    "Laufen": {"Leicht": 7, "Mittel": 9, "Hart": 12},
    "Radfahren": {"Leicht": 5, "Mittel": 7, "Hart": 10},
    "Schwimmen": {"Leicht": 6, "Mittel": 8, "Hart": 11},
    "Triathlon": {"Leicht": 6, "Mittel": 9, "Hart": 13},
}
kalorien_pro_stunde = faktoren[sportart][intensität] * gewicht
kalorien_training = kalorien_pro_stunde * (dauer / 60)

# --- Flüssigkeitsbedarf fürs Training ---
fluessigkeit_training = (0.7 / 60) * dauer  # 0.7 L per hour

# --- Gesamtbedarf ---
kalorien_gesamt = grundumsatz + kalorien_training
fluessigkeit_gesamt = fluessigkeit_tag + fluessigkeit_training

# --- Ausgabe ---
st.markdown("---")
st.subheader("📈 Deine Berechnungen:")
st.write(f"**Geplanter Kalorienverbrauch im Training**: `{int(kalorien_training)} kcal`")
st.write(f"**Zusätzlicher Flüssigkeitsbedarf fürs Training**: `{fluessigkeit_training:.2f} L`")
st.write("---")
st.write(f"**Gesamter Kalorienbedarf heute**: `{int(kalorien_gesamt)} kcal`")
st.write(f"**Gesamter Flüssigkeitsbedarf heute**: `{fluessigkeit_gesamt:.2f} L`")

# --- Snack-Empfehlung vor Workout ---
st.markdown("---")
st.subheader("🍌 Snack-Empfehlung vor dem Training:")
vorkalorien = kalorien_training * 0.3  # 30% der Trainingskalorien vorab
snack = recommend_snack(vorkalorien)
st.write(f"Um ~{int(vorkalorien)} kcal vor dem Training zuzuführen, empfehlen wir: **{snack['name']}**")
st.write(f"Portion: {snack['serving_qty']} {snack['serving_unit']} (~{int(snack['calories'])} kcal)")

# --- Verlauf visualisieren ---
st.markdown("---")
st.subheader("📊 Verlauf von Kalorien und Flüssigkeit während des Trainings")
# Erstelle Zeitreihe pro Minute
minutes = list(range(0, dauer + 1))
cal_per_min = kalorien_pro_stunde / 60
fluid_per_min = 0.7 / 60

data = {
    'Minute': minutes,
    'Kumulierte Kalorien (kcal)': [cal_per_min * m for m in minutes],
    'Kumulierte Flüssigkeit (L)': [fluid_per_min * m for m in minutes]
}
df = pd.DataFrame(data).set_index('Minute')

# Plot mit Streamlit
st.line_chart(df)

st.info("Der Chart zeigt, wie sich dein Kalorienverbrauch und deine Flüssigkeitsabgabe über die Trainingszeit aufbauen.")
