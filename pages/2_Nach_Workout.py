import os
import streamlit as st
import requests

# Must be first
st.set_page_config(page_title="Meal Plan", layout="wide")

# Load credentials
EDAMAM_APP_ID       = os.getenv("EDAMAM_APP_ID", "")
EDAMAM_APP_KEY      = os.getenv("EDAMAM_APP_KEY", "")
EDAMAM_ACCOUNT_USER = os.getenv("EDAMAM_ACCOUNT_USER", "")

if not (EDAMAM_APP_ID and EDAMAM_APP_KEY and EDAMAM_ACCOUNT_USER):
    st.error("Bitte setze EDAMAM_APP_ID, EDAMAM_APP_KEY und EDAMAM_ACCOUNT_USER in deinen Secrets!")
    st.stop()

EDAMAM_NUTRI_URL = "https://api.edamam.com/api/nutrition-details"

@st.cache_data(ttl=3600)
def analyze_calories(ingredient_lines: list[str]) -> int | None:
    headers = {
        "Edamam-Account-User": EDAMAM_ACCOUNT_USER,
        "Content-Type": "application/json"
    }
    params = {"app_id": EDAMAM_APP_ID, "app_key": EDAMAM_APP_KEY}
    body = {"title": "Meal", "ingr": ingredient_lines}

    r = requests.post(EDAMAM_NUTRI_URL, params=params, json=body, headers=headers, timeout=10)

    st.write("🧪 Nutrition API status:", r.status_code)
    try:
        js = r.json()
        st.write("🧪 Nutrition raw JSON:", js)
    except ValueError:
        st.write("🧪 Nutrition raw text:", r.text)

    if r.status_code != 200:
        st.error(f"Nutrition API returned {r.status_code}")
        return None

    return js.get("calories")

# … rest of your app (MealDB & layout) unchanged …
