import os #bindet Python "os"-Modul ein, mit dem wir das Betriebssystem-Funktionnen nutzen können
import streamlit as st #lädt Stramlitrahmen und gibt ihm st als alias, damit Komponenten einfach auf App platziert werden können
import requests #wird benötigt um requests an APIs zu senden und Antworten zu verarbeiten
import matplotlib.pyplot as plt #Importiert marplotlibs Plot-API unter alias plt, um Grafiken zu erzeugen und in Stremlit einzubinden

# Seitenkonfiguration
st.set_page_config(page_title="Meal Plan", layout="wide") #legt Titel von Browser-Tab fest und Layout für volle Breite

# -
# Edamam API-Anmeldeinformationen werden eingelesen
# -
# Liest IDs und Schlüssel aus Umgebungsvariablen bzw. Streamlit-Secrets https://www.geeksforgeeks.org/python-os-getenv-method/?utm_source=chatgpt.com
APP_ID   = os.getenv("EDAMAM_APP_ID", "") #APP_ID von EDAMAM welche in Secret abgespeichert ist (https://developer.edamam.com/admin/applications)
APP_KEY  = os.getenv("EDAMAM_APP_KEY", "") #APP_KEY von EDAMAM die in Secret abgespeichert ist (https://developer.edamam.com/admin/applications)
USER_ID  = os.getenv("EDAMAM_ACCOUNT_USER", "") #USER_ID von EDAMAM die in Secret abgespeichert ist (https://developer.edamam.com/admin/applications)

# Basis-URL für Edamam API v2
V2_URL = "https://api.edamam.com/api/recipes/v2"

# ----------------------------------------
# Sidebar: Allergien & Ernährungspräferenzen
# ----------------------------------------
st.sidebar.markdown("## Allergien & Ernährungspräferenzen")
# Mögliche Diet- und Health-Labels laut Edamam
diet_opts = ["balanced","high-fiber","high-protein","low-carb","low-fat","low-sodium"]
health_opts = ["alcohol-free","dairy-free","egg-free","gluten-free","paleo","vegetarian","vegan"]
# Auswahlfelder für Nutzerpräferenzen
sel_diets  = st.sidebar.multiselect("Diet labels", diet_opts)
sel_health = st.sidebar.multiselect("Health labels", health_opts)

# DishType-Mapping für jede Mahlzeit (wird an API-Parameter angehängt)
DISH_TYPES = {
    "Breakfast": ["Cereals","Pancake","Bread","Main course"],
    "Lunch":     ["Main course","Salad","Sandwiches","Side dish","Soup"],
    "Dinner":    ["Main course","Side dish","Soup"]
}

# ----------------------------------------
# Fetch-Hilfsfunktion: Rezepte aus Edamam laden
# ----------------------------------------
@st.cache_data(ttl=3600)
def fetch_recipes(meal_type, diets, healths, max_results=5):
    """
    Ruft Rezepte von Edamam basierend auf mealType, diet- und health-Labels ab.
    Ergebnisse werden für 1 Stunde gecached.
    """
    # Basis-Parameter für die Anfrage
    params = {"type":"public","app_id":APP_ID,"app_key":APP_KEY,"mealType":meal_type}
    # Füge ausgewählte diet-Labels hinzu
    for d in diets:  params.setdefault("diet", []).append(d)
    # Füge ausgewählte health-Labels hinzu
    for h in healths: params.setdefault("health", []).append(h)
    # Füge DishType-Labels basierend auf meal_type hinzu
    for dt in DISH_TYPES.get(meal_type,[]): params.setdefault("dishType", []).append(dt)
    # Liste der gewünschten Felder aus der API-Antwort
    params["field"] = ["uri","label","image","yield","ingredientLines","calories","totalNutrients","instructions"]
    # Benutzer-Header für Edamam-Account
    headers = {"Edamam-Account-User": USER_ID}
    # GET-Request mit Timeout
    r = requests.get(V2_URL, params=params, headers=headers, timeout=5)
    r.raise_for_status()
    # Extrahiere Rezepte aus der Antwort
    hits = [h["recipe"] for h in r.json().get("hits",[])]
    return hits[:max_results]

