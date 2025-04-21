#now comes the Homepage

import streamlit as st

# --- Titel ---
st.title("🏡 Sport Fuel Guide")
st.markdown("Willkommen! Diese App hilft dir bei der Planung deiner Trainings- und Wettkampfernährung.")

# Benutzerangaben
gewicht = st.slider("Gewicht (in kg)", min_value=40, max_value=150, value=70, step=1)
groesse = st.slider("Körpergröße (in cm)", min_value=140, max_value=210, value=175, step=1)
alter = st.slider("Alter (in Jahren)", min_value=12, max_value=80, value=25, step=1)
geschlecht = st.selectbox("Geschlecht", ["Männlich", "Weiblich", "Divers"])

# Harris-Benedict-Formel zur Grundumsatz-Berechnung
if geschlecht == "Männlich":
    grundumsatz = 66.47 + (13.7 * gewicht) + (5.0 * groesse) - (6.8 * alter)
elif geschlecht == "Weiblich":
    grundumsatz = 655.1 + (9.6 * gewicht) + (1.8 * groesse) - (4.7 * alter)
else:
    grundumsatz = (66.47 + 655.1) / 2 + (11.65 * gewicht) + (3.4 * groesse) - (5.75 * alter)  # Mittelwert aus beiden

# Flüssigkeitsbedarf (Richtwert: 35 ml pro kg Körpergewicht)
fluessigkeit = gewicht * 0.035  # in Litern

# Ergebnisse
st.markdown("---")
st.subheader("🧮 Deine berechneten Werte:")

st.write(f"**Grundumsatz**: ca. `{int(grundumsatz)} kcal` pro Tag")
st.write(f"**Täglicher Flüssigkeitsbedarf**: ca. `{fluessigkeit:.2f} Liter`")

st.info("Diese Werte gelten als Basis – dein Bedarf variiert je nach Aktivität, Temperatur und Trainingsziel.")
