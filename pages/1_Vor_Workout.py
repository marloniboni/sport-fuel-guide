import os
import streamlit as st
import pandas as pd
import requests
import gpxpy
import folium
from streamlit_folium import st_folium
import altair as alt
from requests_oauthlib import OAuth1Session

# ─────────────────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Sport-Fuel Guide", layout="wide")

# ─────────────────────────────────────────────────────────────────────────────
# 1) Vor-Workout Planung
# ─────────────────────────────────────────────────────────────────────────────
if 'gewicht' not in st.session_state:
    st.warning("Bitte gib zuerst deine Körperdaten auf der Startseite ein.")
    st.stop()
gewicht = st.session_state.gewicht

sportart = st.selectbox("Sportart", ["Laufen", "Radfahren", "Schwimmen"])
mode     = st.radio("Datenquelle wählen", ["GPX-Datei hochladen", "Manuelle Eingabe"])

if mode == "GPX-Datei hochladen":
    uploaded = st.file_uploader("GPX-Datei hochladen", type="gpx")
    if not uploaded:
        st.error("Bitte eine GPX-Datei hochladen.")
        st.stop()
    try:
        gpx = gpxpy.parse(uploaded.getvalue().decode())
        duration_sec = gpx.get_duration() or 0      # float seconds
        dauer        = duration_sec / 60
        distanz      = (gpx.length_3d() or 0) / 1000
        coords       = [
            (pt.latitude, pt.longitude)
            for tr in gpx.tracks
            for seg in tr.segments
            for pt in seg.points
        ]
    except Exception as e:
        st.error(f"Fehler beim Parsen der GPX-Datei: {e}")
        st.stop()
else:
    dauer   = st.slider("Dauer (Min)", 15, 300, 60)
    distanz = st.number_input("Distanz (km)", 0.0, 100.0, 10.0)
    coords  = []

st.markdown(f"**Dauer:** {dauer:.0f} Min • **Distanz:** {distanz:.2f} km")

faktoren   = {"Laufen": 7, "Radfahren": 5, "Schwimmen": 6}
cal_burn   = faktoren[sportart] * gewicht * (dauer / 60)
fluid_loss = 0.7 * (dauer / 60)

st.session_state['planned_calories'] = cal_burn
st.session_state['fluessigkeit']     = fluid_loss

st.subheader("Deine persönlichen Berechnungen")
st.write(f"Kalorienverbrauch: **{int(cal_burn)} kcal** • Flüssigkeitsverlust: **{fluid_loss:.2f} L**")

eat_int   = st.select_slider("Essen alle (Min)",   [15,20,30,45,60], value=30)
drink_int = st.select_slider("Trinken alle (Min)", [10,15,20,30],   value=15)

events    = sorted(
    set(range(eat_int,   int(dauer)+1, eat_int  )) |
    set(range(drink_int, int(dauer)+1, drink_int))
)
req_cal   = cal_burn   / len(events) if events else 0
req_fluid = fluid_loss / len(events) if events else 0

schedule = []
for t in events:
    row = {"Minute": t}
    if t % eat_int   == 0: row["Essen (kcal)"] = round(req_cal,   1)
    if t % drink_int == 0: row["Trinken (L)"]  = round(req_fluid, 3)
    schedule.append(row)

df_schedule = pd.DataFrame(schedule).set_index("Minute")
st.subheader("Dein persönlicher Intake-Plan")
st.table(df_schedule)

# ─────────────────────────────────────────────────────────────────────────────
# 2) Snack-Finder via USDA + Bilder + Auswahl
# ─────────────────────────────────────────────────────────────────────────────
FDC_API_KEY = "XDzSn37cJ5NRjskCXvg2lmlYUYptpq8tT68mPmPP"

@st.cache_data
def search_foods(query: str, limit: int=5):
    r = requests.get(
        "https://api.nal.usda.gov/fdc/v1/foods/search",
        params={'api_key': FDC_API_KEY, 'query':query, 'pageSize':limit}
    )
    r.raise_for_status()
    return r.json().get('foods', [])

@st.cache_data
def get_food_details(fdc_id: int):
    r = requests.get(
        f"https://api.nal.usda.gov/fdc/v1/food/{fdc_id}",
        params={'api_key': FDC_API_KEY}
    )
    r.raise_for_status()
    return r.json()

# Nutritionix credentials (or set them as Secrets in Streamlit Cloud)
NX_APP_ID  = os.getenv("NUTRITIONIX_APP_ID",  "9810d473")
NX_APP_KEY = os.getenv("NUTRITIONIX_APP_KEY", "f9668e402b5a79eaee8028e4aac19a04")

@st.cache_data
def fetch_image(item: str):
    r = requests.get(
        "https://trackapi.nutritionix.com/v2/search/instant",
        headers={'x-app-id':NX_APP_ID,'x-app-key':NX_APP_KEY},
        params={'query':item,'branded':'true'}
    )
    r.raise_for_status()
    branded = r.json().get('branded',[])
    return branded[0]['photo']['thumb'] if branded else None

# initialize cart once
if "cart" not in st.session_state:
    st.session_state.cart = []

