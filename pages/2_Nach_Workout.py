import os
import random
import streamlit as st
import requests

# ─── Credentials laden ────────────────────────────────────────────────────────
EDAMAM_APP_ID  = os.getenv("EDAMAM_APP_ID", "")
EDAMAM_APP_KEY = os.getenv("EDAMAM_APP_KEY", "")

if not EDAMAM_APP_ID or not EDAMAM_APP_KEY:
    st.error("Bitte setze EDAMAM_APP_ID und EDAMAM_APP_KEY in deinen Secrets")
    st.stop()

# ─── Helper: v1 Recipe Search ─────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def fetch_recipes_v1(query: str, max_results: int = 3) -> list[dict]:
    url = "https://api.edamam.com/search"
    params = {
        "q":        query,
        "app_id":   EDAMAM_APP_ID,
        "app_key":  EDAMAM_APP_KEY,
        "from":     0,
        "to":       max_results
    }
    r = requests.get(url, params=params, timeout=5)
    r.raise_for_status()
    hits = r.json().get("hits", [])
    return [h["recipe"] for h in hits]

# ─── Dein Streamlit-Layout ────────────────────────────────────────────────────
st.set_page_config(page_title="Meal Plan mit Edamam v1", layout="wide")

if "grundumsatz" not in st.session_state or "workout_calories" not in st.session_state:
    st.error("Bitte zuerst Home & Vor-Workout ausfüllen.")
    st.stop()

total_cal = st.session_state.grundumsatz + st.session_state.workout_calories
per_meal  = total_cal // 3

st.markdown(f"**Daily Need:** {total_cal} kcal — **per meal:** ~{per_meal} kcal")
cols = st.columns(3)
types = [("Frühstück","breakfast"), ("Mittagessen","lunch"), ("Abendessen","dinner")]

for (label, q), col in zip(types, cols):
    with col:
        st.header(f"{label} (~{per_meal} kcal)")
        try:
            recipes = fetch_recipes_v1(q, max_results=3)
        except Exception as e:
            st.error(f"Error loading recipes: {e}")
            continue

        if not recipes:
            st.info("Keine Rezepte gefunden.")
            continue

        for r in recipes:
            title    = r.get("label")
            image    = r.get("image")
            calories = int(r.get("calories",0))
            nutrients = r.get("totalNutrients",{})

            protein = int(nutrients.get("PROCNT",{}).get("quantity",0))
            fat     = int(nutrients.get("FAT",{}).get("quantity",0))
            carbs   = int(nutrients.get("CHOCDF",{}).get("quantity",0))

            st.subheader(f"{title} — {calories} kcal")
            if image:
                st.image(image, use_container_width=True)
            st.markdown(f"**Makros:** {protein} g P • {fat} g F • {carbs} g KH")
            st.markdown("**Zutaten:**")
            for line in r.get("ingredientLines",[])[:5]:
                st.write(f"- {line}")
            st.markdown("**Quelle / Anleitung:**")
            st.write(r.get("url","—"))
            st.markdown("---")
