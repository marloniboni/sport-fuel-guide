import os
import random
import urllib.parse

import streamlit as st
import requests

# ─── 0) Page config MUST be first Streamlit call ────────────────────────────
st.set_page_config(page_title="Nach Workout", layout="wide")

# ─── 1) Load Edamam Nutrition Analysis credentials ───────────────────────────
EDAMAM_APP_ID       = os.getenv("EDAMAM_APP_ID", "")
EDAMAM_APP_KEY      = os.getenv("EDAMAM_APP_KEY", "")
EDAMAM_ACCOUNT_USER = os.getenv("EDAMAM_ACCOUNT_USER", "")

if not (EDAMAM_APP_ID and EDAMAM_APP_KEY and EDAMAM_ACCOUNT_USER):
    st.error(
        "🚨 Bitte setze in deinen Secrets:\n"
        "• EDAMAM_APP_ID\n"
        "• EDAMAM_APP_KEY\n"
        "• EDAMAM_ACCOUNT_USER"
    )
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
    meal = resp.json().get("meals", [])
    return meal[0] if meal else {}

# ─── 3) Edamam Nutrition Analysis ────────────────────────────────────────────
@st.cache_data(ttl=3600)
def analyze_calories(ingredient_lines: list[str]) -> int | None:
    """
    Calls Edamam Nutrition Analysis API with full ingredient lines.
    Returns total calories or None on failure.
    """
    headers = {"Edamam-Account-User": EDAMAM_ACCOUNT_USER}
    params  = {"app_id": EDAMAM_APP_ID, "app_key": EDAMAM_APP_KEY}
    body    = {"title": "Meal", "ingr": ingredient_lines}

    r = requests.post(EDAMAM_NUTRI_URL, params=params, json=body, headers=headers, timeout=10)
    # If unauthorized or error, bail out
    if r.status_code != 200:
        return None

    data = r.json()
    return data.get("calories")

# ─── 4) Ensure session-state values exist ────────────────────────────────────
if "grundumsatz" not in st.session_state or "workout_calories" not in st.session_state:
    st.error("Bitte zuerst Home & Vor-Workout ausfüllen.")
    st.stop()

# ─── 5) Filter UI ────────────────────────────────────────────────────────────
categories, areas, ingredients = load_mealdb_lists()
c1, c2, c3 = st.columns(3)
with c1:
    choice_cat  = st.selectbox("Kategorie", ["Alle"] + categories)
with c2:
    choice_area = st.selectbox("Region",    ["Alle"] + areas)
with c3:
    choice_ing  = st.selectbox("Zutat",     ["Alle"] + ingredients)

# ─── 6) Fetch MealDB list ────────────────────────────────────────────────────
params = {}
if choice_cat  != "Alle": params["c"] = choice_cat
if choice_area != "Alle": params["a"] = choice_area
if choice_ing  != "Alle": params["i"] = choice_ing

if params:
    query = "&".join(f"{k}={urllib.parse.quote(v)}" for k, v in params.items())
    meals = requests.get(f"https://www.themealdb.com/api/json/v1/1/filter.php?{query}")\
                   .json().get("meals", [])
else:
    meals = []

# ─── 7) Calorie targets ──────────────────────────────────────────────────────
total_cal   = st.session_state.grundumsatz + st.session_state.workout_calories
per_meal_cal = total_cal // 3

st.markdown("---")
st.markdown(f"**Täglicher Gesamtbedarf:** {total_cal} kcal   •   **Ziel pro Mahlzeit:** ~{per_meal_cal} kcal")

# ─── 8) Display 3-column meal plan ───────────────────────────────────────────
cols   = st.columns(3)
labels = ["Frühstück", "Mittagessen", "Abendessen"]

for label, col in zip(labels, cols):
    with col:
        st.subheader(label)
        if not meals:
            st.write("Keine Rezepte gefunden.")
            continue

        # pick up to 3 random recipes
        picks = random.sample(meals, k=min(3, len(meals)))
        for m in picks:
            d = get_meal_details(m["idMeal"])
            if not d:
                continue

            # build ingredient lines for nutrition
            ingr_lines = []
            for i in range(1, 21):
                ing = d.get(f"strIngredient{i}")
                msr = d.get(f"strMeasure{i}")
                if ing and ing.strip():
                    ingr_lines.append(f"{msr.strip()} {ing.strip()}")

            kcal = analyze_calories(ingr_lines)
            title = d.get("strMeal", "Unbekannt")
            if kcal is None:
                st.warning(f"{title} — Kalorien konnten nicht berechnet werden.")
            else:
                st.markdown(f"**{title} — {kcal} kcal**")

            # image
            thumb = d.get("strMealThumb")
            if thumb:
                st.image(thumb, use_container_width=True)

            # ingredients
            st.markdown("**Zutaten:**")
            for line in ingr_lines[:5]:
                st.write(f"- {line}")
            if len(ingr_lines) > 5:
                st.write("…")

            # instructions
            st.markdown("**Anleitung:**")
            st.write(d.get("strInstructions", "Keine Anleitung vorhanden."))
            st.markdown("---")
