import streamlit as st
import requests
import urllib

# --- Titel ---
st.title("🏡 Sport Fuel Guide")
st.markdown("Willkommen! Diese App hilft dir bei der Planung deiner Trainings- und Wettkampfernährung.")

# --- Bild ---
st.image("https://images.ctfassets.net/aytpbz9e0sd0/5n9hvfTT9hG7QxgveI7E3W/58dfe5751c5aef4155e60f110fa6f1cd/Peter-Stetina-with-CLIF-SHOT-Energy-Gel-riding-bike.jpg?w=1920", use_container_width=800)

st.markdown("<p style='font-weight:bold; font-size:1.2rem; margin-top:-0.5rem;'>Geben Sie Ihre Daten ein👇</p>", unsafe_allow_html=True)

# --- Eingaben ---
gewicht = st.slider("Gewicht (in kg)", min_value=40, max_value=150, value=70, step=1)
groesse = st.slider("Körpergröße (in cm)", min_value=140, max_value=210, value=175, step=1)
alter = st.slider("Alter (in Jahren)", min_value=12, max_value=80, value=25, step=1)
geschlecht = st.selectbox("Geschlecht", ["Männlich", "Weiblich"])

# --- Berechnung Grundumsatz & Flüssigkeit ---
if geschlecht == "Männlich":
    grundumsatz = 66.47 + (13.7 * gewicht) + (5.0 * groesse) - (6.8 * alter)
else:
    grundumsatz = 655.1 + (9.6 * gewicht) + (1.8 * groesse) - (4.7 * alter)

fluessigkeit = gewicht * 0.035

# --- Ausgabe ---
st.markdown("---")
st.subheader("🧮 Deine berechneten Werte:")
st.image("https://sp-ao.shortpixel.ai/client/to_webp,q_glossy,ret_img/https://eatmyride.com/wp-content/uploads/2023/01/garmin_balancer_new-1.png", use_container_width=25)
st.markdown("<p style='font-weight:bold; font-size:1.2rem; margin-top:-0.5rem;'>Mit deinen Zahlen hört das Rätselraten auf 💪</p>", unsafe_allow_html=True)
st.write(f"**Grundumsatz**: ca. `{int(grundumsatz)} kcal` pro Tag")
st.write(f"**Täglicher Flüssigkeitsbedarf**: ca. `{fluessigkeit:.2f} Liter`")
st.info("Diese Werte gelten als Basis – dein Bedarf variiert je nach Aktivität, Temperatur und Trainingsziel.")

# --- Speichern ---
st.session_state.gewicht = gewicht
st.session_state.grundumsatz = grundumsatz
st.session_state.fluessigkeit = fluessigkeit

# --- Navigation zur Vorbereitungsseite ---
st.markdown("---")
st.markdown("### 🏋️ Hast du ein Workout geplant?")
if st.button("➡️ Ja, gehe zur Vorbereitungsseite"):
    st.switch_page("pages/1_Vor Workout.py")

# --- STRAVA LOGIN ---
st.markdown("---")
st.markdown("### 🚴‍♂️ Oder möchtest du deine letzte Aktivität von Strava analysieren?")

import streamlit as st
import requests
import urllib

# --- Strava API Credentials ---
CLIENT_ID = "157336"
CLIENT_SECRET = "4531907d956f3c5c00919538d514970173156c6a"
REDIRECT_URI = "https://sport-fuel-guide-psxpkf6ezmm76drupopimc.streamlit.app"  # Beispiel: https://nach-workout.streamlit.app/

# --- Schritt 1: Nutzer zu Strava weiterleiten ---
def get_strava_authorization_url():
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "read,activity:read",
        "approval_prompt": "force",
    }
    url = "https://www.strava.com/oauth/authorize?" + urllib.parse.urlencode(params)
    return url

# --- Streamlit Seite ---
st.title("🚴‍♂️ Verbinde dein Strava-Konto")

if "auth_code" not in st.session_state:
    auth_url = get_strava_authorization_url()
    st.markdown(f"[Hier klicken, um dich mit Strava zu verbinden]({auth_url})")
    
    # Checke ob ein Code im URL-Parameter ist
query_params = st.query_params
if "code" in query_params:
    st.session_state.auth_code = query_params["code"][0]
    st.rerun()

else:
    st.success("✅ Verbindung zu Strava erfolgreich!")

    # --- Schritt 2: Token anfordern ---
    token_response = requests.post(
        url="https://www.strava.com/oauth/token",
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": st.session_state.auth_code,
            "grant_type": "authorization_code",
        }
    ).json()

    access_token = token_response["access_token"]
    st.session_state.access_token = access_token

    # --- Schritt 3: Aktivitäten abrufen ---
    activities_response = requests.get(
        "https://www.strava.com/api/v3/athlete/activities",
        headers={"Authorization": f"Bearer {access_token}"}
    ).json()

    st.subheader("Deine letzten Aktivitäten:")
    
    # Nur erste 5 Aktivitäten anzeigen
    for activity in activities_response[:5]:
        st.write(f"- {activity['name']} ({activity['type']}) - {activity['distance']/1000:.2f} km, {activity['elapsed_time']//60} min")

    # Hier könnten wir weitermachen: Aktivität auswählen, analysieren usw.
