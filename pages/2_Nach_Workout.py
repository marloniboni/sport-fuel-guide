import os
import streamlit as st
import requests

# ─── Load credentials ───────────────────────────────────────────────────────
EDAMAM_APP_ID  = os.getenv("EDAMAM_APP_ID", "")
EDAMAM_APP_KEY = os.getenv("EDAMAM_APP_KEY", "")
if not EDAMAM_APP_ID or not EDAMAM_APP_KEY:
    st.error("Bitte setze EDAMAM_APP_ID und EDAMAM_APP_KEY in deinen Secrets!")
    st.stop()

# ─── Helper to fetch recipes via v1 Search ─────────────────────────────────
@st.cache_data(ttl=3600)
def fetch_recipes(query: str, max_results: int = 3):
    url = "https://api.edamam.com/search"
    params = {
        "q":       query,
        "app_id":  EDAMAM_APP_ID,
        "app_key": EDAMAM_APP_KEY,
        "from":    0,
        "to":      max_results
    }
    resp = requests.get(url, params=params, timeout=5)
    resp.raise_for_status()
    hits = resp.json().get("hits", [])
    return [hit["recipe"] for hit in hits]

# ─── Streamlit layout ───────────────────────────────────────────────────────
st.set_page_config(layout="wide")
if "grundumsatz" not in st.session_state or "workout_calories" not in st.session_state:
    st.error("Bitte zuerst Home & Vor-Workout ausfüllen.")
    st.stop()

total = st.session_state.grundumsatz + st.session_state.workout_calories
per_meal = total // 3

st.markdown(f"**Täglicher Bedarf:** {total} kcal — **pro Mahlzeit:** ~{per_meal} kcal")
cols = st.columns(3)
queries = [("Frühstück", "breakfast"), ("Mittagessen", "lunch"), ("Abendessen", "dinner")]

for (label, q), col in zip(queries, cols):
    with col:
        st.header(f"{label} (~{per_meal} kcal)")
        try:
            recipes = fetch_recipes(q, max_results=3)
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

            protein = int(nutrients.get("PROCNT", {}).get("quantity", 0))
            fat     = int(nutrients.get("FAT", {}).get("quantity", 0))
            carbs   = int(nutrients.get("CHOCDF", {}).get("quantity", 0))

            st.subheader(f"{title} — {calories} kcal")
            if image:
                st.image(image, use_container_width=True)
            st.markdown(f"**Makros:** {protein} g Protein • {fat} g Fett • {carbs} g KH")
            st.markdown("**Zutaten:**")
            for line in r.get("ingredientLines", [])[:5]:
                st.write(f"- {line}")
            st.markdown("**Quelle:**")
            st.write(r.get("url", "–"))
            st.markdown("---")
