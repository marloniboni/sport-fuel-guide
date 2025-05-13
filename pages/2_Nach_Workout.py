import os, streamlit as st, requests

EDAMAM_APP_ID  = os.getenv("EDAMAM_APP_ID", "")
EDAMAM_APP_KEY = os.getenv("EDAMAM_APP_KEY", "")
BASE_URL = "https://api.edamam.com/api/recipes/v2"

if not EDAMAM_APP_ID or not EDAMAM_APP_KEY:
    st.error("Bitte EDAMAM_APP_ID und EDAMAM_APP_KEY setzen!")
    st.stop()

# Minimaler Test-Request
resp = requests.get(
    BASE_URL,
    params={
        "type":    "public",
        "q":       "chicken",
        "app_id":  EDAMAM_APP_ID,
        "app_key": EDAMAM_APP_KEY
    },
    timeout=5
)
st.write("Status Code:", resp.status_code)
st.write("Response JSON:", resp.text)
