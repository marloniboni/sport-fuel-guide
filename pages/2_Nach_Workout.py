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
    """
    Holt bis zu `number` Rezepte für die Suchanfrage `query`, indem
    jeweils ein Rezept mit steigendem offset abgefragt wird.
    """
    recipes = []
    for offset in range(number):
        params = {"query": query, "offset": offset}
        resp = requests.get(RECIPE_URL, headers=HEADERS, params=params, timeout=5)
        # Bei 400 könnte offset zu groß sein oder limit genutzt worden sein:
        resp.raise_for_status()
        data = resp.json()
        if not data:
            break
        # Data ist eine Liste; nehmen ersten Eintrag
        recipes.append(data[0])
    return recipes

@st.cache_data(show_spinner=False)
def estimate_calories(ingredients: str) -> int:
    """
    Zerlegt `ingredients` (Semikolon-separiert) und
    summiert die Kalorien jedes Items via Nutrition-API.
    """
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
            data = r.json()
            # data ist Liste von Nutrition-Infos
            if data:
                total += int(data[0].get("calories", 0))
        except Exception:
            continue
    return total

# ─────────────────────────────────────────────────────────────────────────────
# 3) Streamlit-Setup
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Meal Plan mit API-Ninjas", layout="wide")

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

        # 4.1) Rezepte holen (offset-basiert statt limit)
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
            if servings:
                st.markdown(f"**Portionen:** {servings}")
            st.markdown("**Zutaten:**")
            for ing in ingredients.split(";")[:5]:
                st.write(f"- {ing.strip()}")
            if len(ingredients.split(";")) > 5:
                st.write("…")

            st.markdown("**Anleitung:**")
            st.write(instructions)
            st.markdown("---")
