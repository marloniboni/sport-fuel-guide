import os #bindet Python "os"-Modul ein, mit dem wir das Betriebssystem-Funktionnen nutzen können
import streamlit as st #lädt Stramlitrahmen und gibt ihm st als alias, damit Komponenten einfach auf App platziert werden können
import requests #wird benötigt um requests an APIs zu senden und Antworten zu verarbeiten
import matplotlib.pyplot as plt #Importiert marplotlibs Plot-API unter alias plt, um Grafiken zu erzeugen und in Stremlit einzubinden
import random, time #random für Zufallzahlen (benötigt um Rezepte zufällig zu mischen unt time für Zeitstemptel zur Initailsierung stabiler Seeds

# Seitenkonfiguration
st.set_page_config(page_title="Meal Plan", layout="wide") #legt Titel von Browser-Tab fest und Layout für volle Breite

# Seitentitel 
st.title("Dein persönlicher Essens-Plan")

# Edamam API-Anmeldeinformationen werden eingelesen
# -
# Liest IDs und Schlüssel aus Umgebungsvariablen bzw. Streamlit-Secrets https://www.geeksforgeeks.org/python-os-getenv-method/?utm_source=chatgpt.com
APP_ID   = os.getenv("EDAMAM_APP_ID", "") #APP_ID von EDAMAM welche in Secret abgespeichert ist (https://developer.edamam.com/admin/applications)
APP_KEY  = os.getenv("EDAMAM_APP_KEY", "") #APP_KEY von EDAMAM die in Secret abgespeichert ist (https://developer.edamam.com/admin/applications)
USER_ID  = os.getenv("EDAMAM_ACCOUNT_USER", "") #USER_ID von EDAMAM die in Secret abgespeichert ist (https://developer.edamam.com/admin/applications)

# Basis-URL für Edamam API Version 2
V2_URL = "https://api.edamam.com/api/recipes/v2"

# Sidebar: Allergien & Ernährungspräferenzen
st.sidebar.markdown("## Diät- & Ernährungspräferenzen")
# Mögliche Diät- und Ernährungspräferenzen laut Edamam
diet_opts = ["balanced","high-fiber","high-protein","low-carb","low-fat","low-sodium"] #sind auf englisch da direkt mit API verbunden, welche auch auf Englisch ist
health_opts = ["alcohol-free","dairy-free","egg-free","gluten-free","paleo","vegetarian","vegan"] #same here (https://developer.edamam.com//admin/applications/1409625691921)
# Auswahlfelder für Nutzerpräferenzen je nach Diät und Ernährungspräferenzen
sel_diets  = st.sidebar.multiselect("Diät", diet_opts) # erzeugt Auswahlfelder für Diätpräferenz labels, die Nutzer anklicken kann (https://github.com/daniellewisdl/streamlit-cheat-sheet/blob/master/app.py)
sel_health = st.sidebar.multiselect("Ernährungspräferenzen", health_opts) #same here für Ernährungspräferenzen 

# Ordnet jedem Mahlzeittyp, die Edamam-API erwartet, eine Liste von Labels zu, damit verschiedene Ergebnisse kommen
DISH_TYPES = {
    "Breakfast": ["Cereals","Breakfast and brunch","Bread"],
    "Lunch":     ["Main course","Salad","Sandwiches","Side dish","Soup"],
    "Dinner":    ["Main course","Side dish","Soup"]
}


#Fetch-Hilfsfunktion: Rezepte aus Edamam laden
#----
@st.cache_data(ttl=3600) #speichert Kopien von Daten in Zwischenspeicher "chace" für 3600 Sekunden lang, um API-Calls zu reduzieren
def fetch_recipes(meal_type, diets, healths, max_results=5, seed=0):  #Ruft Rezepte von Edamam basierend auf Mahlzeittyp, Diät- + Ernährungspräferenz Labels, seed dient als Initialisierung für Zufallsgenerator, um gefundene Rezeptliste vor Kürzen zu mischen
    # Parameter für Anfrage aufbauen basierden auf ID, Key, Essenstyp ^oben definiert
    params = {"q": "","type": "public", "app_id": APP_ID, "app_key": APP_KEY, "mealType": meal_type}
    for d in diets: #nimmt die Diätpräferenz welche der Nutzer in der Sidebar auwählt in kauf
        params.setdefault("diet", []).append(d)
    for h in healths:    #same für Ernährungsprägerenzen^
        params.setdefault("health", []).append(h)
    for dt in DISH_TYPES.get(meal_type, []): #sagt API nach welchen Essenstypen es suchen soll
        params.setdefault("dishType", []).append(dt)
    params["field"] = ["uri", "label", "image", "yield","ingredientLines", "calories", "totalNutrients", "instructions"]
    headers = {"Edamam-Account-User": USER_ID}

    #Sendet die API-Anfrage mit Parametern und Headern (Timeout 5 s) und löst bei Fehlern eine Ausnahme aus.
    r = requests.get(V2_URL, params=params, headers=headers, timeout=5)
    r.raise_for_status()

#Hits extrahieren, mischen, und auf maximale Resulate, hier 5 beschränken
    hits = [h["recipe"] for h in r.json().get("hits", [])]
    random.Random(seed).shuffle(hits)
    return hits[:max_results]

# Prüft, ob nötige Werte im vorherigen Seiten schon vorhanden sind, ansonsten Fehlermeldung dass diese noch ausgefüllt werden müssen
# ----------------
# Grundumsatz und Kalorienverbrauch müssen aus vorheriger App-Seite kommen, sonst gibt es keine Berechnungsgrundlage
if "grundumsatz" not in st.session_state or "workout_calories" not in st.session_state:
    st.error("Bitte zuerst Home & Vor-Workout ausfüllen.")
    st.stop()

