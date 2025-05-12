import streamlit as st
import requests
import urllib.parse

# ─────────────────────────────────────────────────────────────────────────────
# Seiten-Config
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Meal Plan",
    page_icon=None,
    layout="wide"
)

# ─────────────────────────────────────────────────────────────────────────────
# Session-State-Werte laden
# ─────────────────────────────────────────────────────────────────────────────
grundumsatz      = st.session_state.get("grundumsatz")
workout_calories = st.session_state.get("workout_calories")

if grundumsatz is None or workout_calories is None:
    st.error("Grundumsatz oder Workout-Kalorien fehlen – bitte zuerst Home und Vor-Workout durchlaufen.")
    st.stop()

total_cal = grundumsatz + workout_calories

# ─────────────────────────────────────────────────────────────────────────────
# 1) Listen aus TheMealDB laden (Categories, Areas, Ingredients)
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data
def load_mealdb_lists():
    base = "https://www.themealdb.com/api/json/v1/1/list.php"
    cats = requests.get(f"{base}?c=list").json().get("meals", [])
    areas = requests.get(f"{base}?a=list").json().get("meals", [])
    ings = requests.get(f"{base}?i=list").json().get("meals", [])
    return (
        [c["strCategory"]   for c in cats],
        [a["strArea"]       for a in areas],
        [i["strIngredient"] for i in ings]
    )

categories, areas, ingredients = load_mealdb_lists()

# ─────────────────────────────────────────────────────────────────────────────
# 2) Filter-UI
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("### Filtere deine Rezepte")
col1, col2, col3 = st.columns(3)
with col1:
    choice_cat  = st.selectbox("Kategorie", ["Alle"] + categories)
with col2:
    choice_area = st.selectbox("Region",    ["Alle"] + areas)
with col3:
    choice_ing  = st.selectbox("Zutat",     ["Alle"] + ingredients)

# ─────────────────────────────────────────────────────────────────────────────
# 3) Rezepte abrufen
# ─────────────────────────────────────────────────────────────────────────────
# Parameter bauen
params = {}
if choice_cat  != "Alle": params["c"] = choice_cat
if choice_area != "Alle": params["a"] = choice_area
if choice_ing  != "Alle": params["i"] = choice_ing

if params:
    query = "&".join(f"{k}={urllib.parse.quote(v)}" for k, v in params.items())
    url   = f"https://www.themealdb.com/api/json/v1/1/filter.php?{query}"
    meals = requests.get(url).json().get("meals") or []
else:
    meals = []

st.header(f"Gefundene Rezepte: {len(meals)}")

# ─────────────────────────────────────────────────────────────────────────────
# 4) Details der ersten 3 Rezepte anzeigen
# ─────────────────────────────────────────────────────────────────────────────
def get_meal_details(idMeal: str) -> dict:
    resp = requests.get(f"https://www.themealdb.com/api/json/v1/1/lookup.php?i={idMeal}")
    data = resp.json().get("meals", [])
    return data[0] if data else {}

for meal in meals[:3]:
    details = get_meal_details(meal["idMeal"])
    if not details:
        continue

    st.subheader(details["strMeal"])
    st.image(details["strMealThumb"], use_container_width=True)
    st.markdown(
        f"**Kategorie:** {details['strCategory']}  •  "
        f"**Region:** {details['strArea']}"
    )
    st.markdown("**Anleitung:**")
    st.write(details["strInstructions"])

    # Zutatenliste
    ingreds = []
    for i in range(1, 21):
        ing  = details.get(f"strIngredient{i}")
        meas = details.get(f"strMeasure{i}")
        if ing and ing.strip():
            ingreds.append(f"- {meas.strip()} {ing.strip()}")
    st.markdown("**Zutaten:**\n" + "\n".join(ingreds))

# ─────────────────────────────────────────────────────────────────────────────
# 5) Kurze Kalorien-Übersicht
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(f"**Gesamtbedarf:** {int(total_cal)} kcal")
