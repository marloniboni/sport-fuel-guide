import os
import random
import streamlit as st
import requests
from requests_oauthlib import OAuth1

# ─── 1) FatSecret-Credentials aus ENV holen ──────────────────────────────────
FS_CONSUMER_KEY    = os.getenv("FS_CONSUMER_KEY", "")
FS_CONSUMER_SECRET = os.getenv("FS_CONSUMER_SECRET", "")

if not FS_CONSUMER_KEY or not FS_CONSUMER_SECRET:
    st.error("Bitte setze FS_CONSUMER_KEY und FS_CONSUMER_SECRET in den Secrets!")
    st.stop()

auth = OAuth1(FS_CONSUMER_KEY, FS_CONSUMER_SECRET)
FS_API_BASE = "https://platform.fatsecret.com/rest/server.api"

def fatsecret_request(method: str, params: dict) -> dict:
    r = requests.get(FS_API_BASE, params={"method": method, "format": "json", **params}, auth=auth)
    r.raise_for_status()
    return r.json()

# ─── 2) Keyword-Mapping pro Mahlzeit ────────────────────────────────────────
KEYWORDS = {
    "Frühstück": ["porridge", "pancakes", "eggs", "muesli", "yogurt"],
    "Mittagessen": ["salad", "sandwich", "soup", "wrap", "rice"],
    "Abendessen": ["pasta", "chicken", "fish", "stir fry", "curry"]
}

# ─── 3) Rezepte zu Keyword-Liste holen ─────────────────────────────────────
@st.cache_data(ttl=3600)
def fetch_recipes(meal_label: str, max_results: int = 3) -> list[dict]:
    for kw in KEYWORDS[meal_label]:
        try:
            js = fatsecret_request("recipe.search", {
                "search_expression": kw,
                "max_results": "20"  # als String übergeben
            })
            hits = js.get("recipes", {}).get("recipe", [])
            if hits:
                return hits[:max_results]
        except Exception:
            continue
    return []

# ─── 4) Streamlit-Layout ───────────────────────────────────────────────────
st.set_page_config(page_title="Meal Plan mit FatSecret", layout="wide")

if "grundumsatz" not in st.session_state or "workout_calories" not in st.session_state:
    st.error("Bitte zuerst Home & Vor-Workout ausfüllen.")
    st.stop()

total_cal    = st.session_state.grundumsatz + st.session_state.workout_calories
per_meal_cal = total_cal // 3

st.markdown("---")
st.markdown(f"**Täglicher Gesamtbedarf:** {total_cal} kcal")  
st.markdown(f"**Ziel pro Mahlzeit:** ~{per_meal_cal} kcal")

cols = st.columns(3)
for label, col in zip(KEYWORDS.keys(), cols):
    with col:
        st.header(f"{label} (~{per_meal_cal} kcal)")
        recipes = fetch_recipes(label)
        if not recipes:
            st.info("Keine Rezepte gefunden.")
            continue

        for rec in recipes:
            # Detail laden
            detail = fatsecret_request("recipe.get", {"recipe_id": rec["recipe_id"]})
            r = detail.get("recipe", {})
            name     = r.get("recipe_name", "–")
            calories = r.get("nutrition", {}).get("calories", "unbekannt")
            img      = r.get("recipe_images", {}).get("recipe_image", {}).get("image_url")
            
            st.subheader(f"{name} — {calories} kcal")
            if img:
                st.image(img, use_container_width=True)
            
            # Zutaten
            ingreds = [i["food_description"] for i in r.get("ingredients", {}).get("ingredient", [])]
            st.markdown("**Zutaten:**")
            for ing in ingreds[:5]:
                st.write(f"- {ing}")
            if len(ingreds) > 5:
                st.write("…")
            
            # Anleitung
            if r.get("directions"):
                st.markdown("**Anleitung:**")
                st.write(r["directions"])
            st.markdown("---")
