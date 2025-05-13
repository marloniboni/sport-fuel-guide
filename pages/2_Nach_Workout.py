import os
import random
import streamlit as st
import requests

# ─── 1) API-Key aus Umgebungsvariablen holen ─────────────────────────────────
API_NINJAS_KEY = os.getenv("API_NINJAS_KEY", "")
if not API_NINJAS_KEY:
    st.error("🚨 Bitte setze die Umgebungsvariable API_NINJAS_KEY!")
    st.stop()

HEADERS       = {"X-Api-Key": API_NINJAS_KEY}
RECIPE_URL    = "https://api.api-ninjas.com/v1/recipe"
NUTRITION_URL = "https://api.api-ninjas.com/v1/nutrition"

# ─── 2) Keyword-Listen für jede Mahlzeit ─────────────────────────────────────
MEAL_KEYWORDS = {
    "breakfast": ["eggs", "oatmeal", "pancakes", "smoothie", "yogurt"],
    "lunch":     ["salad", "sandwich", "soup", "wrap", "pasta"],
    "dinner":    ["chicken", "beef", "fish", "stir fry", "curry"]
}

# ─── 3) Hilfsfunktion: Rezepte zu Keyword-Liste holen ────────────────────────
@st.cache_data(show_spinner=False, ttl=3600)
def fetch_recipes_for_meal(keywords: list[str], max_results: int = 3) -> list[dict]:
    recipes = []
    for kw in keywords:
        try:
            resp = requests.get(RECIPE_URL, headers=HEADERS, params={"query": kw}, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            if data:
                # nimm bis zu max_results aus der ersten erfolgreichen Suche
                return data[:max_results]
        except requests.HTTPError:
            continue
    return []

# ─── 4) Kalorien schätzen ────────────────────────────────────────────────────
@st.cache_data(show_spinner=False, ttl=3600)
def estimate_calories(ingredients: str) -> int:
    total = 0
    for part in ingredients.split(";"):
        item = part.strip()
        if not item:
            continue
        try:
            r = requests.get(
                NUTRITION_URL,
                headers=HEADERS,
                params={"query": item},
                timeout=5
            )
            r.raise_for_status()
            items = r.json().get("items", [])
            if items:
                total += int(items[0].get("calories", 0))
        except Exception:
            continue
    return total

# ─── 5) Streamlit-UI ─────────────────────────────────────────────────────────
st.set_page_config(page_title="Meal Plan mit API-Ninjas", layout="wide")

if "grundumsatz" not in st.session_state or "workout_calories" not in st.session_state:
    st.error("Bitte zuerst Home & Vor-Workout ausfüllen.")
    st.stop()

total_cal    = st.session_state.grundumsatz + st.session_state.workout_calories
per_meal_cal = total_cal // 3

st.markdown("---")
st.markdown(f"**Täglicher Gesamtbedarf:** {total_cal} kcal")
st.markdown(f"**Ziel pro Mahlzeit:** ~{per_meal_cal} kcal")

cols = st.columns(3)
meals = [("Frühstück", "breakfast"), ("Mittagessen", "lunch"), ("Abendessen", "dinner")]

for (label, key), col in zip(meals, cols):
    with col:
        st.header(f"{label} (~{per_meal_cal} kcal)")
        recipes = fetch_recipes_for_meal(MEAL_KEYWORDS[key])
        if not recipes:
            st.info("Keine Rezepte gefunden.")
            continue

        for rec in recipes:
            title        = rec.get("title", "–")
            ingredients  = rec.get("ingredients", "")
            instructions = rec.get("instructions", "")
            servings     = rec.get("servings", "")

            kcal_est = estimate_calories(ingredients)

            st.subheader(f"{title} — ca. {kcal_est} kcal")
            if servings:
                st.markdown(f"**Portionen:** {servings}")

            # Zutaten anzeigen
            st.markdown("**Zutaten:**")
            for ing in ingredients.split(";")[:5]:
                st.write(f"- {ing.strip()}")
            if len(ingredients.split(";")) > 5:
                st.write("…")

            # Anleitung
            st.markdown("**Anleitung:**")
            st.write(instructions)
            st.markdown("---")
