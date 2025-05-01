import streamlit as st

st.title("📊 Analyse deiner Strava-Aktivität")

# Prüfen, ob eine Aktivität vorhanden ist
if "selected_activity" not in st.session_state:
    st.error("⚠️ Keine Aktivität ausgewählt. Bitte kehre zur Startseite zurück und wähle eine Aktivität.")
    st.page_link("Home", label="Zurück zur Home-Seite", icon="🏠")
    st.stop()

activity = st.session_state["selected_activity"]

# Basisinfos
st.subheader(f"🏃 Aktivität: {activity['name']}")
st.write(f"📅 Datum: `{activity['start_date_local']}`")
st.write(f"⏱️ Dauer: `{activity['elapsed_time'] // 60} min`")
st.write(f"📏 Distanz: `{activity['distance']/1000:.2f} km`")
st.write(f"🔥 Kalorien: `{activity.get('kilojoules', 'k.A.')}`")
st.write(f"🏔️ Höhenmeter: `{activity.get('total_elevation_gain', 0)} m`")
st.write(f"💓 Durchschnittspuls: `{activity.get('average_heartrate', 'nicht verfügbar')}`")

# Optionale Erweiterung: Geschwindigkeit berechnen
if activity["elapsed_time"] > 0:
    speed = (activity["distance"] / activity["elapsed_time"]) * 3.6  # m/s → km/h
    st.write(f"🚴 Durchschnittsgeschwindigkeit: `{speed:.2f} km/h`")

# Optional: zur Startseite zurück
st.markdown("---")
if st.button("🏠 Zurück zur Home-Seite"):
    st.switch_page("Home")