# Berechnung der Gesamt- und pro Mahlzeit -Kalorien
total_cal = st.session_state.grundumsatz + st.session_state.workout_calories
# Snack-Kalorien aus Pre-Workout-Seite abziehen (Session-State "cart" wird dort befüllt)
snack_cal = sum(item["kcal"] for item in st.session_state.get("cart", []))
# Angepasster Tagesbedarf minus bereits konsumierter Snack-Kalorien
total_cal = total_cal - snack_cal

per_meal  = total_cal // 3   # jetzt bereits abzüglich aller Snacks
st.sidebar.caption("Snacks aus Vor-Workout werden im Meal Plan abgezogen.")

# Ausgabe des Bedarfs, der aus Vor-Workout und Home genommen und addiert wird
if snack_cal:
    st.markdown(f"**Snack-Kalorien (Vor-Workout):** –{snack_cal} kcal")
st.markdown(f"**Täglicher Gesamtbedarf:** {total_cal} kcal  •  **pro Mahlzeit:** ~{per_meal} kcal")
st.markdown("---")

# Funktion zur Ausgabe der Rezeptkarte
# --------
def render_recipe_card(r, key_prefix): #Zeigt Titel, Bild, Kalorien, Makronährstoffe und Zutaten/Anleitung im Expander an.

    #Titel und Bild aus API
    title    = r.get("label", "–")
    image    = r.get("image")
    total_c  = r.get("calories", 0)
    #Yield: Anzahl Portionen insgesamt indem es die Totale Kalorienanzahl die benötigt wird, durch die des Rezeptes rechnet
    yield_n  = r.get("yield", 1) or 1
    per_serv = total_c / yield_n
    # Berechnet, wie viele Portionen nötig sind, um pro Mahlzeit kcal zu erreichen
    portions = per_meal / per_serv if per_serv > 0 else None

    st.markdown(f"**{title}**")
    if image:
        st.image(image, use_container_width=True)

    # Ausgabe der Portionen oder Kalorien insgesamt
    if portions:
        st.markdown(f"Portionen: {portions:.1f} × {per_serv:.0f} kcal = {per_meal} kcal")
    else:
        st.markdown(f"Kalorien gesamt: {total_c} kcal")

    # Makronährstoff-Chart aus Edamam API
    nut = r.get("totalNutrients", {})
    prot = nut.get("PROCNT", {}).get("quantity", 0) / yield_n
    fat  = nut.get("FAT", {}).get("quantity", 0) / yield_n
    carb = nut.get("CHOCDF", {}).get("quantity", 0) / yield_n

    # Erstellt Balkendiagramm mit Matplotlib, um nicht nur Altair zu nutzen (https://matplotlib.org)
    fig, ax = plt.subplots()
    ax.bar(["Protein","Fat","Carbs"], [prot, fat, carb])
    ax.set_ylabel("g pro Portion")
    ax.set_title("Makros")
    st.pyplot(fig)

    # Zutaten und Rezepteanleitugn damit User weiss wie Gericht zubereitet werden muss
    with st.expander("Zutaten"):
        for line in r.get("ingredientLines", []):
            st.write(f"- {line}")
    with st.expander("Anleitung"): #gibt genaue Auflistung welche Zutaten benötigt werden
        instr = r.get("instructions") or []
        instr_list = instr if isinstance(instr, list) else [instr]
        for step in instr_list:
            st.write(f"- {step}")

# 3 Spalten für Frühstück, Mittag- + Abendessen
# ----------------
cols = st.columns(3)
meals = [("Frühstück","Breakfast"),("Mittagessen","Lunch"),("Abendessen","Dinner")]

#Für jeden Mahlzeit Typen einen eigenen Seed legen, wenn noch keiner existiert, um bilder zu ändern ohne dabei die anderen zu Ändern
for _, mtype in meals:
    seed_key = f"seed_{mtype}" #https://docs.streamlit.io/develop/concepts/architecture/caching
    if seed_key not in st.session_state:
        # z.B. aus timestamp + Zufall, bleibt stabil bis zum Neuladen
        st.session_state[seed_key] = int(time.time()*1000) + random.randint(0, 999) #Speichert den Seed im Session-State + Nutzt den aktuellen Zeitstempel in Millisekunden + eine Zufallszahl

# Für jede Mahlzeit: Überschrift, Rezepte laden, Slider um mehrere Rezepte anzuzeigen und Visualisierung darzustellen
#-----------
for (label, mtype), col in zip(meals, cols):
    with col:
        st.subheader(f"{label} (~{per_meal} kcal)")
        seed_key = f"seed_{mtype}" # holt den individuellen Seed https://docs.streamlit.io/develop/concepts/architecture/caching
        recs = fetch_recipes(mtype, sel_diets, sel_health,seed=st.session_state[seed_key]) #holt Vorschläge aus Edamam API ansonsten wird Fehlermeldung angezeigt
        if not recs:
            st.info("Keine passenden Rezepte gefunden.") #Fehlermeldung falls keine Rezepte gefunden wurden
            continue
        # Slider zur Auswahl der geladenen Rezepte, damit man sich was aussuchen kann, um grössere Variabilität zu haben
        idx = st.slider("Wähle Rezept", 1, len(recs), key=f"slider_{mtype}")
        r = recs[idx-1]
        render_recipe_card(r, mtype)
