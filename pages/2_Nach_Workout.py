import os
import random
import streamlit as st
import requests
from requests_oauthlib import OAuth1

# ─────────────────────────────────────────────────────────────────────────────
# 1) FatSecret Credentials aus ENV (oder st.secrets)
# ─────────────────────────────────────────────────────────────────────────────
FS_CONSUMER_KEY    = os.getenv("FS_CONSUMER_KEY", "")
FS_CONSUMER_SECRET = os.getenv("FS_CONSUMER_SECRET", "")

if not FS_CONSUMER_KEY or not FS_CONSUMER_SECRET:
    st.error(
        "🚨 Bitte setze deine FatSecret-Credentials:\n"
        "FS_CONSUMER_KEY  = 0339876fd4db22846f5650bf84f5f70886ce2bae\n"
        "FS_CONSUMER_SECRET = 97259\n\n"
        "Entweder als ENV-Vars lokal oder unter Streamlit Cloud → Settings → Secrets."
    )
    st.stop()

auth = OAuth1(FS_CONSUMER_KEY, FS_CONSUMER_SECRET)
FS_API_BASE = "https://platform.fatsecret.com/rest/server.api"

def fatsecret_request(method: str, params: dict) -> dict:
    resp = requests.get(
        FS_API_BASE,
        params={**{"method": method, "format": "json"}, **params},
        auth=auth,
        timeout=10
    )
    resp.raise_for_status()
    return resp.json()

# ─────────────────────────────────────────────────────────────────────────────
# 2) Streamlit-Grundgerüst
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Meal Plan mit FatSecret", layout="wide")

if "grundumsatz" not in st.session_state or "workout_calories" not in st.session_state:
    st.error("Bitte zuerst Home & Vor-Workout ausfüllen.")
    st.stop()

total_cal    = st.session_state.grundumsatz + st.session_state.workout_calories
per_meal_cal = total_cal // 3

st.markdown("---")
st.markdown(f"**Täglicher Gesamtbedarf:** {total_cal} kcal")  
st.markdown(f"**Ziel pro Mahlzeit:** ~{per_meal_cal} kcal")

# ─────────────────────────────────────────────────────────────────────────────
# 3) Drei-Spalten-Layout mit 3 Rezepten + Kalorien
# ─────────────────────────────────────────────────────────────────────────────
cols  = st.columns(3)
meals = [("Frühstück", "breakfast"), ("Mittagessen", "lunch"), ("Abendessen", "dinner")]

for (label, term), col in zip(meals, cols):
    with col:
        st.header(f"{label} (~{per_meal_cal} kcal)")

        # 3.1) recipe.search (max 20 Ergebnisse) → wir wählen 3 zufällige
        try:
            js   = fatsecret_request("recipe.search", {
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

        picks = random.sample(hits, k=min(3, len(hits)))
        for rec in picks:
            # 3.2) recipe.get inkl. calories
            try:
                detail = fatsecret_request("recipe.get", {"recipe_id": rec["recipe_id"]})
                r      = detail["recipe"]
            except Exception as e:
                st.warning(f"Details konnten nicht geladen werden: {e}")
                continue

            name     = r.get("recipe_name")
            calories = r.get("nutrition", {}).get("calories", "unbekannt")
            img = r.get("recipe_images", {}).get("recipe_image", {}).get("image_url")

            st.subheader(f"{name} — {calories} kcal")
            if img:
                st.image(img, use_container_width=True)

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