st.subheader("🍌 Snack-Empfehlungen (USDA + Bilder)")
snack_query = st.text_input("Snack suchen (Schlagwort)", "")
if snack_query:
    foods = search_foods(snack_query, limit=5)
    if not foods:
        st.warning("Keine Produkte gefunden – versuche ein anderes Stichwort.")
    else:
        for food in foods:
            desc = food.get('description','Unbekannt')
            fdc  = food.get('fdcId')
            details = get_food_details(fdc)

            # pick first gram serving
            serv     = (details.get("servings",{}).get("serving") or [{}])[0]
            size_g   = float(serv.get("metric_serving_amount",0))
            cal_serv = float(serv.get("calories",0))
            grams_n  = (req_cal * size_g / cal_serv) if cal_serv else 0

            img = fetch_image(desc)
            c1, c2 = st.columns([5,1])
            with c1:
                if img:
                    st.image(img, width=64)
                st.markdown(f"**{desc}**  —  {size_g:.0f} g → **{cal_serv:.0f} kcal**")
                st.caption(f"Portionsgröße: {size_g:.0f} g")
            # on click: add one serving (with its cal_serv) to cart
            if c2.button("➕", key=f"add_{fdc}"):
                existing = [item['fdc'] for item in st.session_state.cart]
                if fdc not in existing:
                    st.session_state.cart.append({
                        "fdc":         fdc,
                        "description": desc,
                        "cal_serv":    cal_serv
                    })

        # render cart & line-chart
        cart = st.session_state.cart
        if cart:
            st.subheader("Deine ausgewählten Snacks")
            df_cart = pd.DataFrame(cart)
            df_cart["cumsum"] = df_cart["cal_serv"].cumsum()
            df_cart["step"]   = list(range(1, len(df_cart)+1))
            st.table(df_cart[["description","cal_serv"]].rename(
                columns={"description":"Snack","cal_serv":"kcal"}))

            # build the line chart: consumed vs burned
            df_chart = df_cart[["step","cumsum"]].copy()
            df_chart["burned"] = df_chart["step"]/len(df_chart) * cal_burn

            df_long = df_chart.melt(
                id_vars=["step"],
                value_vars=["cumsum","burned"],
                var_name="Type",
                value_name="kcal"
            ).replace({"cumsum":"Consumed","burned":"Burned"})

            st.subheader("Kumulativ: Verbraucht vs. Gegessen")
            line = (
                alt.Chart(df_long)
                   .mark_line(point=True)
                   .encode(
                       x=alt.X("step:Q",     title="Auswahl-Schritt"),
                       y=alt.Y("kcal:Q",     title="kcal"),
                       color="Type:N",
                       tooltip=["Type","kcal"]
                   )
                   .properties(width=600, height=350)
            )
            st.altair_chart(line, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# 3) Verbrauch vs. kumulative Aufnahme über die ganze Dauer
# ─────────────────────────────────────────────────────────────────────────────
mins     = list(range(int(dauer)+1))
burned   = [cal_burn/dauer * m for m in mins]
ingested = [req_cal if m in events else 0 for m in mins]

df3 = pd.DataFrame({
    "Minute": mins,
    "Burned": burned,
    "Ingested": ingested
})
df3["Cum Aufnahme"] = df3["Ingested"].cumsum()
df3["Netto"]       = df3["Burned"] - df3["Cum Aufnahme"]

base      = alt.Chart(df3).encode(
    x=alt.X("Minute:Q", axis=alt.Axis(title="Minute"))
)
burn_line = base.mark_line(strokeWidth=2).encode(
    y=alt.Y("Burned:Q",      axis=alt.Axis(title="kcal verbrannt")),
    color=alt.value("blue")
)
eat_line  = base.mark_line(strokeDash=[4,2]).encode(
    y=alt.Y("Cum Aufnahme:Q", axis=alt.Axis(title="kcal kumuliert")),
    color=alt.value("orange")
)
net_line  = base.mark_line(opacity=0.7).encode(
    y=alt.Y("Netto:Q",        axis=alt.Axis(title="kcal Differenz")),
    color=alt.value("green")
)
st.subheader("Verbrauch vs. kumulative Aufnahme & Netto-Bilanz")
st.altair_chart(alt.layer(burn_line,eat_line,net_line).properties(
    width=700, height=400
), use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# 4) Route Map & GPX-Download
# ─────────────────────────────────────────────────────────────────────────────
if coords:
    m = folium.Map(location=coords[0], zoom_start=13)
    folium.PolyLine(coords, color="blue").add_to(m)
    for t in events:
        idx = min(int(t/dauer*len(coords)), len(coords)-1)
        lat, lon = coords[idx]
        folium.CircleMarker((lat,lon),
                            radius=5,
                            color="red" if t%eat_int==0 else "yellow",
                            fill=True).add_to(m)
    st.subheader("Route & Timing auf der Karte")
    st_folium(m, width=700, height=400)
    st.download_button(
        "GPX herunterladen",
        gpx.to_xml(),
        file_name="route_intake.gpx",
        mime="application/gpx+xml"
    )
