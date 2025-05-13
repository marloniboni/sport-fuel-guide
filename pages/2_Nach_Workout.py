import os
import random
import streamlit as st
import requests
from requests_oauthlib import OAuth1

# ─────────────────────────────────────────────────────────────────────────────
# 1) FatSecret-Credentials aus Umgebungsvariablen holen
# ─────────────────────────────────────────────────────────────────────────────
FS_CONSUMER_KEY    = os.getenv("FS_CONSUMER_KEY", "")
FS_CONSUMER_SECRET = os.getenv("FS_CONSUMER_SECRET", "")

if not FS_CONSUMER_KEY or not FS_CONSUMER_SECRET:
    st.error(
        "🚨 FatSecret-Credentials fehlen!\n\n"
        "Bitte setze in deiner Umgebung die Variablen:\n"
        "• FS_CONSUMER_KEY\n"
        "• FS_CONSUMER_SECRET\n\n"
        "z.B. lokal via `export FS_CONSUMER_KEY=...` oder in Streamlit Cloud unter App Settings → Secrets."
    )
    st.stop()

auth = OAuth1(FS_CONSUMER_KEY, FS_CONSUMER_SECRET)
FS_API_BASE = "https://platform.fatsecret.com/rest/server.api"

def fatsecret_request(method: str, params: dict) -> dict:
    payload = {"method": method, "format": "json", **params}
    resp = requests.get(FS_API_BASE, params=payload, auth=auth, timeout=10)
    resp.raise_for_status()
    return resp.json()

# ─────────────────────────────────────────────────────────────────────────────
# 2) Streamlit-Grundgerüst
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Meal Plan mit FatSecret", layout="wide")

# Simulation: Session-State-Werte müssen vorab gesetzt sein
# st.session_state["grundumsatz"] = 2000
# st.session_state["workout_calories"] = 500

if "grundumsatz" not in st.session_state or "workout_calories" not in st.session_state:
    st.error("Bitte zuerst Home & Vor-Workout ausfüllen.")
    st.stop()

total_cal    = st.session_state.grundumsatz + st.session_state.workout_calories
per_meal_cal = total_cal // 3

st.markdown("---")
st.markdown(f"**Täglicher Gesamtbedarf:** {total_cal} kcal")
st.markdown(f"**Ziel pro Mahlzeit:** ~{per_meal_cal} kcal")

# ─────────────────────────────────────────────────────────────────────────────
# 3) Drei-Spalten-Layout: Frühstück, Mittag, Abendessen
# ─────────────────────────────────────────────────────────────────────────────
cols    = st.columns(3)
queries = [("Frühstück", "breakfast"), ("Mittagessen", "lunch"), ("Abendessen", "dinner")]

for (label, term), col in zip(queries, cols):
    with col:
        st.header(f"{label} (~{per_meal_cal} kcal)")

        # 3.1) Suche Rezepte
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

        # 3.2) Wähle bis zu 3 Rezepte
        for rec in random.sample(hits, k=min(3, len(hits))):
            try:
                detail = fatsecret_request("recipe.get", {"recipe_id": rec["recipe_id"]})
                r      = detail.get("recipe", {})
            except Exception as e:
                st.warning(f"Details konnten nicht geladen werden: {e}")
                continue

            name    = r.get("recipe_name", "–")
            calories= r.get("nutrition", {}).get("calories", "unbekannt")
            img_url = r.get("recipe_images", {}).get("recipe_image", {}).get("image_url")

            st.subheader(f"{name} — {calories} kcal")
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
