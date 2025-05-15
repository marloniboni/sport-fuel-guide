import os                                           #-> siehe requirements.txt
import streamlit as st
import pandas as pd
import numpy as np
import requests
import gpxpy
import folium
from streamlit_folium import st_folium
import altair as alt
import joblib

# Seitenkonfiguration
# Legt den Titel und Layout der Streamlit-App fest
st.set_page_config(page_title="Sport-Fuel Guide", layout="wide")

# Vor-Workout Planung
# ----------------------------

# Prüft, ob das Körpergewicht im Session-State gespeichert ist
# Wenn nicht, warnt der Nutzer und stoppt die Ausführung
if "gewicht" not in st.session_state:
    st.warning("Bitte gib zuerst deine Körperdaten auf der Startseite ein.")
    st.stop()
# Liest das gespeicherte Gewicht aus dem Session-State
gewicht = st.session_state.gewicht

# Auswahl der Sportart und Datenquelle
sportart = st.selectbox("Sportart", ["Laufen", "Radfahren", "Schwimmen"])
mode     = st.radio("Datenquelle wählen", ["GPX-Datei hochladen", "Manuelle Eingabe"])

# Wenn der Nutzer eine GPX-Datei hochlädt, wird sie eingelesen und geparst
if mode == "GPX-Datei hochladen":
    uploaded = st.file_uploader("GPX-Datei hochladen", type="gpx")
    if not uploaded:
        st.error("Bitte eine GPX-Datei hochladen.")
        st.stop()
    try:
        # Parse die GPX-Datei und berechne Dauer und Distanz
        gpx          = gpxpy.parse(uploaded.getvalue().decode())
        duration_sec = gpx.get_duration() or 0
        dauer        = duration_sec / 60                  # Dauer in Minuten
        distanz      = (gpx.length_3d() or 0) / 1000       # Distanz in Kilometern
        # Extrahiere Koordinaten für die Karte
        coords       = [
            (pt.latitude, pt.longitude)
            for tr in gpx.tracks
            for seg in tr.segments
            for pt in seg.points
        ]
    except Exception as e:
        st.error(f"Fehler beim Parsen der GPX-Datei: {e}")
        st.stop()
        
# Manuelle Eingabe von Dauer und Distanz
else:
    dauer   = st.slider("Dauer (Min)", 15, 300, 60)
    distanz = st.number_input("Distanz (km)", 0.0, 100.0, 10.0)
    coords  = []

# Ausgabe der eingegebenen Werte
st.markdown(f"**Dauer:** {dauer:.0f} Min • **Distanz:** {distanz:.2f} km")

#Machine Learning Teil
# -----------
@st.cache_resource
# Lädt das vortrainierte Modell nur einmal und cached es
def load_model():
    return joblib.load("models/calorie_predictor.pkl")

model = load_model()

# Mapping der Sportart auf den ML-verständlichen Activity-String
activity_map = {
    "Laufen": "Running, 6 mph (10 min mile)",
    "Radfahren": "Cycling, 14-15.9 mph",
    "Schwimmen": "Swimming laps, freestyle, fast"
}
activity = activity_map[sportart]

# Bereitet das DataFrame für das Modell vor
X = pd.DataFrame([{  
    "Activity": activity,
    "Sportart": sportart,
    "Gewicht": gewicht,
    "Dauer": dauer,
    "Distanz": distanz
}])

# Versucht die Vorhersage mit dem Modell, ansonsten Fall-Back-Formel. Die nächten 7 Codezeilen erstellt mit Hilfe von: OpenAI. (2025). ChatGPT 4O (Version vom 29.04.2025) [Large language model]. https://chat.openai.com/chat.
try:
    cal_burn = model.predict(X)[0]
    st.success(f"✅ Modell verwendet: → {int(cal_burn)} kcal")
except Exception as e:
    st.warning(f"⚠️ Fehler beim Modell: {e}. Formel wird verwendet.")
    faktoren = {"Laufen": 7, "Radfahren": 5, "Schwimmen": 6}
    cal_burn = faktoren[sportart] * gewicht * (dauer / 60)

# Berechnet den geschätzten Flüssigkeitsverlust (L pro Stunde). Quelle: Hirsladen: https://www.hirslanden.ch/de/hirslandenblog/medizin/trinken-beim-sport.html#:~:text=Hier%20sollten%20Sie%20auch%20w%C3%A4hrend,Schweissverlustes%20an%20Fl%C3%BCssigkeit%20wieder%20aufzunehmen.&text=Das%20American%20College%20of%20Sports
fluid_loss = 0.7 * (dauer / 60)

# Speichert die Werte im Session-State für spätere Nutzung
st.session_state["workout_calories"] = cal_burn
st.session_state["fluessigkeit"] = fluid_loss

