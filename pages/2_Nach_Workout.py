import os, streamlit as st, requests

# 1) Load your v1 Recipe Search creds
EDAMAM_APP_ID  = os.getenv("EDAMAM_APP_ID", "")
EDAMAM_APP_KEY = os.getenv("EDAMAM_APP_KEY", "")
if not EDAMAM_APP_ID or not EDAMAM_APP_KEY:
    st.error("Bitte setze EDAMAM_APP_ID und EDAMAM_APP_KEY in deinen Secrets!")
    st.stop()

# 2) Helper: v1 Recipe Search just for ingredients & steps
@st.cache_data(ttl=3600)
def fetch_recipes_v1(query, max_results=3):
    url = "https://api.edamam.com/search"
    params = {
        "q":       query,
        "app_id":  EDAMAM_APP_ID,
        "app_key": EDAMAM_APP_KEY,
        "from":    0,
        "to":      max_results
    }
    r = requests.get(url, params=params, timeout=5)
    r.raise_for_status()
    return [hit["recipe"] for hit in r.json().get("hits", [])]

# 3) Helper: Nutrition Analysis to get calories
@st.cache_data(ttl=3600)
def analyze_nutrition(ingredients):
    url = "https://api.edamam.com/api/nutrition-details"
    params = {"app_id": EDAMAM_APP_ID, "app_key": EDAMAM_APP_KEY}
    body = {"title":"Recipe","ingr": ingredients}
    r = requests.post(url, params=params, json=body, timeout=5)
    r.raise_for_status()
    return r.json().get("calories", None)

# 4) Streamlit UI
st.set_page_config(layout="wide")
if "grundumsatz" not in st.session_state or "workout_calories" not in st.session_state:
    st.error("Bitte zuerst Home & Vor-Workout ausfüllen.")
    st.stop()

total = st.session_state.grundumsatz + st.session_state.workout_calories
per_meal = total // 3

st.markdown(f"**Täglicher Bedarf:** {total} kcal — **pro Mahlzeit:** ~{per_meal} kcal")
cols = st.columns(3)
for label, q in [("Frühstück","breakfast"),("Mittagessen","lunch"),("Abendessen","dinner")]:
    with cols.pop(0):
        st.header(f"{label} (~{per_meal} kcal)")
        try:
            recipes = fetch_recipes_v1(q)
        except Exception as e:
            st.error(f"Recipe Search v1 Fehler: {e}")
            continue
        if not recipes:
            st.info("Keine Rezepte gefunden.")
            continue

        for r in recipes:
            title = r["label"]
            ingr  = r["ingredientLines"]
            instr = r.get("url") or r.get("instructions","–")
            kcal  = analyze_nutrition(ingr)

            st.subheader(f"{title} — {kcal or '?'} kcal")
            st.markdown("**Zutaten:**")
            for i in ingr[:5]: st.write(f"- {i}")
            if len(ingr)>5: st.write("…")
            st.markdown("**Quelle/Anleitung:**")
            st.write(instr)
            st.markdown("---")
