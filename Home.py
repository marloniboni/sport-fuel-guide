import streamlit as st
import requests
import urllib

st.set_page_config(
    page_title="Sport Fuel Guide",
    page_icon=None,
    layout="wide"
)
st.title("Sport Fuel Guide")
st.info("Diese App hilft dir bei der Planung deiner Trainings- und Wettkampfernährung.")
with st.expander("Gib deine Daten ein"):
    col1, col2 = st.columns(2)
    with col1:
        gewicht    = st.slider("Gewicht (kg)", 40, 150, 70)
        alter      = st.slider("Alter (Jahre)", 12, 80, 25)
    with col2:
        groesse    = st.slider("Körpergröße (cm)", 140, 210, 175)
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
st.success("Deine berechneten Werte")
r1, r2 = st.columns(2)
r1.metric("Grundumsatz (kcal/Tag)", f"{int(grundumsatz)}")
r2.metric("Flüssigkeitsbedarf (L/Tag)", f"{fluessigkeit:.2f} L")
st.markdown("<p style='font-weight:bold; font-size:1.2rem; margin-top:-0.5rem;'>Mit deinen Zahlen hört das Rätselraten auf </p>", unsafe_allow_html=True)
st.write(f"**Grundumsatz**: ca. `{int(grundumsatz)} kcal` pro Tag")
st.write(f"**Täglicher Flüssigkeitsbedarf**: ca. `{fluessigkeit:.2f} Liter`")

st.session_state.gewicht = gewicht
st.session_state.grundumsatz = grundumsatz
st.session_state.fluessigkeit = fluessigkeit

# Navigation zur Vorbereitungsseite
st.markdown("---")
st.markdown("### Hast du ein Workout geplant?")

left, center, right = st.columns([1,2,1])
if center.button("Zur Vorbereitungsseite"):
    # Session-State updaten (wie gehabt)
    st.session_state.update({
        "gewicht":      gewicht,
        "groesse":      groesse,
        "alter":        alter,
        "geschlecht":   geschlecht,
        "grundumsatz":  grundumsatz,
        "fluessigkeit": fluessigkeit
    })
st.switch_page("pages/1_Vor_Workout.py")
