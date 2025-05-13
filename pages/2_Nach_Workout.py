import os
import random
import streamlit as st
import requests
from requests_oauthlib import OAuth1

# ─────────────────────────────────────────────────────────────────────────────
# FatSecret Credentials
# ─────────────────────────────────────────────────────────────────────────────
FS_CONSUMER_KEY    = os.getenv("FS_CONSUMER_KEY", "9ced8a2df62549a594700464259c95de")
FS_CONSUMER_SECRET = os.getenv("FS_CONSUMER_SECRET", "<dein_consumer_secret>")

FS_API_BASE = "https://platform.fatsecret.com/rest/server.api"

# OAuth1-Objekt (zum Signieren jeder Anfrage)
auth = OAuth1(FS_CONSUMER_KEY, FS_CONSUMER_SECRET)

def fatsecret_request(method: str, params: dict) -> dict:
    """
    Macht eine GET-Anfrage an FatSecret, signiert mit OAuth1.
    Gibt das JSON zurück oder wirft eine Exception mit voller Fehlermeldung.
    """
    payload = {
        "method": method,
        "format": "json",
        **params
    }
    resp = requests.get(FS_API_BASE, params=payload, auth=auth, timeout=10)
    
    # Debug-Ausgabe, damit du siehst, was kommt
    st.write(f"Request to {method} returned HTTP {resp.status_code}")
    try:
        data = resp.json()
        st.write(data)  # zeige das rohe JSON
    except ValueError:
        st.error("Keine JSON-Antwort erhalten:")
        st.write(resp.text)
        st.stop()
    
    resp.raise_for_status()
    return data

# ─────────────────────────────────────────────────────────────────────────────
# Streamlit-Grundgerüst
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Debug FatSecret", layout="wide")

if "grundumsatz" not in st.session_state or "workout_calories" not in st.session_state:
    st.error("Bitte zuerst Home & Vor-Workout ausfüllen.")
    st.stop()

total_cal   = st.session_state.grundumsatz + st.session_state.workout_calories
per_meal_cal = total_cal // 3

st.markdown(f"**Tagesbedarf:** {total_cal} kcal — **pro Mahlzeit:** ~{per_meal_cal} kcal")
st.markdown("---")

cols = st.columns(3)
queries = [("Frühstück", "breakfast"), ("Mittagessen", "lunch"), ("Abendessen", "dinner")]

for (label, term), col in zip(queries, cols):
    with col:
        st.header(f"{label} (~{per_meal_cal} kcal)")
        try:
            search = fatsecret_request("recipe.search", {
                "search_expression": term,
                "max_results": 20
            })
            recipes = search.get("recipes", {}).get("recipe", [])
        except Exception as e:
            st.error(f"Fehler bei recipe.search: {e}")
            continue

        if not recipes:
            st.info("Keine Rezepte gefunden.")
            continue

        for rec in random.sample(recipes, min(3, len(recipes))):
            try:
                detail = fatsecret_request("recipe.get", {"recipe_id": rec["recipe_id"]})
                r = detail.get("recipe", {})
            except Exception as e:
                st.warning(f"recipe.get fehlgeschlagen: {e}")
                continue

            # Anzeige
            kcal = r.get("nutrition", {}).get("calories", "unbekannt")
            st.subheader(f"{r.get('recipe_name','?')} — {kcal} kcal")
            img = r.get("recipe_images", {}).get("recipe_image", {}).get("image_url")
            if img:
                st.image(img, use_container_width=True)
            ingreds = [i["food_description"] for i in r.get("ingredients",{}).get("ingredient",[])]
            st.markdown("**Zutaten:**")
            for i in ingreds[:5]:
                st.write(f"- {i}")
            if len(
