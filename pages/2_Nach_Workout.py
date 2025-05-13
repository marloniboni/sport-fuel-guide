import os, streamlit as st, requests

# Load your Meal Planner Developer creds
EDAMAM_APP_ID  = os.getenv("EDAMAM_APP_ID", "")
EDAMAM_APP_KEY = os.getenv("EDAMAM_APP_KEY", "")

if not EDAMAM_APP_ID or not EDAMAM_APP_KEY:
    st.error("Bitte EDAMAM_APP_ID und EDAMAM_APP_KEY in Secrets setzen!")
    st.stop()

@st.cache_data(ttl=3600)
def fetch_recipes_v1(query, max_results=3):
    url = "https://api.edamam.com/search"
    params = {
        "q":       query,
        "app_id":  EDAMAM_APP_ID,
        "app_key": EDAMAM_APP_KEY,
        "from":    0,
        "to":      max_results
    }
    r = requests.get(url, params=params, timeout=5)
    r.raise_for_status()
    return [hit["recipe"] for hit in r.json().get("hits", [])]

# In your 3-column layout:
recipes = fetch_recipes_v1("breakfast")
# each recipe has .get("calories") and .get("totalNutrients")!
