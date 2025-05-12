import streamlit as st

# -----------------------------
# Seiten-Config & Styles
# -----------------------------
st.set_page_config(
    page_title="Sport Fuel Guide",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
  /* Seite-Hintergrund & Schrift */
  body {
    background-color: #F7F9FA;
    font-family: 'Segoe UI', sans-serif;
  }
  /* Card-Container */
  .card {
    background: white;
    border-radius: 12px;
    padding: 1.2rem;
    box-shadow: 0 3px 8px rgba(0,0,0,0.04);
    margin-bottom: 1.2rem;
  }
  /* Überschriften in Cards */
  .card h1 {
    margin: 0;
    font-size: 2.2rem;
    color: #2E3A59;
  }
  .card p {
    margin: 0.2rem 0 0;
    color: #6B7A95;
    font-size: 1rem;
  }
  /* Vergrößerte Buttons */
  .stButton > button {
    padding: 0.8rem 1.5rem !important;
    font-size: 1.1rem !important;
    border-radius: 8px;
  }
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Header
# -----------------------------
st.markdown(
    "<div class='card'><h1>Sport Fuel Guide</h1>"
    "<p>Plane deine Trainings- und Wettkampfernährung.</p></div>",
    unsafe_allow_html=True
)

# Banner-Bild
st.image(
    "https://images.ctfassets.net/aytpbz9e0sd0/5n9hvfTT9hG7QxgveI7E3W/"
    "58dfe5751c5aef4155e60f110fa6f1cd/Peter-Stetina-with-CLIF-SHOT-"
    "Energy-Gel-riding-bike.jpg?w=1920",
    use_container_width=True,
    clamp=True
)

st.markdown("---")

# -----------------------------
# Nutzereingaben
# -----------------------------
st.markdown("<div class='card'><h2>Deine Daten</h2></div>", unsafe_allow_html=True)
col1, col2 = st.columns(2)
with col1:
    gewicht    = st.slider("Gewicht (kg)", 40, 150, 70)
    alter      = st.slider("Alter (Jahre)", 12, 80, 25)
with col2:
    groesse    = st.slider("Körpergröße (cm)", 140, 210, 175)
    geschlecht = st.selectbox("Geschlecht", ["Männlich", "Weiblich"])

# -----------------------------
# Berechnungen
# -----------------------------
if geschlecht == "Männlich":
    grundumsatz = 66.47 + 13.7 * gewicht + 5.0 * groesse - 6.8 * alter
else:
    grundumsatz = 655.1 + 9.6 * gewicht + 1.8 * groesse - 4.7 * alter
fluessigkeit = gewicht * 0.035

# -----------------------------
# Ergebnisse
# -----------------------------
st.markdown("<div class='card'><h2>Deine Werte</h2></div>", unsafe_allow_html=True)
r1, r2 = st.columns(2)
r1.metric("Grundumsatz (kcal/Tag)", f"{int(grundumsatz)}")
r2.metric("Flüssigkeitsbedarf (L/Tag)", f"{fluessigkeit:.2f}")

# -----------------------------
# Navigation zum Workout
# -----------------------------
st.markdown("---")
if st.button("Zur Vorbereitungsseite"):
    # Session-State updaten
    st.session_state.update({
        "gewicht": gewicht,
        "groesse": groesse,
        "alter": alter,
        "geschlecht": geschlecht,
        "grundumsatz": grundumsatz,
        "fluessigkeit": fluessigkeit
    })
st.query_params.page = "vor_workout"
