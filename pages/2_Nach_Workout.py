import streamlit as st
import requests
import urllib.parse
import random  # neu importieren

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
# 4) Helper: Meal-Details abrufen
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data
def get_meal_details(idMeal: str) -> dict:
    resp = requests.get(f"https://www.themealdb.com/api/json/v1/1/lookup.php?i={idMeal}")
    data = resp.json().get("meals", [])
    return data[0] if data else {}

# ─────────────────────────────────────────────────────────────────────────────
# 5) Kalorien-Übersicht und Verteilung
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(f"**Täglicher Gesamtbedarf:** {int(total_cal)} kcal")

# teile das Tagesziel in drei gleiche Mahlzeiten auf
per_meal_cal = int(total_cal / 3)
st.markdown(f"**Kalorien pro Mahlzeit:** ~{per_meal_cal} kcal")

# ─────────────────────────────────────────────────────────────────────────────
# 6) Empfehlungen: Frühstück, Mittagessen, Abendessen
# ─────────────────────────────────────────────────────────────────────────────
meal_times = [("Frühstück", "Breakfast"), ("Mittagessen", "Lunch"), ("Abendessen", "Dinner")]

for label, _ in meal_times:
    st.subheader(label + f" (~{per_meal_cal} kcal)")
    if not meals:
        st.write("Keine Rezepte gefunden.")
        continue

    # zufälliges Rezept wählen (Sie können hier auch nach Kategorie filtern)
    meal = random.choice(meals)
    details = get_meal_details(meal["idMeal"])
    if not details:
        st.write("Details konnten nicht geladen werden.")
        continue

    st.markdown(f"**{details['strMeal']}**")
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
