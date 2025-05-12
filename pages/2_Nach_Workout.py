import streamlit as st
import requests

# ─────────────────────────────────────────────────────────────────────────────
# Seiten-Config
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Meal Plan",
    page_icon=None,
    layout="wide"
)

# ─────────────────────────────────────────────────────────────────────────────
# 1) Session-State aus Home & Vor-Workout laden
# ─────────────────────────────────────────────────────────────────────────────
grundumsatz      = st.session_state.get("grundumsatz")
workout_calories = st.session_state.get("workout_calories")
if grundumsatz is None or workout_calories is None:
    st.error("Grundumsatz oder Workout-Kalorien fehlen – bitte zuerst Home und Vor-Workout durchlaufen.")
    st.stop()
total_cal = int(grundumsatz + workout_calories)

# ─────────────────────────────────────────────────────────────────────────────
# 2) Spoonacular API-Key
# ─────────────────────────────────────────────────────────────────────────────
API_KEY = "3e9ef3731c664a8ea66b35267f051e27"

# ─────────────────────────────────────────────────────────────────────────────
# 3) Tages-Meal-Plan von Spoonacular holen
# ─────────────────────────────────────────────────────────────────────────────
plan_url = (
    "https://api.spoonacular.com/mealplanner/generate"
    f"?timeFrame=day&targetCalories={total_cal}&apiKey={API_KEY}"
)
plan = requests.get(plan_url).json()
meals = plan.get("meals", [])  # Liste mit 3 Einträgen: breakfast, lunch, dinner

# ─────────────────────────────────────────────────────────────────────────────
# 4) Detail-Infos für jedes Meal abrufen
# ─────────────────────────────────────────────────────────────────────────────
def fetch_recipe_details(recipe_id: int) -> dict:
    """Lädt vollständige Rezept-Infos inkl. Nährwerte, Zutaten und Anleitung."""
    url = (
        f"https://api.spoonacular.com/recipes/{recipe_id}/information"
        f"?includeNutrition=true&apiKey={API_KEY}"
    )
    return requests.get(url