# Darstellung der Ergebnisse
st.subheader("Deine persönlichen Berechnungen")
st.write(
    f"Kalorienverbrauch: **{int(cal_burn)} kcal**  •  "
    f"Flüssigkeitsverlust: **{fluid_loss:.2f} L**"
)

# Intake-Plan erstellen: Essen und Trinken
# ---------------------
# Intervall-Auswahl für Essen und Trinken
eat_int   = st.select_slider("Essen alle (Min)",   [15,20,30,45,60], 30)
drink_int = st.select_slider("Trinken alle (Min)", [10,15,20,30],   15)

# Ermittelt alle Zeitpunkte innerhalb der Trainingseinheit
events    = sorted(
    set(range(eat_int,   int(dauer)+1, eat_int  )) |
    set(range(drink_int, int(dauer)+1, drink_int))
)

# Berechnet benötigte Kalorien und Flüssigkeit pro Event
eat_events = [t for t in events if t % eat_int == 0]
req_cal = cal_burn / len(eat_events) if eat_events else 0

req_fluid = fluid_loss / len(events) if events else 0

# Erstellt eine Tabelle mit Minuten und Empfehlung pro Event
schedule = []
for t in events:
    row = {"Minute": t}
    if t % eat_int   == 0: row["Essen (kcal)"] = round(req_cal,   1)
    if t % drink_int == 0: row["Trinken (L)"]  = round(req_fluid, 3)
    schedule.append(row)

df_schedule = pd.DataFrame(schedule).set_index("Minute")  
st.subheader("Dein persönlicher Intake-Plan")
st.table(df_schedule)


# Snack-Finder via USDA API
# -------
FDC_API_KEY = "XDzSn37cJ5NRjskCXvg2lmlYUYptpq8tT68mPmPP"        #Eingabe der API. Quelle: U.S. Department of Agriculture, https://fdc.nal.usda.gov/api-guide

@st.cache_data
# Sucht Snacks anhand eines Stichworts und limit Quelle: U.S. Department of Agriculture, https://fdc.nal.usda.gov/api-guide
def search_foods(q, limit=5):
    r = requests.get(
        "https://api.nal.usda.gov/fdc/v1/foods/search",
        params={"api_key":FDC_API_KEY,"query":q,"pageSize":limit}
    )
    r.raise_for_status()
    return r.json().get("foods", [])

@st.cache_data
# Holt detaillierte Nährstoffdaten für ein Food-Item Quelle: U.S. Department of Agriculture, https://fdc.nal.usda.gov/api-guide
def get_food_details(fid):
    r = requests.get(
        f"https://api.nal.usda.gov/fdc/v1/food/{fid}",
        params={"api_key":FDC_API_KEY}
    )
    r.raise_for_status()
    return r.json()

# Initialisiert den Warenkorb im Session-State
if "cart" not in st.session_state:
    st.session_state.cart = []

st.subheader("Snack-Empfehlungen (via USDA)")
snack_query = st.text_input("Snack suchen (Schlagwort)", "")

if snack_query:
    foods = search_foods(snack_query, limit=5)        #Erscheinung von 5 Suchresultaten
    if not foods:
        st.warning("Keine Produkte gefunden – versuche ein anderes Stichwort.")     #Keine Resultate gefunden
    else:
        for food in foods:
            desc    = food.get("description","Unbekannt")
            fdc     = food.get("fdcId")
            details = get_food_details(fdc)

            # Robustes Nährstoff-Dictionary wird erstellt. Code erstellt mit Hilfe von: OpenAI. (2025). ChatGPT 4O (Version vom 29.04.2025) [Large language model]. https://chat.openai.com/chat.
            nut = {}
            for n in details.get("foodNutrients",[]):
                if "nutrient" in n and isinstance(n["nutrient"], dict):
                    k = n["nutrient"].get("name"); v = n.get("amount",0)
                elif "nutrientName" in n:
                    k = n.get("nutrientName");     v = n.get("value",0)
                else:
                    continue
                if k:
                    nut[k] = v or 0

            # Nährwerte pro 100g Quelle: U.S. Department of Agriculture, https://fdc.nal.usda.gov/api-guide
            cal100  = nut.get("Energy") or nut.get("Calories") or 0
            carb100 = nut.get("Carbohydrate, by difference",0)

            # Bestimme Portionsgröße in Gramm Quelle: U.S. Department of Agriculture, https://fdc.nal.usda.gov/api-guide
            servs     = details.get("servings",{}).get("serving",[])
            if isinstance(servs,dict): servs=[servs]
            gs        = next((s for s in servs if s.get("metricServingUnit")=="g"), servs[0] if servs else {}).get("metricServingAmount",100)
            gram_serv = float(gs)

            # Berechne Nährwerte pro Portion klassische 3 Satz Berechnung
            kcal_serv = cal100  * gram_serv/100.0
            carb_serv = carb100 * gram_serv/100.0

            c1,c2 = st.columns([5,1]) #Streamlit Design zur Darstellung von Warenkörben
            with c1:
                st.markdown(f"**{desc}** — {gram_serv:.0f} g → **{kcal_serv:.0f} kcal**, "
                            f"**{carb_serv:.0f} g Carbs**")
            if c2.button("+", key=f"add_{fdc}"):
                if not any(item["fdc"]==fdc for item in st.session_state.cart):
                    st.session_state.cart.append({
                        "fdc":        fdc,
                        "description":desc,
                        "grams":      gram_serv,
                        "kcal":       kcal_serv,
                        "carbs":      carb_serv
                    })

