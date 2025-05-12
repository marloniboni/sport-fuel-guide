import streamlit as st
import requests

# Seiten-Config
st.set_page_config(
    page_title="Meal Plan",
    page_icon=None,
    layout="wide"
)

# 1. Session-State-Werte laden
#    Aus Home.py: st.session_state["grundumsatz"]
#    Aus Vor-Workout.py: st.session_state["workout_calories"]
grundumsatz       = st.session_state.get("grundumsatz")
workout_calories  = st.session_state.get("workout_calories")

if grundumsatz is None or workout_calories is None:
    st.error("Grundumsatz oder Workout-Kalorien fehlen – bitte zuerst Home und Vor-Workout durchlaufen.")
    st.stop()

total_cal = grundumsatz + workout_calories

# 2. Funktion, um eine zufällige Mahlzeit zu holen
def get_random_meal():
    resp = requests.get("https://www.themealdb.com/api/json/v1/1/random.php")
    meals = resp.json().get("meals", [])
    return meals[0] if meals else None

# 3. UI: Überschrift und Tabs
st.header(f"Dein Meal Plan – Gesamtbedarf: {int(total_cal)} kcal")

tabs = st.tabs(["Frühstück", "Mittagessen", "Abendessen"])
for name, tab in zip(["Frühstück", "Mittagessen", "Abendessen"], tabs):
    with tab:
        meal = get_random_meal()
        if not meal:
            st.warning("Keine Mahlzeit gefunden.")
            continue

        st.subheader(meal["strMeal"])
        st.image(meal["strMealThumb"], use_container_width=True)
        st.markdown(f"**Kategorie:** {meal['strCategory']}  •  **Herkunft:** {meal['strArea']}")
        st.markdown("**Anleitung:**")
        st.write(meal["strInstructions"])

        # Zutatenliste
        ingredients = []
        for i in range(1, 21):
            ing = meal.get(f"strIngredient{i}")
            meas = meal.get(f"strMeasure{i}")
            if ing and ing.strip():
                ingredients.append(f"- {ing.strip()}: {meas.strip()}")
        st.markdown("**Zutaten:**\n" + "\n".join(ingredients))
