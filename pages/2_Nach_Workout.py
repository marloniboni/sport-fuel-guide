import os
import random
import streamlit as st
import requests

# ─────────────────────────────────────────────────────────────────────────────
# 1) API-Key aus Umgebungsvariablen holen
# ─────────────────────────────────────────────────────────────────────────────
API_NINJAS_KEY = os.getenv("API_NINJAS_KEY", "")
if not API_NINJAS_KEY:
    st.error(
        "🚨 Bitte setze die Umgebungsvariable API_NINJAS_KEY mit deinem API-Ninjas-Key!"
    )
    st.stop()

HEADERS = {"X-Api-Key": API_NINJAS_KEY}
RECIPE_URL   = "https://api.api-ninjas.com/v1/recipe"
NUTRITION_URL = "https://api.api-ninjas.com/v1/nutrition"

# ─────────────────────────────────────────────────────────────────────────────
# 2) Hilfsfunktionen
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def fetch_recipes(query: str, number: int = 3) -> list[dict]:
    """Holt bis zu `number` Rezepte für die Suchanfrage `query`."""
    params = {"query": query, "limit": number}
    resp = requests.get(RECIPE_URL, headers=HEADERS, params=params, timeout=5)
    resp.raise_for_status()
    return resp.json()  # Liste von {title, ingredients, instructions, servings}

@st.cache_data(show_spinner=False)
def estimate_calories(ingredients: str) -> int:
    """
    Zerlegt den `ingredients`-String (Semikolon-separiert),
    fragt jede Zutat einmal an die Nutrition-API und summiert die kcal.
    """
    total = 0
    # Zutaten-Split an Semikolon
    for part in ingredients.split(";"):
        item = part.strip()
        if not item:
            continue
        # Nutrition-Request
        try:
            r = requests.get(NUTRITION_URL, headers=HEADERS, params={"query": item}, timeout=5)
            r.raise_for_status()
            data = r.json()
            # data ist Liste von Einträgen, wir nehmen das erste
            if data:
                total += data[0].get("calories", 0)
        except Exception:
            # im Fehlerfall diese Zutat überspringen
            continue
    return total

# ─────────────────────────────────────────────────────────────────────────────
# 3) Streamlit-Setup
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Meal Plan mit API-Ninjas", layout="wide")

# Simuliere Session-State (in deinem echten Code wird das gesetzt)
# st.session_state["grundumsatz"] = 2000
# st.session_state["workout_calories"] = 500

if "grundumsatz" not in st.session_state or "workout_calories" not in st.session_state:
    st.error("Bitte zuerst Home & Vor-Workout ausfüllen.")
    st.stop()

total_cal    = st.session_state.grundumsatz + st.session_state.workout_calories
per_meal_cal = total_cal // 3

st.markdown("---")
st.markdown(f"**Täglicher Gesamtbedarf:** {total_cal} kcal")  
st.markdown(f"**Ziel pro Mahlzeit:** ~{per_meal_cal} kcal")

# ─────────────────────────────────────────────────────────────────────────────
# 4) Drei-Spalten: Frühstück, Mittag, Abend
# ─────────────────────────────────────────────────────────────────────────────
cols    = st.columns(3)
queries = [("Frühstück", "breakfast"), ("Mittagessen", "lunch"), ("Abendessen", "dinner")]

for (label, term), col in zip(queries, cols):
    with col:
        st.header(f"{label} (~{per_meal_cal} kcal)")

        # 4.1) Rezepte holen
        try:
            recipes = fetch_recipes(term, number=3)
        except Exception as e:
            st.error(f"Fehler beim Laden der Rezepte: {e}")
            continue

        if not recipes:
            st.info("Keine Rezepte gefunden.")
            continue

        # 4.2) Jedes Rezept anzeigen und Kalorien schätzen
        for rec in recipes:
            title        = rec.get("title", "–")
            ingredients  = rec.get("ingredients", "")
            instructions = rec.get("instructions", "")
            servings     = rec.get("servings", "")

            kcal_est = estimate_calories(ingredients)

            st.subheader(f"{title} — ca. {kcal_est} kcal")
            st.markdown(f"**Portionen:** {servings}")
            st.markdown("**Zutaten:**")
            for ing in ingredients.split(";")[:5]:
                st.write(f"- {ing.strip()}")
            if len(ingredients.split(";")) > 5:
                st.write("…")

            st.markdown("**Anleitung:**")
            st.write(instructions)
            st.markdown("---")