# Darstellung des Warenkorbs und Fueling-Chart
# -------------------------
cart = st.session_state.cart        #Warenkorb wieder abrufen
if cart:
    df_cart = pd.DataFrame(cart)      #Umwandlung Liste von Snacks in DataFrame Tabelle
    df_cart["step"] = np.arange(1,len(df_cart)+1)    #Fortlaufende Nummerierung 1 bis N

    st.subheader("Deine ausgewählten Snacks") #Anzeigen der Tabelle
    st.table(
        df_cart[["step","description","grams","kcal","carbs"]]
               .rename(columns={"step":"#","description":"Snack","carbs":"Carbs (g)"}) #Umbennennung der Spaltenüberschriften zur besseren Lesbarkeit
    )
  
    # Fueling: Bedarf vs. Zufuhr
    hours      = np.arange(0, dauer/60 + 1, 1)    #Erstellung von Stundenmarken von 0 bis zur Dauer der Aktivität
    req_hourly = gewicht * 1.5                      # Quelle: Hirsladen: https://www.hirslanden.ch/de/hirslandenblog/medizin/trinken-beim-sport.html#:~:text=Hier%20sollten%20Sie%20auch%20w%C3%A4hrend,Schweissverlustes%20an%20Fl%C3%BCssigkeit%20wieder%20aufzunehmen.&text=Das%20American%20College%20of%20Sports
    req_cum    = hours * req_hourly                #Rechnet wie viele g Carbs man bis zu jeder Stunde komuliert benötigt wird

    total_carbs = df_cart["carbs"].sum()        #Summe alles Kcal die durch Snacks aufgenommen werden

    df_req = pd.DataFrame({"Hour": hours, "Carbs": req_cum, "Type":"Required"}) #Soll-Werte Kcal pro Stunde
    df_act = pd.DataFrame({                            #Ist-Wert am Schluss des Workouts
        "Hour":    [hours.max()],
        "Carbs":   [total_carbs],
        "Type":    ["Consumed"]
    })

    df_plot = pd.concat([df_req, df_act], ignore_index=True)    #Verbindet beide Tabellen also Bedarf + nötige Kcal Zufuhr in eine Plot Tabelle

    st.subheader("Kumulative Kohlenhydrat-Zufuhr vs. Bedarf")    #Visualisierung mit alt->requirements.txt
    chart = (
        alt.Chart(df_plot)
           .mark_line(point=True)
           .encode(
               x=alt.X("Hour:Q", title="Stunden seit Workout"),
               y=alt.Y("Carbs:Q", title="Kohlenhydrate (g)"),
               color="Type:N",
               tooltip=["Type","Carbs"]
           )
           .properties(width=700, height=400)
    )
    st.altair_chart(chart, use_container_width=True)

# 3) Route-Map & GPX-Download
# ----
if coords:                #Sind Koordinatenpunkte da?
    # Erstelle Folium-Karte mit Track. Quelle: Folium: https://python-visualization.github.io/folium/latest/reference.html
    m = folium.Map(location=coords[0], zoom_start=13)
    folium.PolyLine(coords, color="blue").add_to(m)
    # Markiere Essen-/Trinken-Zeitpunkte auf der Karte
    for t in events:        #Zeitpunkte für Ess- und Trinkaufnahme markieren. Quelle: Folium: https://python-visualization.github.io/folium/latest/reference.html
        idx = min(int(t/dauer*len(coords)), len(coords)-1)
        lat, lon = coords[idx]
        folium.CircleMarker(                #Setzt Punkt auf Karte
            (lat, lon),
            radius=5,
            color="red" if t%eat_int==0 else "yellow",
            fill=True
        ).add_to(m)
    st.subheader("Route & Timing auf der Karte")        #Einfügen der Karte in Streamlit
    st_folium(m, width=700, height=400)
    # Bietet die Route als GPX zum Download an
    st.download_button(                                    #Mögliches Herunterladen der Karte in Form einer .gpx Datei für bspw. Garmin Edge
        "GPX herunterladen",
        gpx.to_xml(),
        file_name="route_intake.gpx",
        mime="application/gpx+xml"
    )                                                  

# Trennt den Abschnitt optisch
st.markdown("---")
# Button zum Wechseln zur Meal-Plan-Seite
if st.button("Zum Meal Plan"):
    st.switch_page("pages/2_Meal_Plan.py")
