import random
import streamlit as st
import requests
from requests_oauthlib import OAuth1

# ─────────────────────────────────────────────────────────────────────────────
# FatSecret-Credentials aus streamlit secrets
# ─────────────────────────────────────────────────────────────────────────────
secrets = st.secrets["fatsecret"]
FS_CONSUMER_KEY    = secrets["consumer_key"]
FS_CONSUMER_SECRET = secrets["consumer_secret"]

# OAuth1-Objekt
auth = OAuth1(FS_CONSUMER_KEY, FS_CONSUMER_SECRET)

FS_API_BASE = "https://platform.fatsecret.com/rest/server.api"

def fatsecret_request(method: str, params: dict) -> dict:
    payload = {
        "method": method,
        "format": "json",
        **params
    }
    resp = requests.get(FS_API_BASE, params=payload, auth=auth, timeout=10)
    resp.raise_for_status()
    return resp.json()

# ─────────────────────────────────────────────────────────────────────────────
# Streamlit-Grundgerüst
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Meal Plan mit FatSecret", layout="wide")

if "grundumsatz" not in st.session_state or "workout_calories" not in st.session_state:
    st.error("Bitte zuerst Home & Vor-Workout ausfüllen.")
    st.stop()

total_cal   = st.session_state.grundumsatz + st.session_state.workout_calories
per_meal_cal = total_cal // 3

st.markdown("---")
st.markdown(f"**Täglicher Gesamtbedarf:** {total_cal} kcal")
st.markdown(f"**Ziel pro Mahlzeit:** ~{per_meal_cal} kcal")

cols = st.columns(3)
queries = [("Frühstück", "breakfast"), ("Mittagessen", "lunch"), ("Abendessen", "dinner")]

for (label, term), col in zip(queries, cols):
    with col:
        st.header(f"{label} (~{per_meal_cal} kcal)")

        # Rezeptsuche
        try:
            js = fatsecret_request("recipe.search", {
                "search_expression": term,
                "max_results": 20
            })
            hits = js.get("recipes", {}).get("recipe", [])
        except Exception as e:
            st.error(f"Fehler bei recipe.search: {e}")
            continue

        if not hits:
            st.info("Keine Rezepte gefunden.")
            continue

        for rec in random.sample(hits, k=min(3, len(hits))):
            try:
                detail = fatsecret_request("recipe.get", {"recipe_id": rec["recipe_id"]})
                r = detail.get("recipe", {})
            except Exception as e:
                st.warning(f"Details konnten nicht geladen werden: {e}")
                continue

            name     = r.get("recipe_name", "–")
            kcal     = r.get("nutrition", {}).get("calories", "unbekannt")
            img_url  = r.get("recipe_images", {}).get("recipe_image", {}).get("image_url")

            st.subheader(f"{name} — {kcal} kcal")
            if img_url:
                st.image(img_url, use_container_width=True)
            # Zutaten
            ingreds = [i["food_description"] for i in r.get("ingredients", {}).get("ingredient", [])]
            st.markdown("**Zutaten:**")
            for ing in ingreds[:5]:
                st.write(f"- {ing}")
            if len(ingreds) > 5:
                st.write("…")
            # Anleitung
            if r.get("directions"):
                st.markdown("**Anleitung:**")
                st.write(r["directions"])
            st.markdown("---")
