import streamlit as st
import requests
import urllib

# --- Strava API Credentials ---
CLIENT_ID = "157336"
CLIENT_SECRET = "91427e877cc7921d28692d6a57312a5edcd12325"
REDIRECT_URI = "https://sport-fuel-guide-psxpkf6ezmm76drupopimc.streamlit.app/Nach_Workout_Strava"  # Wichtig!

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

# --- Schritt 2: Authorization Code prüfen ---
query_params = st.query_params

if "code" in query_params and "access_token" not in st.session_state:
    auth_code = query_params["code"][0]

    # --- Token anfordern ---
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
        st.success("✅ Verbindung zu Strava erfolgreich!")
    else:
        st.error("❌ Fehler bei der Strava-Autorisierung. Bitte versuche es erneut.")
        st.json(token_response)

# --- Schritt 3: Aktivitäten abrufen ---
if "access_token" in st.session_state:
    access_token = st.session_state.access_token

    st.subheader("Deine letzten Aktivitäten:")

    activities_response = requests.get(
        "https://www.strava.com/api/v3/athlete/activities",
        headers={"Authorization": f"Bearer {access_token}"}
    ).json()

    # Nur erste 5 Aktivitäten anzeigen
    for activity in activities_response[:5]:
        st.write(f"- {activity['name']} ({activity['type']}) - {activity['distance']/1000:.2f} km, {activity['elapsed_time']//60} min")

else:
    # Falls noch kein Token: Button zum Login
    auth_url = get_strava_authorization_url()
    st.markdown(f"[Hier klicken, um dich mit Strava zu verbinden]({auth_url})")
