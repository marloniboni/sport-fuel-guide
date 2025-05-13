import os
import random
import streamlit as st
from requests_oauthlib import OAuth1Session

# ─────────────────────────────────────────────────────────────────────────────
# FatSecret Credentials (bitte in deinen Umgebungsvariablen setzen!)
# ─────────────────────────────────────────────────────────────────────────────
FS_CONSUMER_KEY    = os.getenv("FS_CONSUMER_KEY", "9ced8a2df62549a594700464259c95de")
FS_CONSUMER_SECRET = os.getenv("FS_CONSUMER_SECRET", "<dein_consumer_secret>")

# ─────────────────────────────────────────────────────────────────────────────
# FatSecret OAuth1-Session initialisieren
# ─────────────────────────────────────────────────────────────────────────────
fs = OAuth1Session(
    client_key=FS_CONSUMER_KEY,
    client_secret=FS_CONSUMER_SECRET
)

FS_API_BASE = "https://platform.fatsecret.com/rest/server.api"

def fatsecret_request(method: str, params: dict) -> dict:
    """
    Generische FatSecret-GET-Anfrage mit OAuth1-Signatur.
    Liefert das JSON-Response-Dict zurück.
    """
    base_params = {
        "method": method,
        "format": "json"
    }
    response = fs.get(FS_API_BASE, params={**base_params, **params})
    response.raise_for_status()
    return response.json()

# ─────────────────────────────────────────────────────────────────────────────
# Streamlit-Setup
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Meal Plan mit FatSecret", layout="wide")

try:
    grundumsatz      = st.session_state["grundumsatz"]
    workout_calories = st.session_state["workout_calories"]
except KeyError:
    st.error("Bitte zuerst Home & Vor-Workout ausfüllen.")
    st.stop()

total_cal   = grundumsatz + workout_calories
per_meal_cal = total_cal // 3

st.markdown("---")
st.markdown(f"**Täglicher Gesamtbedarf:** {total_cal} kcal")
st.markdown(f"**Ziel pro Mahlzeit:** ~{per_meal_cal} kcal")

# ─────────────────────────────────────────────────────────────────────────────
# Drei-Spalten-Layout: Frühstück, Mittagessen, Abendessen
# ─────────────────────────────────────────────────────────────────────────────
cols = st.columns(3)
queries = [("Frühstück", "breakfast"), ("Mittagessen", "lunch"), ("Abendessen", "dinner")]

for (label, search_term), col in zip(queries, cols):
    with col:
        st.header(f"{label} (~{per_meal_cal} kcal)")
        try:
            # 1) Suche Rezepte
            search_json = fatsecret_request("recipe.search", {
                "search_expression": search_term,
                "max_results": 20
            })
            hits = search_json.get("recipes", {}).get("recipe", [])
        except Exception as e:
            st.error(f"Fehler bei FatSecret-Suche: {e}")
            continue

        if not hits:
            st.write("Keine Rezepte gefunden.")
            continue

        # 2) Wähle bis zu 3 zufällige Rezepte
        picks = random.sample(hits, k=min(3, len(hits)))

        for rec in picks:
            try:
                # 3) Hole Detail-Infos
                detail_json = fatsecret_request("recipe.get", {"recipe_id": rec["recipe_id"]})
                recipe = detail_json.get("recipe", {})
            except Exception as e:
                st.warning(f"Details konnten nicht geladen werden: {e}")
                continue

            name       = recipe.get("recipe_name", "Unbekannt")
            calories   = recipe.get("nutrition", {}).get("calories", "unbekannt")
            image_url  = recipe.get("recipe_images", {}).get("recipe_image", {}).get("image_url", None)
            ingredients = [i.get("food_description", "") for i in recipe.get("ingredients", {}).get("ingredient", [])]

            st.subheader(f"{name} — {calories} kcal")
            if image_url:
                st.image(image_url, use_container_width=True)
            st.markdown("**Zutaten:**")
            for ing in ingredients[:5]:
                st.write(f"- {ing}")
            if len(ingredients) > 5:
                st.write("…")
            if recipe.get("directions"):
                st.markdown("**Anleitung:**")
                st.write(recipe["directions"])
            st.markdown("---")
