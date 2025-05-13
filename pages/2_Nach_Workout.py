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

HEADERS        = {"X-Api-Key": API_NINJAS_KEY}
RECIPE_URL     = "https://api.api-ninjas.com/v1/recipe"
NUTRITION_URL  = "https://api.api-ninjas.com/v1/nutrition"

# ─────────────────────────────────────────────────────────────────────────────
# 2) Hilfsfunktionen
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False, ttl=3600)
def fetch_recipes(query: str, max_results: int = 3) -> list[dict]:
    """
    Holt bis zu `max_results` Rezepte für die Suchanfrage `query`.
    Entfernt unerlaubte Parameter und sliced lokal das Ergebnis.
    """
    resp = requests.get(RECIPE_URL, headers=HEADERS, params={"query": query}, timeout=5)
    resp.raise_for_status()
    data = resp.json()  # Liste von Rezepten
    return data[:max_results]

@st.cache_data(show_spinner=False, ttl=3600)
def estimate_calories(ingredients: str) -> int:
    """
    Splittet die Zutaten-Sektion (durch Semikolon getrennt) und summiert
    die Kalorien über die Nutrition-API.
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
            items = r.json().get("items", [])
            if items:
                total += int(items[0].get("calories", 0))
        except Exception:
            # überspringe fehlerhafte Einträge
            continue
    return total

# ─────────────────────────────────────────────────────────────────────────────
# 3) Streamlit-UI
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

cols    = st.columns(3)
queries = [("Frühstück", "breakfast"), ("Mittagessen", "lunch"), ("Abendessen", "dinner")]

for (label, term), col in zip(queries, cols):
    with col:
        st.header(f"{label} (~{per_meal_cal} kcal)")

        # Rezepte holen (ohne limit/offset)
        try:
            recipes = fetch_recipes(term, max_results=3)
        except Exception as e:
            st.error(f"Fehler beim Laden der Rezepte: {e}")
            continue

        if not recipes:
            st.info("Keine Rezepte gefunden.")
            continue

        # Jedes Rezept anzeigen und Kalorien schätzen
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