# ----------------------------------------
# Prüfen, ob nötige Werte im Session-State vorhanden sind
# ----------------------------------------
# Grundumsatz und Kalorienverbrauch müssen aus vorheriger App-Seite kommen
if "grundumsatz" not in st.session_state or "workout_calories" not in st.session_state:
    st.error("Bitte zuerst Home & Vor-Workout ausfüllen.")
    st.stop()

# Gesamt- und pro-Mahlzeit-Kalorien berechnen
total_cal = st.session_state.grundumsatz + st.session_state.workout_calories
per_meal  = total_cal // 3

# Ausgabe des Bedarfs
st.markdown(f"**Täglicher Gesamtbedarf:** {total_cal} kcal  •  **pro Mahlzeit:** ~{per_meal} kcal")
st.markdown("---")

# ----------------------------------------
# Funktion zum Rendern einer Rezeptkarte
# ----------------------------------------
def render_recipe_card(r, key_prefix):
    """
    Zeigt Titel, Bild, Kalorien, Makronährstoffe und Zutaten/Anleitung im Expander an.
    """
    # Titel und Bild
    title    = r.get("label", "–")
    image    = r.get("image")
    total_c  = r.get("calories", 0)
    # Yield: Anzahl Portionen insgesamt
    yield_n  = r.get("yield", 1) or 1
    per_serv = total_c / yield_n
    # Berechne, wie viele Portionen nötig sind, um pro_meal kcal zu erreichen
    portions = per_meal / per_serv if per_serv > 0 else None

    st.markdown(f"**{title}**")
    if image:
        st.image(image, use_container_width=True)

    # Ausgabe der Portionen oder Kalorien insgesamt
    if portions:
        st.markdown(f"Portionen: {portions:.1f} × {per_serv:.0f} kcal = {per_meal} kcal")
    else:
        st.markdown(f"Kalorien gesamt: {total_c} kcal")

    # ----------------------------------------
    # Makronährstoff-Chart
    # ----------------------------------------
    nut = r.get("totalNutrients", {})
    prot = nut.get("PROCNT", {}).get("quantity", 0) / yield_n
    fat  = nut.get("FAT", {}).get("quantity", 0) / yield_n
    carb = nut.get("CHOCDF", {}).get("quantity", 0) / yield_n

    # Erstelle Balkendiagramm mit Matplotlib
    fig, ax = plt.subplots()
    ax.bar(["Protein","Fat","Carbs"], [prot, fat, carb])
    ax.set_ylabel("g pro Portion")
    ax.set_title("Makros")
    st.pyplot(fig)

    # ----------------------------------------
    # Zutaten und Anleitung in Expandern
    # ----------------------------------------
    with st.expander("Zutaten"):
        for line in r.get("ingredientLines", []):
            st.write(f"- {line}")
    with st.expander("Anleitung"):
        instr = r.get("instructions") or []
        instr_list = instr if isinstance(instr, list) else [instr]
        for step in instr_list:
            st.write(f"- {step}")

# ----------------------------------------
# Hauptlayout: 3 Spalten für Frühstück, Mittag, Abend
# ----------------------------------------
cols = st.columns(3)
meals = [("Frühstück","Breakfast"),("Mittagessen","Lunch"),("Abendessen","Dinner")]

# Für jede Mahlzeit: Überschrift, Rezepte laden, Slider und Karte rendern
for (label, mtype), col in zip(meals, cols):
    with col:
        st.subheader(f"{label} (~{per_meal} kcal)")
        recs = fetch_recipes(mtype, sel_diets, sel_health)
        if not recs:
            st.info("Keine passenden Rezepte gefunden.")
            continue
        # Slider zur Auswahl eines der geladenen Rezepte
        idx = st.slider("Wähle Rezept", 1, len(recs), key=f"slider_{mtype}")
        r = recs[idx-1]
        render_recipe_card(r, mtype)
