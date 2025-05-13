import os
import streamlit as st
import requests

# ─── 0) Page config ────────────────────────────────────────────────────────────
st.set_page_config(page_title="Meal Plan", layout="wide")

# ─── 1) Edamam v2 Credentials ─────────────────────────────────────────────────
APP_ID   = os.getenv("EDAMAM_APP_ID", "")
APP_KEY  = os.getenv("EDAMAM_APP_KEY", "")
USER_ID  = os.getenv("EDAMAM_ACCOUNT_USER", "")
if not (APP_ID and APP_KEY and USER_ID):
    st.error("Bitte setze EDAMAM_APP_ID, EDAMAM_APP_KEY und EDAMAM_ACCOUNT_USER in deinen Secrets!")
    st.stop()

V2_URL = "https://api.edamam.com/api/recipes/v2"

# ─── 2) Sidebar: Preferences ──────────────────────────────────────────────────
st.sidebar.markdown("## Allergien & Ernährungspräferenzen")
diet_options = ["balanced", "high-fiber", "high-protein", "low-carb", "low-fat", "low-sodium"]
health_options = [
    "alcohol-free","celery-free","crustacean-free","dairy-free","egg-free",
    "fish-free","fodmap-free","gluten-free","keto-friendly","kosher",
    "low-sugar","lupine-free","Mediterranean","paleo","peanut-free",
    "pescatarian","pork-free","vegetarian","vegan","wheat-free"
]
selected_diets  = st.sidebar.multiselect("Diet labels", diet_options)
selected_health = st.sidebar.multiselect("Health labels", health_options)

# ─── 3) DishType mapping per meal ─────────────────────────────────────────────
DISH_TYPES = {
    "Breakfast": ["Cereals", "Pancake", "Bread"],
    "Lunch":     ["Main course", "Salad", "Sandwiches", "Soup"],
    "Dinner":    ["Main course", "Side dish", "Soup"]
}

# ─── 4) Helper: Fetch recipes ─────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def fetch_recipes(meal_type, diets, healths, max_results=3):
    params = {
        "type":     "public",
        "app_id":   APP_ID,
        "app_key":  APP_KEY,
        "mealType": meal_type,
    }
    # apply diet & health filters
    for d in diets:
        params.setdefault("diet", []).append(d)
    for h in healths:
        params.setdefault("health", []).append(h)
    # apply dishType filter to avoid beverages
    for dt in DISH_TYPES.get(meal_type, []):
        params.setdefault("dishType", []).append(dt)
    # only needed fields
    params["field"] = ["label","image","yield","ingredientLines","calories","totalNutrients"]
    headers = {"Edamam-Account-User": USER_ID}
    r = requests.get(V2_URL, params=params, headers=headers, timeout=5)
    r.raise_for_status()
    hits = r.json().get("hits", [])
    return [h["recipe"] for h in hits][:max_results]

# ─── 5) Check session state ───────────────────────────────────────────────────
if "grundumsatz" not in st.session_state or "workout_calories" not in st.session_state:
    st.error("Bitte zuerst Home & Vor-Workout ausfüllen.")
    st.stop()

total_cal = st.session_state.grundumsatz + st.session_state.workout_calories
per_meal  = total_cal // 3

st.markdown("---")
st.markdown(f"**Täglicher Gesamtbedarf:** {total_cal} kcal  •  **pro Mahlzeit:** ~{per_meal} kcal")

# ─── 6) Display three columns ─────────────────────────────────────────────────
cols  = st.columns(3)
meals = [("Frühstück","Breakfast"), ("Mittagessen","Lunch"), ("Abendessen","Dinner")]

for (label, meal_type), col in zip(meals, cols):
    with col:
        st.subheader(f"{label} (~{per_meal} kcal)")
        try:
            recipes = fetch_recipes(meal_type, selected_diets, selected_health)
        except requests.HTTPError as e:
            st.error(f"Fehler beim Laden der Rezepte: {e}")
            continue

        if not recipes:
            st.info("Keine Rezepte gefunden mit diesen Präferenzen.")
            continue

        for r in recipes:
            title      = r["label"]
            image      = r.get("image")
            total_cals = r.get("calories", 0)
            yield_n    = r.get("yield", 1) or 1
            per_serv   = total_cals / yield_n
            portions   = per_meal / per_serv if per_serv>0 else None

            st.subheader(title)
            if image:
                st.image(image, use_container_width=True)

            # Portionenberechnung
            if portions:
                st.markdown(f"**Portionen:** {portions:.1f} à {per_serv:.0f} kcal = {per_meal} kcal")
            else:
                st.markdown(f"**Kalorien gesamt:** {total_cals} kcal")

            # Makros pro Portion
            nutrients = r.get("totalNutrients", {})
            prot = nutrients.get("PROCNT",{}).get("quantity",0) / yield_n
            fat  = nutrients.get("FAT",{}).get("quantity",0) / yield_n
            carb = nutrients.get("CHOCDF",{}).get("quantity",0) / yield_n
            st.markdown(f"**Makro pro Portion:** {prot:.0f} g P • {fat:.0f} g F • {carb:.0f} g KH")

            # Zutaten
            st.markdown("**Zutaten:**")
            for line in r.get("ingredientLines", [])[:5]:
                st.write(f"- {line}")
            if len(r.get("ingredientLines", [])) > 5:
                st.write("…")

            st.markdown("---")
