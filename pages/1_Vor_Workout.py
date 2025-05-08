import os
import streamlit as st
import pandas as pd
import numpy as np
import requests
import gpxpy
import folium
from streamlit_folium import st_folium
import altair as alt
import joblib

# ─────────────────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Sport-Fuel Guide", layout="wide")

# ─────────────────────────────────────────────────────────────────────────────
# 1) Vor-Workout Planung
# ─────────────────────────────────────────────────────────────────────────────

# Auswahl der Sportart
sportart = st.selectbox("Sportart", ["Laufen", "Radfahren", "Schwimmen"])

# Manuelle Eingabe oder GPX-Upload
quelle = st.radio("Datenquelle wählen", ["Manuelle Eingabe", "GPX-Datei hochladen"])

if quelle == "Manuelle Eingabe":
    dauer = st.slider("Dauer (Min)", 15, 300, 60)
    distanz = st.number_input("Distanz (km)", min_value=0.0, value=10.0)
else:
    gpx_file = st.file_uploader("GPX-Datei hochladen", type="gpx")
    # Placeholder (du hast das sicher schon eingebaut)
    dauer = 60
    distanz = 10.0

gewicht = 70  # Optional später als Eingabe machen

# Aktivität definieren basierend auf Sportart
activity_map = {
    "Laufen": "Running, 6 mph (10 min mile)",
    "Radfahren": "Cycling, 12-13.9 mph, moderate",
    "Schwimmen": "Swimming laps, freestyle, slow"
}
activity = activity_map[sportart]

# 🔍 Eingabe anzeigen
st.caption(f"Eingabe für ML-Modell: {{'Activity': '{activity}', 'Sportart': '{sportart}', 'Gewicht': {gewicht}, 'Dauer': {dauer}}}")

# 🧠 Modell laden und Vorhersage berechnen
try:
    model = joblib.load("models/calorie_predictor.pkl")
    input_df = pd.DataFrame([{
        "Activity": activity,
        "Sportart": sportart,
        "Gewicht": gewicht,
        "Dauer": dauer
    }])
    kcal = model.predict(input_df)[0]
    wasser = round(dauer * 0.012, 2)

    # Ergebnisse anzeigen
    st.subheader("Deine persönlichen Berechnungen")
    st.write(f"Kalorienverbrauch: **{round(kcal)} kcal**")
    st.write(f"Flüssigkeitsverlust: **{wasser} L**")

    # Intake-Plan (einfaches Beispiel)
    st.slider("Essen alle (Min)", 15, 60, 30)
    st.slider("Trinken alle (Min)", 10, 30, 15)

except Exception as e:
    st.error(f"⚠️ Fehler bei der Vorhersage: {e}")





# ─────────────────────────────────────────────────────────────────────────────
# 2) Snack-Finder (USDA) mit Accumulativer Liste
# ─────────────────────────────────────────────────────────────────────────────
FDC_API_KEY = "XDzSn37cJ5NRjskCXvg2lmlYUYptpq8tT68mPmPP"

@st.cache_data
def search_foods(q, limit=5):
    r = requests.get(
        "https://api.nal.usda.gov/fdc/v1/foods/search",
        params={"api_key":FDC_API_KEY,"query":q,"pageSize":limit}
    )
    r.raise_for_status()
    return r.json().get("foods", [])

@st.cache_data
def get_food_details(fid):
    r = requests.get(
        f"https://api.nal.usda.gov/fdc/v1/food/{fid}",
        params={"api_key":FDC_API_KEY}
    )
    r.raise_for_status()
    return r.json()

if "cart" not in st.session_state:
    st.session_state.cart = []

st.subheader("🍌 Snack-Empfehlungen via USDA")
snack_query = st.text_input("Snack suchen (Schlagwort)", "")

if snack_query:
    foods = search_foods(snack_query, limit=5)
    if not foods:
        st.warning("Keine Produkte gefunden – versuche ein anderes Stichwort.")
    else:
        for food in foods:
            desc    = food.get("description","Unbekannt")
            fdc     = food.get("fdcId")
            details = get_food_details(fdc)

            # robust nutrient dict
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

            # grams per 100g
            cal100  = nut.get("Energy") or nut.get("Calories") or 0
            carb100 = nut.get("Carbohydrate, by difference",0)

            # find gram serving
            servs     = details.get("servings",{}).get("serving",[])
            if isinstance(servs,dict): servs=[servs]
            gs        = next((s for s in servs if s.get("metricServingUnit")=="g"), servs[0] if servs else {}).get("metricServingAmount",100)
            gram_serv = float(gs)

            # per-serving values
            kcal_serv = cal100  * gram_serv/100.0
            carb_serv = carb100 * gram_serv/100.0

            c1,c2 = st.columns([5,1])
            with c1:
                st.markdown(f"**{desc}** — {gram_serv:.0f} g → **{kcal_serv:.0f} kcal**, "
                            f"**{carb_serv:.0f} g Carbs**")
            if c2.button("➕", key=f"add_{fdc}"):
                if not any(item["fdc"]==fdc for item in st.session_state.cart):
                    st.session_state.cart.append({
                        "fdc":        fdc,
                        "description":desc,
                        "grams":      gram_serv,
                        "kcal":       kcal_serv,
                        "carbs":      carb_serv
                    })

# render cart & fueling graph
cart = st.session_state.cart
if cart:
    df_cart = pd.DataFrame(cart)
    df_cart["step"] = np.arange(1,len(df_cart)+1)

    st.subheader("Deine ausgewählten Snacks")
    st.table(
        df_cart[["step","description","grams","kcal","carbs"]]
               .rename(columns={"step":"#","description":"Snack","carbs":"Carbs (g)"})
    )

    # ─────────────────────────────────────────────────────────────────────────
    #  Fueling requirement vs actual carbs consumed
    # ─────────────────────────────────────────────────────────────────────────
    hours      = np.arange(0, dauer/60 + 1, 1)
    req_hourly = gewicht * 1.5                       # g carbs per kg per hour
    req_cum    = hours * req_hourly

    total_carbs = df_cart["carbs"].sum()

    df_req = pd.DataFrame({"Hour": hours, "Carbs": req_cum, "Type":"Required"})
    df_act = pd.DataFrame({
        "Hour":    [hours.max()],
        "Carbs":   [total_carbs],
        "Type":    ["Consumed"]
    })

    df_plot = pd.concat([df_req, df_act], ignore_index=True)

    st.subheader("Kumulative Kohlenhydrat-Zufuhr vs. Bedarf")
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

# ─────────────────────────────────────────────────────────────────────────────
# 3) Route-Map & GPX-Download
# ─────────────────────────────────────────────────────────────────────────────
if coords:
    m = folium.Map(location=coords[0], zoom_start=13)
    folium.PolyLine(coords, color="blue").add_to(m)
    for t in events:
        idx = min(int(t/dauer*len(coords)), len(coords)-1)
        lat, lon = coords[idx]
        folium.CircleMarker(
            (lat, lon),
            radius=5,
            color="red" if t%eat_int==0 else "yellow",
            fill=True
        ).add_to(m)
    st.subheader("Route & Timing auf der Karte")
    st_folium(m, width=700, height=400)
    st.download_button(
        "GPX herunterladen",
        gpx.to_xml(),
        file_name="route_intake.gpx",
        mime="application/gpx+xml"
    )
