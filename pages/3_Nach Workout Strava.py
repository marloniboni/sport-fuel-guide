import streamlit as st
import requests
import urllib

# --- Strava API Credentials ---
CLIENT_ID = "157336"
CLIENT_SECRET = "91427e877cc7921d28692d6a57312a5edcd12325"
REDIRECT_URI = "https://sport-fuel-guide-psxpkf6ezmm76drupopimc.streamlit.app/"  # Wichtig: Hauptseite!

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

# Schritt: Prüfen, ob Auth-Code da
query_params = st.query_params

if "code" in query_params and "auth_code" not in st.session_state:
    st.session_state.auth_code = query_params["code"][0]
    st.success("✅ Verbindung zu Strava erfolgreich!")

    # --- Token anfordern ---
    token_response = requests.post(
        url="https://www.strava.com/oauth/token",
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": st.session_state.auth_code,
            "grant_type": "authorization_code",
        }
    ).json()

    if "access_token" in token_response:
        access_token = token_response["access_token"]
        st.session_state.access_token = access_token

        # --- UND JETZT direkt auf "Nach Workout Strava" Seite springen! ---
        st.switch_page("pages/3_Nach_Workout_Strava.py")
    else:
        st.error("❌ Fehler bei der Strava-Autorisierung. Bitte versuche es erneut.")
        st.json(token_response)

# Falls noch kein Code: Login anbieten
if "auth_code" not in st.session_state:
    auth_url = get_strava_authorization_url()
    st.markdown(f"[Hier klicken, um dich mit Strava zu verbinden]({auth_url})")

