import streamlit as st

# -----------------------------
# Seiten-Config & Styles
# -----------------------------
st.set_page_config(
    page_title="🏋️‍♂️ Sport Fuel Guide",
    page_icon="⛽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS für Card-Look & Farben
st.markdown("""
<style>
/* Hintergrundfarbe und Schriftart */
body {
  background-color: #F7F9FA;
  font-family: 'Segoe UI', sans-serif;
}
/* Card-Container */
.card {
  background: white;
  border-radius: 15px;
  padding: 1.5rem;
  box-shadow: 0 4px 12px rgba(0,0,0,0.05);
  margin-bottom: 1.5rem;
}
/* Header-Styling */
h1, .big {
  color: #2E3A59;
}
.small {
  color: #6B7A95;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Header
# -----------------------------
st.markdown("<div class='card'><h1>🏋️‍♂️ Sport Fuel Guide</h1><p class='small'>Plan deine Trainings- und Wettkampfernährung smart.</p></div>", unsafe_allow_html=True)

# Optional: Bild dezent einbetten (z.B. als Banner)
st.image("https://images.ctfassets.net/aytpbz9e0sd0/5n9hvfTT9hG7QxgveI7E3W/58dfe5751c5aef4155e60f110fa6f1cd/Peter-Stetina-with-CLIF-SHOT-Energy-Gel-riding-bike.jpg?w=1920",
         use_container_width=True, clamp=True)
st.markdown("---")

# -----------------------------
# Nutzer-Eingaben in Spalten
# -----------------------------
with st.container():
    col1, col2 = st.columns(2)
    with col1:
        gewicht = st.slider("⚖️ Gewicht (kg)", 40, 150, 70, 1)
        alter = st.slider("🎂 Alter (Jahre)", 12, 80, 25, 1)
    with col2:
        groesse = st.slider("📏 Körpergröße (cm)", 140, 210, 175, 1)
        geschlecht = st.selectbox("🚻 Geschlecht", ["Männlich", "Weiblich"])
st.markdown(" ")

# Grundumsatz & Flüssigkeit berechnen
if geschlecht == "Männlich":
    grundumsatz = 66.47 + 13.7 * gewicht + 5.0 * groesse - 6.8 * alter
else:
    grundumsatz = 655.1 + 9.6 * gewicht + 1.8 * groesse - 4.7 * alter
fluessigkeit = gewicht * 0.035

# -----------------------------
# Ausgabe in Metrics-Cards
# -----------------------------
st.markdown("<div class='card'><h2>Deine Werte</h2></div>", unsafe_allow_html=True)
m1, m2 = st.columns(2)
m1.metric(label="🔥 Grundumsatz (kcal/Tag)", value=f"{int(grundumsatz)}")
m2.metric(label="💧 Flüssigkeit (Liter/Tag)", value=f"{fluessigkeit:.2f}")

# -----------------------------
# Navigation-Button
# -----------------------------
st.markdown("---")
st.markdown("<div class='card'><h3>Bereit fürs Workout?</h3></div>", unsafe_allow_html=True)
if st.button("➡️ Zur Vorbereitungsseite"):
    st.session_state.update({
        'gewicht': gewicht,
        'groesse': groesse,
        'alter': alter,
        'geschlecht': geschlecht,
        'grundumsatz': grundumsatz,
        'fluessigkeit': fluessigkeit
    })
    st.experimental_set_query_params(page="vor_workout")
