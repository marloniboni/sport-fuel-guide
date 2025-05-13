import os
import random
import streamlit as st
import requests
import urllib.parse

# ─── 0) Must be the first Streamlit command! ────────────────────────────────
st.set_page_config(page_title="Meal Plan", layout="wide")

# ─── 1) Load Edamam Nutrition creds ──────────────────────────────────────────
EDAMAM_APP_ID  = os.getenv("EDAMAM_APP_ID", "")
EDAMAM_APP_KEY = os.getenv("EDAMAM_APP_KEY", "")
if not EDAMAM_APP_ID or not EDAMAM_APP_KEY:
    st.error("Bitte setze EDAMAM_APP_ID und EDAMAM_APP_KEY in deinen Secrets!")
    st.stop()

EDAMAM_NUTRI_URL = "https://api.edamam.com/api/nutrition-details"

# ─── 2) MealDB helpers ───────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_mealdb_lists():
    base = "https://www.themealdb.com/api/json/v1/1/list.php"
    cats  = requests.get(f"{base}?c=list").json().get("meals", [])
    areas = requests.get(f"{base}?a=list").json().get("meals", [])
    ings  = requests.get(f"{base}?i=list").json().get("meals", [])
    return (
        [c["strCategory"]   for c in cats],
        [a["strArea"]       for a in areas],
        [i["strIngredient"] for i in ings]
    )

@st.cache_data(ttl=3600)
def get_meal_details(idMeal: str) -> dict:
    resp = requests.get(f"https://www.themealdb.com/api/json/v1/1/lookup.php?i={idMeal}")
    m = resp.json().get("meals", [])
    return m[0] if m else {}

# ─── 3) Edamam Nutrition Analysis ────────────────────────────────────────────
@st.cache_data(ttl=3600)
def analyze_calories(ingredient_lines: list[str]) -> int | None:
    """
    Calls Edamam Nutrition Analysis endpoint with full ingredient lines.
    Returns calories or None on failure.
    """
    r = requests.post(
        EDAMAM_NUTRI_URL,
        params={"app_id": EDAMAM_APP_ID, "app_key": EDAMAM_APP_KEY},
        json={"title": "Meal", "ingr": ingredient_lines},
        timeout=10
    )
    # Debug output for status and body
    st.write("🧪 Nutrition API status:", r.status_code)
    try:
        js = r.json()
        st.write("🧪 Nutrition raw JSON:", js)
    except ValueError:
        st.write("🧪 Nutrition raw text:", r.text)

    if r.status_code != 200:
        st.error(f"Nutrition API returned {r.status_code}")
        return None

    return js.get("calories", None)

# ─── 4) Streamlit App ────────────────────────────────────────────────────────
# Ensure session-state values exist
if "grundumsatz" not in st.session_state or "workout_calories" not in st.session_state:
    st.error("Bitte zuerst Home & Vor-Workout ausfüllen.")
    st.stop()

# Filter UI
categories, areas, ingredients = load_mealdb_lists()
col1, col2, col3 = st.columns(3)
with col1:
    cat = st.selectbox("Kategorie", ["Alle"] + categories)
with col2:
    area = st.selectbox("Region", ["Alle"] + areas)
with col3:
    ing = st.selectbox("Zutat", ["Alle"] + ingredients)

# Build MealDB query
params = {}
if cat != "Alle":  params["c"] = cat
if area != "Alle": params["a"] = area
if ing != "Alle":  params["i"] = ing

if params:
    q = "&".join(f"{k}={urllib.parse.quote(v)}" for k, v in params.items())
    meals = requests.get(f"https://www.themealdb.com/api/json/v1/1/filter.php?{q}").json().get("meals", [])
else:
    meals = []

# Calorie targets
total     = st.session_state.grundumsatz + st.session_state.workout_calories
per_meal  = total // 3
st.markdown(f"**Täglicher Bedarf:** {total} kcal  •  **pro Mahlzeit:** ~{per_meal} kcal")
st.markdown("---")

# Show 3 columns of recipes
cols   = st.columns(3)
labels = ["Frühstück", "Mittagessen", "Abendessen"]

for label, col in zip(labels, cols):
    with col:
        st.subheader(label)
        if not meals:
            st.write("Keine Rezepte gefunden.")
            continue

        picks = random.sample(meals, k=min(3, len(meals)))
        for meal in picks:
            d = get_meal_details(meal["idMeal"])
            if not d:
                continue

            # Build ingredient lines
            ingr_lines = [
                f"{d[f'strMeasure{i}'].strip()} {d[f'strIngredient{i}'].strip()}"
                for i in range(1, 21)
                if d.get(f"strIngredient{i}") and d[f"strIngredient{i}"].strip()
            ]

            kcal = analyze_calories(ingr_lines)
            if kcal is None:
                st.warning("Kalorien konnten nicht berechnet werden.")
            else:
                st.markdown(f"**{d['strMeal']} — {kcal} kcal**")

            if thumb := d.get("strMealThumb"):
                st.image(thumb, use_container_width=True)

            st.markdown("**Zutaten:**")
            for line in ingr_lines[:5]:
                st.write(f"- {line}")
            if len(ingr_lines) > 5:
                st.write("…")

            st.markdown("**Anleitung:**")
            st.write(d.get("strInstructions", "Keine Anleitung vorhanden."))
            st.markdown("---")
