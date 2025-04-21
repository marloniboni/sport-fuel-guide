import streamlit as st

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
# Richtwerte: kcal/kg/h je nach Sport & Intensität
faktoren = {
    "Laufen": {"Leicht": 7, "Mittel": 9, "Hart": 12},
    "Radfahren": {"Leicht": 5, "Mittel": 7, "Hart": 10},
    "Schwimmen": {"Leicht": 6, "Mittel": 8, "Hart": 11},
    "Triathlon": {"Leicht": 6, "Mittel": 9, "Hart": 13},
}

kalorien_pro_stunde = faktoren[sportart][intensität] * gewicht
kalorien_training = kalorien_pro_stunde * (dauer / 60)

# --- Flüssigkeitsbedarf fürs Training (Richtwert: 0.7 Liter pro Stunde Training) ---
fluessigkeit_training = dauer / 60 * 0.7

# --- Gesamtbedarf ---
kalorien_gesamt = grundumsatz + kalorien_training
fluessigkeit_gesamt = fluessigkeit_tag + fluessigkeit_training

# --- Ausgabe ---
st.markdown("---")
st.subheader("📈 Deine Berechnungen:")

st.write(f"**Geplanter Kalorienverbrauch im Training**: `{int(kalorien_training)} kcal`")
st.write(f"**Zusätzlicher Flüssigkeitsbedarf fürs Training**: `{fluessigkeit_training:.2f} Liter`")
st.write(f"---")
st.write(f"**Gesamter Kalorienbedarf heute**: `{int(kalorien_gesamt)} kcal`")
st.write(f"**Gesamter Flüssigkeitsbedarf heute**: `{fluessigkeit_gesamt:.2f} Liter`")

st.info("Tipp: Iss vor dem Training leicht verdauliche Kohlenhydrate und trinke gleichmässig über den Tag verteilt.")
