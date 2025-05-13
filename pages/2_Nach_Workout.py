import os
import random
import streamlit as st
from requests_oauthlib import OAuth1Session

# ─────────────────────────────────────────────────────────────────────────────
# FatSecret Credentials (bitte in Env-Variablen setzen!)
# ─────────────────────────────────────────────────────────────────────────────
FS_CONSUMER_KEY    = os.getenv("FS_CONSUMER_KEY", "9ced8a2df62549a594700464259c95de")
FS_CONSUMER_SECRET = os.getenv("FS_CONSUMER_SECRET", "dein_consumer_secret")

# FatSecret Endpunkte
FS_API_BASE = "https://platform.fatsecret.com/rest/server.api"

# OAuth1 Session initialisieren
fs = OAuth1Session(
    client_key=FS_CONSUMER_KEY,
    client_secret=FS_CONSUMER_SECRET
)

def fatsecret_request(method: str, params: dict) -> dict:
    """Allgemeine FatSecret-Request (GET) mit OAuth1-Signatur."""
    base_params = {
        "method": method,
        "format": "json",
    }
    r = fs.get(FS_API_BASE, params={**base_params, **params})
    r.raise_for_status()
    return r.json()

# ─────────────────────────────────────────────────────────────────────────────
# Streamlit Setup
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Meal Plan mit FatSecret", layout="wide")
grundumsatz      = st.session_state.get("grundumsatz")
workout_calories = st.session_state.get("workout_calories")
if grundumsatz is None or workout_calories is None:
    st.error("Bitte zuerst Home & Vor-Workout ausfüllen.")
    st.stop()

total_cal   = grundumsatz + workout_calories
per_meal_cal = int(total_cal / 3)

st.markdown("---")
st.markdown(f"**Täglicher Gesamtbedarf:** {total_cal} kcal   •   **Ziel pro Mahlzeit:** ~{per_meal_cal} kcal")

# ─────────────────────────────────────────────────────────────────────────────
# Drei-Spalten: Frühstück, Mittag, Abend
# ─────────────────────────────────────────────────────────────────────────────
cols = st.columns(3)
meal_queries = [("Frühstück", "breakfast"), ("Mittagessen", "lunch"), ("Abendessen", "dinner")]

for (label, query), col in zip(meal_queries, cols):
    with col:
        st.header(f"{label}\n~{per_meal_cal} kcal")

        # 1) Suche nach Rezepten mit Stichwort (liefert bis zu 20 Treffer)
        try:
            search_resp = fatsecret_request("recipe.search", {
                "search_expression": query,
                "max_results": 20
            })
            hits
