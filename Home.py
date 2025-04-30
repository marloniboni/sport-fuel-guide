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

# --- Strava API Daten ---
CLIENT_ID = "157336"
CLIENT_SECRET = "91427e877cc7921d28692d6a57312a5edcd12325"
REDIRECT_URI = "https://sport-fuel-guide-psxpkf6ezmm76drupopimc.streamlit.app/"

def get_strava_authorization_url():
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "read,activity:read",
        "approval_prompt": "force",
    }
    return "https://www.strava.com/oauth/authorize?" + urllib.parse.urlencode(params)

query_params = st.query_params

if "access_token" not in st.session_state:

    # Wenn Code vorhanden ist (nach Login)
    if "code" in query_params:
        auth_code = query_params["code"][0]

        token_response = requests.post(
            url="https://www.strava.com/oauth/token",
            data={
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "code": auth_code,
                "grant_type": "authorization_code"
                # ACHTUNG: kein "redirect_uri" hier – das ist der Fix!
            }
        ).json()

        if "access_token" in token_response:
            st.session_state.access_token = token_response["access_token"]
            st.success("✅ Verbindung zu Strava erfolgreich! Weiterleitung...")
            st.switch_page("pages/3_Nach_Workout_Strava.py")
        else:
            st.error("❌ Fehler bei der Strava-Autorisierung")
            st.json(token_response)
            st.stop()

    else:
        login_url = get_strava_authorization_url()
        st.markdown(f"[➡️ Jetzt mit Strava verbinden]({login_url})")
        st.stop()

else:
    st.success("✅ Du bist bereits mit Strava verbunden!")
