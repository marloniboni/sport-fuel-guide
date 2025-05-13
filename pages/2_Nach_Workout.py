import os
import random
import streamlit as st
import requests

# ─── 0) Page config ────────────────────────────────────────────────────────────
st.set_page_config(page_title="Meal Plan", layout="wide")

# ─── 1) Load v2 credentials ───────────────────────────────────────────────────
APP_ID   = os.getenv("EDAMAM_APP_ID", "")
APP_KEY  = os.getenv("EDAMAM_APP_KEY", "")
USER_ID  = os.getenv("EDAMAM_ACCOUNT_USER", "")
if not (APP_ID and APP_KEY and USER_ID):
    st.error("Bitte setze EDAMAM_APP_ID, EDAMAM_APP_KEY und EDAMAM_ACCOUNT_USER in deinen Secrets!")
    st.stop()

V2_URL = "https://api.edamam.com/api/recipes/v2"

# ─── 2) UI: Diet & Health labels ───────────────────────────────────────────────
st.sidebar.markdown("### Ernährungspräferenzen")
diet_options = ["balanced", "high-fiber", "high-protein", "low-carb", "low-fat", "low-sodium"]
health_options = [
    "alcohol-free","celery-free","crustacean-free","dairy-free","egg-free",
    "fish-free","fodmap-free","gluten-free","keto-friendly","kosher",
    "low-sugar","lupine-free","Mediterranean","paleo","peanut-free",
    "pescatarian","pork-free","vegetarian","vegan","wheat-free"
]

selected_diets  = st.sidebar.multiselect("Diet labels", diet_options)
selected_health = st.sidebar.multiselect("Health labels", health_options)

# ─── 3) Fetch recipes via v2 ──────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def fetch_recipes_v2(meal_type: str, diets: list[str], healths: list[str], max_results: int = 3):
    params = {
        "type":     "public",
        "app_id":   APP_ID,
        "app_key":  APP_KEY,
        "mealType": meal_type,
    }
    # Only include q if you want to search text; otherwise omit.
    # params["q"] = meal_type.lower()  

    # add arrays
    for d in diets:
        params.setdefault("diet", []).append(d)
    for h in healths:
        params.setdefault("health", []).append(h)

    # request only the fields we need
    params["field"] = ["label","image","ingredientLines","calories","totalNutrients"]

    headers = {"Edamam-Account-User": USER_ID}
    resp = requests.get(V2_URL, params=params, headers=headers, timeout=5)
    resp.raise_for_status()
    hits = resp.json().get("hits", [])
    return [h["recipe"] for h in hits][:max_results]

# ─── 4) Main app: Calories target and 3 columns ──────────────────────────────
# Assume session_state already has these
if "grundumsatz" not in st.session_state or "workout_calories" not in st.session_state:
    st.error("Bitte zuerst Home & Vor-Workout ausfüllen.")
    st.stop()

total_cal   = st.session_state.grundumsatz + st.session_state.workout_calories
per_meal    = total_cal // 3

st.markdown("---")
st.markdown(f"**Täglicher Gesamtbedarf:** {total_cal} kcal  •  **pro Mahlzeit:** ~{per_meal} kcal")

cols = st.columns(3)
meals = [("Frühstück","Breakfast"), ("Mittagessen","Lunch"), ("Abendessen","Dinner")]

for (label, meal_type), col in zip(meals, cols):
    with col:
        st.subheader(f"{label} (~{per_meal} kcal)")
        try:
            recipes = fetch_recipes_v2(meal_type, selected_diets, selected_health, max_results=3)
        except requests.HTTPError as e:
            st.error(f"Fehler beim Laden: {e}")
            continue

        if not recipes:
            st.info("Keine Rezepte gefunden mit diesen Präferenzen.")
            continue

        for r in recipes:
            title     = r["label"]
            image     = r.get("image")
            calories  = int(r.get("calories",0))
            nutrients = r.get("totalNutrients", {})
            protein   = int(nutrients.get("PROCNT",{}).get("quantity",0))
            fat       = int(nutrients.get("FAT",{}).get("quantity",0))
            carbs     = int(nutrients.get("CHOCDF",{}).get("quantity",0))

            st.subheader(f"{title} — {calories} kcal")
            if image:
                st.image(image, use_container_width=True)

            st.markdown(f"**Makros:** {protein} g P • {fat} g F • {carbs} g KH")
            st.markdown("**Zutaten:**")
            for line in r.get("ingredientLines", [])[:5]:
                st.write(f"- {line}")
            if len(r.get("ingredientLines", [])) > 5:
                st.write("…")
            st.markdown("---")
