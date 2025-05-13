import os
import streamlit as st
import requests
import matplotlib.pyplot as plt

# ─── 0) Page config ───────────────────────────────────────────────────────────
st.set_page_config(page_title="Meal Plan", layout="wide")

# ─── 1) Edamam v2 Credentials ─────────────────────────────────────────────────
APP_ID   = os.getenv("EDAMAM_APP_ID", "")
APP_KEY  = os.getenv("EDAMAM_APP_KEY", "")
USER_ID  = os.getenv("EDAMAM_ACCOUNT_USER", "")
if not (APP_ID and APP_KEY and USER_ID):
    st.error("Bitte setze EDAMAM_APP_ID, EDAMAM_APP_KEY und EDAMAM_ACCOUNT_USER in deinen Secrets!")
    st.stop()

V2_URL = "https://api.edamam.com/api/recipes/v2"

# ─── 2) Sidebar: Preferences ──────────────────────────────────────────────────
st.sidebar.markdown("## Allergien & Ernährungspräferenzen")
diet_opts = ["balanced","high-fiber","high-protein","low-carb","low-fat","low-sodium"]
health_opts = [
    "alcohol-free","celery-free","crustacean-free","dairy-free","egg-free",
    "fish-free","fodmap-free","gluten-free","keto-friendly","kosher",
    "low-sugar","lupine-free","Mediterranean","paleo","peanut-free",
    "pescatarian","pork-free","vegetarian","vegan","wheat-free"
]
sel_diets  = st.sidebar.multiselect("Diet labels", diet_opts)
sel_health = st.sidebar.multiselect("Health labels", health_opts)

# ─── 3) DishType mapping per meal ─────────────────────────────────────────────
DISH_TYPES = {
    "Breakfast": ["Cereals","Pancake","Bread","Preps"],
    "Lunch":     ["Main course","Salad","Sandwiches","Soup","Side dish"],
    "Dinner":    ["Main course","Side dish","Soup"]
}

# ─── 4) Fetch & filter helper ─────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def fetch_and_filter(meal_type, diets, healths, max_results=5):
    params = {"type":"public","app_id":APP_ID,"app_key":APP_KEY,"mealType":meal_type}
    for d in diets:  params.setdefault("diet", []).append(d)
    for h in healths: params.setdefault("health", []).append(h)
    for dt in DISH_TYPES.get(meal_type,[]): params.setdefault("dishType", []).append(dt)
    params["field"] = ["label","image","yield","ingredientLines","calories","totalNutrients","instructions"]
    headers = {"Edamam-Account-User": USER_ID}

    r = requests.get(V2_URL, params=params, headers=headers, timeout=5)
    r.raise_for_status()
    hits = [h["recipe"] for h in r.json().get("hits",[])]
    return hits[:max_results]

# ─── 5) Session-State check ───────────────────────────────────────────────────
if "grundumsatz" not in st.session_state or "workout_calories" not in st.session_state:
    st.error("Bitte zuerst Home & Vor-Workout ausfüllen.")
    st.stop()

total_cal = st.session_state.grundumsatz + st.session_state.workout_calories
per_meal  = total_cal // 3

st.markdown("---")
st.markdown(f"**Täglicher Gesamtbedarf:** {total_cal} kcal  •  **pro Mahlzeit:** ~{per_meal} kcal")

# ─── 6) Anzeige mit Slider und Grafik ─────────────────────────────────────────
cols  = st.columns(3)
meals = [("Frühstück","Breakfast"),("Mittagessen","Lunch"),("Abendessen","Dinner")]

for (label, mtype), col in zip(meals, cols):
    with col:
        st.subheader(f"{label} (~{per_meal} kcal)")
        recipes = fetch_and_filter(mtype, sel_diets, sel_health)
        if not recipes:
            st.info("Keine passenden Rezepte gefunden.")
            continue

        # Slider 1–5
        idx = st.slider("Rezept auswählen", 1, len(recipes), key=mtype)
        r   = recipes[idx-1]

        # Basisdaten
        title    = r["label"]
        image    = r.get("image")
        total_c  = r.get("calories",0)
        yield_n  = r.get("yield",1) or 1
        per_serv = total_c / yield_n
        portions = per_meal / per_serv if per_serv>0 else None

        st.markdown(f"### {title}")
        if image: st.image(image, use_container_width=True)

        # Portionen­berechnung
        if portions:
            st.markdown(f"**Portionen:** {portions:.1f} × {per_serv:.0f} kcal = {per_meal} kcal")
        else:
            st.markdown(f"**Kalorien gesamt:** {total_c} kcal")

        # Makros pro Portion
        nut  = r.get("totalNutrients",{})
        prot = nut.get("PROCNT",{}).get("quantity",0) / yield_n
        fat  = nut.get("FAT",{}).get("quantity",0) / yield_n
        carb = nut.get("CHOCDF",{}).get("quantity",0) / yield_n

        # Grafik
        fig, ax = plt.subplots()
        ax.bar(["Protein","Fat","Carbs"], [prot, fat, carb])
        ax.set_ylabel("Gramm pro Portion")
        ax.set_title("Makros pro Portion")
        st.pyplot(fig)

        # Zutaten & Anleitung
        with st.expander("Zutaten"):
            for line in r.get("ingredientLines",[]): st.write(f"- {line}")
        with st.expander("Anleitung"):
            instr = r.get("instructions") or []
            instr_list = instr if isinstance(instr,list) else [instr]
            for step in instr_list: st.write(f"- {step}")
