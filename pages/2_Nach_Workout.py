import os
import streamlit as st
import requests
import matplotlib.pyplot as plt

# ─── 0) Page config ───────────────────────────────────────────────────────────
st.set_page_config(page_title="Meal Plan", layout="wide")

# ─── 1) Credentials ────────────────────────────────────────────────────────────
APP_ID   = os.getenv("EDAMAM_APP_ID", "")
APP_KEY  = os.getenv("EDAMAM_APP_KEY", "")
USER_ID  = os.getenv("EDAMAM_ACCOUNT_USER", "")
if not (APP_ID and APP_KEY and USER_ID):
    st.error("Bitte setze EDAMAM_APP_ID, EDAMAM_APP_KEY und EDAMAM_ACCOUNT_USER in deinen Secrets!")
    st.stop()

V2_URL = "https://api.edamam.com/api/recipes/v2"

# ─── 2) Sidebar: Preferences ──────────────────────────────────────────────────
st.sidebar.markdown("## Allergien & Präferenzen")
diet_opts = ["balanced","high-fiber","high-protein","low-carb","low-fat","low-sodium"]
health_opts = [
    "alcohol-free","celery-free","crustacean-free","dairy-free","egg-free",
    "fish-free","fodmap-free","gluten-free","keto-friendly","kosher",
    "low-sugar","lupine-free","Mediterranean","paleo","peanut-free",
    "pescatarian","pork-free","vegetarian","vegan","wheat-free"
]
sel_diets  = st.sidebar.multiselect("Diet labels", diet_opts)
sel_health = st.sidebar.multiselect("Health labels", health_opts)

# ─── 3) DishType mapping ──────────────────────────────────────────────────────
DISH_TYPES = {
    "Breakfast": ["Cereals","Pancake","Bread","Preps"],
    "Lunch":     ["Main course","Salad","Sandwiches","Soup","Side dish"],
    "Dinner":    ["Main course","Side dish","Soup"]
}

# ─── 4) Fetch helper ──────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def fetch_recipes(meal_type, diets, healths, max_results=5):
    params = {"type":"public","app_id":APP_ID,"app_key":APP_KEY,"mealType":meal_type}
    for d in diets:  params.setdefault("diet", []).append(d)
    for h in healths: params.setdefault("health", []).append(h)
    for dt in DISH_TYPES.get(meal_type,[]): params.setdefault("dishType", []).append(dt)
    params["field"] = ["uri","label","image","yield","ingredientLines","calories","totalNutrients","instructions"]
    headers = {"Edamam-Account-User": USER_ID}

    r = requests.get(V2_URL, params=params, headers=headers, timeout=5)
    r.raise_for_status()
    hits = [h["recipe"] for h in r.json().get("hits",[])]
    return hits[:max_results]

# ─── 5) State check ───────────────────────────────────────────────────────────
if "grundumsatz" not in st.session_state or "workout_calories" not in st.session_state:
    st.error("Bitte zuerst Home & Vor-Workout ausfüllen.")
    st.stop()

total_cal = st.session_state.grundumsatz + st.session_state.workout_calories
per_meal  = total_cal // 3

st.markdown("---")
st.markdown(f"**Täglicher Gesamtbedarf:** {total_cal} kcal   •   **pro Mahlzeit:** ~{per_meal} kcal")

cols  = st.columns(3)
meals = [("Frühstück","Breakfast"),("Mittagessen","Lunch"),("Abendessen","Dinner")]

# ─── 6) Breakfast ─────────────────────────────────────────────────────────────
with cols[0]:
    st.subheader(f"Frühstück (~{per_meal} kcal)")
    b_recipes = fetch_recipes("Breakfast", sel_diets, sel_health)
    if not b_recipes:
        st.info("Keine passenden Rezepte.")
    else:
        idx_b = st.slider("Breakfast auswählen", 1, len(b_recipes), key="idx_b")
        sel_b = b_recipes[idx_b-1]

# ─── 7) Lunch ─────────────────────────────────────────────────────────────────
with cols[1]:
    st.subheader(f"Mittagessen (~{per_meal} kcal)")
    l_recs = fetch_recipes("Lunch", sel_diets, sel_health)
    # Filter breakfast URI
    if b_recipes:
        l_recs = [r for r in l_recs if r["uri"] != sel_b.get("uri")]
    if not l_recs:
        st.info("Keine passenden Rezepte (nach Breakfast-Filter).")
    else:
        idx_l = st.slider("Lunch auswählen", 1, len(l_recs), key="idx_l")
        sel_l = l_recs[idx_l-1]

# ─── 8) Dinner ───────────────────────────────────────────────────────────────
with cols[2]:
    st.subheader(f"Abendessen (~{per_meal} kcal)")
    d_recs = fetch_recipes("Dinner", sel_diets, sel_health)
    # Filter breakfast & lunch URIs
    used = {sel_b.get("uri")} if b_recipes else set()
    if l_recs:
        used.add(sel_l.get("uri"))
    d_recs = [r for r in d_recs if r["uri"] not in used]
    if not d_recs:
        st.info("Keine passenden Rezepte (nach Breakfast+Lunch-Filter).")
    else:
        idx_d = st.slider("Dinner auswählen", 1, len(d_recs), key="idx_d")
        sel_d = d_recs[idx_d-1]

# ─── 9) Function to render a recipe ───────────────────────────────────────────
def render_recipe(r):
    title    = r["label"]
    image    = r.get("image")
    total_c  = r.get("calories",0)
    yield_n  = r.get("yield",1) or 1
    per_serv = total_c / yield_n
    portions = per_meal / per_serv if per_serv>0 else None

    st.markdown(f"### {title}")
    if image: st.image(image, use_container_width=True)
    if portions:
        st.markdown(f"**Portionen:** {portions:.1f} × {per_serv:.0f} kcal = {per_meal} kcal")
    else:
        st.markdown(f"**Kalorien gesamt:** {total_c} kcal")

    # Makrografik
    nut  = r.get("totalNutrients",{})
    prot = nut.get("PROCNT",{}).get("quantity",0) / yield_n
    fat  = nut.get("FAT",{}).get("quantity",0) / yield_n
    carb = nut.get("CHOCDF",{}).get("quantity",0) / yield_n
    fig, ax = plt.subplots()
    ax.bar(["Protein","Fat","Carbs"], [prot, fat, carb])
    ax.set_ylabel("g pro Portion")
    ax.set_title("Makros pro Portion")
    st.pyplot(fig)

    with st.expander("Zutaten"):
        for line in r.get("ingredientLines",[]): st.write(f"- {line}")
    with st.expander("Anleitung"):
        instr = r.get("instructions") or []
        steps = instr if isinstance(instr, list) else [instr]
        for s in steps: st.write(f"- {s}")

# ─── 10) Render selected recipes ──────────────────────────────────────────────
if b_recipes and "sel_b" in locals():
    render_recipe(sel_b)
if l_recs and "sel_l" in locals():
    render_recipe(sel_l)
if d_recs and "sel_d" in locals():
    render_recipe(sel_d)
