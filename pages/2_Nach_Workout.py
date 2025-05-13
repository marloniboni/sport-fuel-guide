import os
import random
import streamlit as st
import requests

# ─────────────────────────────────────────────────────────────────────────────
# 1) Load Edamam v2 credentials from Secrets (or ENV)
# ─────────────────────────────────────────────────────────────────────────────
EDAMAM_APP_ID  = os.getenv("EDAMAM_APP_ID", "")
EDAMAM_APP_KEY = os.getenv("EDAMAM_APP_KEY", "")

if not EDAMAM_APP_ID or not EDAMAM_APP_KEY:
    st.error("🚨 Bitte setze EDAMAM_APP_ID und EDAMAM_APP_KEY in deinen Secrets!")
    st.stop()

BASE_URL = "https://api.edamam.com/api/recipes/v2"

# ─────────────────────────────────────────────────────────────────────────────
# 2) Helper: Fetch up to max_results recipes for a given mealType
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def fetch_recipes_v2(meal_type: str, max_results: int = 3) -> list[dict]:
    params = {
        "type":      "public",
        "q":         meal_type,
        "app_id":    EDAMAM_APP_ID,
        "app_key":   EDAMAM_APP_KEY,
        "mealType":  meal_type,
        "field":     ["label", "image", "ingredientLines", "calories", "totalNutrients", "instructions"],
    }
    resp = requests.get(BASE_URL, params=params, timeout=5)
    resp.raise_for_status()
    hits = resp.json().get("hits", [])
    return [h["recipe"] for h in hits][:max_results]

# ─────────────────────────────────────────────────────────────────────────────
# 3) Streamlit layout
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Meal Plan mit Edamam v2", layout="wide")

# Ensure session-state values exist
if "grundumsatz" not in st.session_state or "workout_calories" not in st.session_state:
    st.error("Bitte zuerst Home & Vor-Workout ausfüllen.")
    st.stop()

total_cal    = st.session_state.grundumsatz + st.session_state.workout_calories
per_meal_cal = total_cal // 3

st.markdown("---")
st.markdown(f"**Täglicher Gesamtbedarf:** {total_cal} kcal")  
st.markdown(f"**Ziel pro Mahlzeit:** ~{per_meal_cal} kcal")

cols  = st.columns(3)
meals = [("Frühstück", "Breakfast"), ("Mittagessen", "Lunch"), ("Abendessen", "Dinner")]

for (label, meal_type), col in zip(meals, cols):
    with col:
        st.header(f"{label} (~{per_meal_cal} kcal)")
        try:
            recipes = fetch_recipes_v2(meal_type, max_results=3)
        except Exception as e:
            st.error(f"Fehler beim Laden der Rezepte: {e}")
            continue

        if not recipes:
            st.info("Keine Rezepte gefunden.")
            continue

        for r in recipes:
            title    = r.get("label", "–")
            image    = r.get("image")
            calories = int(r.get("calories", 0))
            nutrients = r.get("totalNutrients", {})

            # Extract macros
            protein = int(nutrients.get("PROCNT", {}).get("quantity", 0))
            fat     = int(nutrients.get("FAT", {}).get("quantity", 0))
            carbs   = int(nutrients.get("CHOCDF", {}).get("quantity", 0))

            st.subheader(f"{title} — {calories} kcal")
            if image:
                st.image(image, use_container_width=True)

            st.markdown(f"**Makros:** {protein} g Protein • {fat} g Fett • {carbs} g Kohlenhydrate")
            st.markdown("**Zutaten:**")
            for line in r.get("ingredientLines", [])[:5]:
                st.write(f"- {line}")
            if len(r.get("ingredientLines", [])) > 5:
                st.write("…")

            st.markdown("**Anleitung:**")
            instructions = r.get("instructions")
            if isinstance(instructions, list):
                for step in instructions:
                    st.write(f"- {step}")
            else:
                st.write(instructions or "Keine Anleitung vorhanden.")
            st.markdown("---")
