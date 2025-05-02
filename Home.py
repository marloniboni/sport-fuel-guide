import streamlit as st
import requests
import urllib

# -----------------------------
# Titel & Benutzer-Eingaben
# -----------------------------
st.title("Sport Fuel Guide")
st.markdown("Willkommen! Diese App hilft dir bei der Planung deiner Trainings- und Wettkampfernährung.")
st.image("https://images.ctfassets.net/aytpbz9e0sd0/5n9hvfTT9hG7QxgveI7E3W/58dfe5751c5aef4155e60f110fa6f1cd/Peter-Stetina-with-CLIF-SHOT-Energy-Gel-riding-bike.jpg?w=1920", use_container_width=800)

st.markdown("<p style='font-weight:bold; font-size:1.2rem; margin-top:-0.5rem;'>Geben Sie Ihre Daten ein👇</p>", unsafe_allow_html=True)

gewicht = st.slider("Gewicht (in kg)", min_value=40, max_value=150, value=70, step=1)
groesse = st.slider("Körpergröße (in cm)", min_value=140, max_value=210, value=175, step=1)
alter = st.slider("Alter (in Jahren)", min_value=12, max_value=80, value=25, step=1)
geschlecht = st.selectbox("Geschlecht", ["Männlich", "Weiblich"])

# Grundumsatz & Flüssigkeit
if geschlecht == "Männlich":
    grundumsatz = 66.47 + (13.7 * gewicht) + (5.0 * groesse) - (6.8 * alter)
else:
    grundumsatz = 655.1 + (9.6 * gewicht) + (1.8 * groesse) - (4.7 * alter)

fluessigkeit = gewicht * 0.035

# Home-Page: nachdem Du die Slider/Selectboxen gelesen hast:
st.session_state['gewicht']    = gewicht
st.session_state['groesse']    = groesse
st.session_state['alter']      = alter
st.session_state['geschlecht'] = geschlecht
st.session_state['grundumsatz'] = grundumsatz
st.session_state['fluessigkeit'] = fluessigkeit

st.markdown("---")
st.subheader("Deine berechneten Werte:")
st.image("https://sp-ao.shortpixel.ai/client/to_webp,q_glossy,ret_img/https://eatmyride.com/wp-content/uploads/2023/01/garmin_balancer_new-1.png", use_container_width=25)
st.markdown("<p style='font-weight:bold; font-size:1.2rem; margin-top:-0.5rem;'>Mit deinen Zahlen hört das Rätselraten auf </p>", unsafe_allow_html=True)
st.write(f"**Grundumsatz**: ca. `{int(grundumsatz)} kcal` pro Tag")
st.write(f"**Täglicher Flüssigkeitsbedarf**: ca. `{fluessigkeit:.2f} Liter`")

st.session_state.gewicht = gewicht
st.session_state.grundumsatz = grundumsatz
st.session_state.fluessigkeit = fluessigkeit

# Navigation zur Vorbereitungsseite
st.markdown("---")
st.markdown("### Hast du ein Workout geplant?")
if st.button("➡️ Ja, gehe zur Vorbereitungsseite"):
    st.switch_page("pages/1_Vor_Workout.py")

