import streamlit as st
import requests
import urllib

# --- Strava API Credentials ---
CLIENT_ID = "157336"
CLIENT_SECRET = "91427e877cc7921d28692d6a57312a5edcd12325"
REDIRECT_URI = "https://sport-fuel-guide-psxpkf6ezmm76drupopimc.streamlit.app/Nach_Workout_Strava"

# --- Funktion zum Erzeugen der Autorisierungs-URL ---
def get_strava_authorization_url():
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "read,activity:read",
        "approval_prompt": "force",
    }
    return "https://www.strava.com/oauth/authorize?" + urllib.parse.urlencode(params)

# --- Streamlit Seite ---
st.title("🚴‍♂️ Verbinde dein Strava-Konto")

# --- Hauptlogik ---
query_params = st.query_params

if "access_token" not in st.session_state:

    # Prüfen ob ein Authorization Code in der URL ist
    if "code" in query_params:
        auth_code = query_params["code"][0]

        # --- Zugriffstoken anfordern ---
        token_response = requests.post(
            url="https://www.strava.com/oauth/token",
            data={
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "code": auth_code,
                "grant_type": "authorization_code",
            }
        ).json()

        if "access_token" in token_response:
            st.session_state.access_token = token_response["access_token"]
            st.success("✅ Verbindung erfolgreich!")
        else:
            st.error("❌ Fehler bei der Strava-Autorisierung.")
            st.json(token_response)
            # Keine weiteren Schritte möglich
            st.stop()

    else:
        # Kein Authorization Code vorhanden – Login anbieten
        auth_url = get_strava_authorization_url()
        st.markdown(f"[➡️ Hier klicken, um dich mit Strava zu verbinden]({auth_url})")
        st.stop()

# --- Zugriffstoken vorhanden: Aktivitäten abrufen ---
access_token = st.session_state.access_token

st.subheader("Deine letzten Aktivitäten:")

activities_response = requests.get(
    "https://www.strava.com/api/v3/athlete/activities",
    headers={"Authorization": f"Bearer {access_token}"}
).json()

# Prüfen ob Aktivitäten korrekt geladen wurden
if isinstance(activities_response, list):
    for activity in activities_response[:5]:
        st.write(f"- {activity['name']} ({activity['type']}) - {activity['distance']/1000:.2f} km, {activity['elapsed_time']//60} min")
else:
    st.error("❌ Fehler beim Laden der Aktivitäten.")
    st.json(activities_response)
