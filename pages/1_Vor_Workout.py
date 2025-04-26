import streamlit as st
import pandas as pd
import requests
import os
import gpxpy
import folium
import re
from streamlit_folium import st_folium
import gpxpy.gpx as gpx_module
import altair as alt

# --- FatSecret OAuth2 Token Fetch ---
FS_CLIENT_ID = os.getenv("FASTSECRET_CLIENT_ID", "9ced8a2df62549a594700464259c95de")
FS_CLIENT_SECRET = os.getenv("FASTSECRET_CLIENT_SECRET", "367bfc354031445abe67c34459ea95d2")
@st.cache_data
def fetch_fs_token():
    """
    Fetch OAuth2 Bearer token from FatSecret.
    """
    token_url = "https://platform.fatsecret.com/connect/token"
    payload = {'grant_type': 'client_credentials'}
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    resp = requests.post(
        token_url,
        data=payload,
        auth=(FS_CLIENT_ID, FS_CLIENT_SECRET),
        headers=headers
    )
    # Debugging output
    st.write("Token Fetch Status Code:", resp.status_code)
    st.write("Token Fetch Response Text (truncated):", resp.text[:200])
    if resp.status_code != 200:
        st.error(f"Token-Fehler: {resp.status_code}")
        return None
    try:
        token = resp.json().get('access_token')
        if not token:
            st.error(f"Kein access_token im Response. Ganzes JSON: {resp.json()}")
        return token
    except ValueError:
        st.error(f"Token-JSON-Decode-Fehler: {resp.text}")
        return None
    except ValueError:
        st.error(f"Token JSON-Decode Fehler: {resp.text}")
        return None

# --- App Title & Data Check ---
st.title("⚡ Vor-Workout Planung")
if 'gewicht' not in st.session_state:
    st.warning("Bitte gib zuerst deine Körperdaten auf der Startseite ein.")
    st.stop()
gewicht = st.session_state.gewicht
grundumsatz = st.session_state.grundumsatz
fluessigkeit_tag = st.session_state.fluessigkeit
sportart = st.selectbox("Sportart", ["Laufen","Radfahren","Schwimmen","Triathlon"])

# --- GPX Parsing Helper ---
def parse_gpx(text):
    g = gpxpy.parse(text)
    secs = g.get_duration() or 0
    dist = (g.length_3d() or 0) / 1000
    pts = [(pt.latitude, pt.longitude) for tr in g.tracks for seg in tr.segments for pt in seg.points]
    return secs/60, dist, pts, g

# --- Input Mode: File or Manual ---
mode = st.radio("Datenquelle", ["GPX-Datei", "Manuelle Eingabe"])
if mode == "GPX-Datei":
    up = st.file_uploader("GPX-Datei hochladen", type='gpx')
    if not up:
        st.error("Bitte lade eine GPX-Datei hoch.")
        st.stop()
    dauer, distanz, coords, gpx_obj = parse_gpx(up.read().decode())
else:
    dauer = st.slider("Dauer (Min)", 15, 300, 60)
    distanz = st.number_input("Distanz (km)", 0.0, 100.0, 10.0)
    coords = []
st.write(f"Dauer: {dauer} Min, Distanz: {distanz} km")

# --- Compute metrics ---
facts = {"Laufen":{"Leicht":7,"Mittel":9,"Hart":12},"Radfahren":{"Leicht":5,"Mittel":7,"Hart":10},
         "Schwimmen":{"Leicht":6,"Mittel":8,"Hart":11},"Triathlon":{"Leicht":6,"Mittel":9,"Hart":13}}
intensity = st.select_slider("Intensität", ["Leicht","Mittel","Hart"])
cal_hr = facts[sportart][intensity] * gewicht
cal_tot = cal_hr * (dauer/60)
flu_tot = 0.7 * (dauer/60)

# --- Schedule Intake ---
if dauer <= 60:
    eat_i = 20
elif dauer <= 120:
    eat_i = 30
elif dauer <= 180:
    eat_i = 45
else:
    eat_i = 60
drink_i = 15
events = sorted(set(range(eat_i, int(dauer)+1, eat_i)) | set(range(drink_i, int(dauer)+1, drink_i)))

# --- Intake Plan Table ---
sched = []
for t in events:
    row = {'Minute': t}
    if t % eat_i == 0:
        row['Essen (kcal)'] = int(cal_tot/(dauer/eat_i))
    if t % drink_i == 0:
        row['Trinken (L)'] = round(flu_tot/(dauer/drink_i), 2)
    sched.append(row)
df_sched = pd.DataFrame(sched).set_index('Minute')
st.markdown("---")
st.subheader("⏰ Intake-Plan: Essen & Trinken")
st.table(df_sched)

# --- Snack via FatSecret v4 API ---
st.markdown("---")
st.subheader("🍪 Snack-Optionen über FatSecret API")
required_cal = cal_tot/(dauer/eat_i)
st.write(f"Benötigte Kalorien pro Snack: **{required_cal:.0f} kcal**")
snack_query = st.text_input("Snack-Name suchen (optional)", value="")
default_snacks = ["Clif Bar","Honey Stinger Gel","Gatorade","Powerbar","Isostar Riegel"]
queries = [snack_query] if snack_query.strip() else default_snacks
token = fetch_fs_token()
if not token:
    st.warning("Konnte kein Access Token von FatSecret abrufen. Snacks werden übersprungen.")
    skip_fs = True
else:
    skip_fs = False
headers = {'Authorization': f"Bearer {token}"}
if skip_fs:
    pass  # skip snack block
else:
    for q in queries:
        if not snack_query.strip():
            st.markdown(f"**Vorschlag:** {q}")
        # Search using Food Search v2
        search_resp = requests.get(
            "https://platform.fatsecret.com/rest/server.api",
            params={'method':'foods.search','search_expression':q,'format':'json'},
            auth=(FS_CLIENT_ID, FS_CLIENT_SECRET)
        )
        items = search_resp.json().get('foods',{}).get('food',[])[:5]
        for item in items:
            fid = item['food_id']
            name = item['food_name']
            # Fetch details via v4 endpoint
            detail_resp = requests.get(
                f"https://platform.fatsecret.com/rest/food/v4?food_id={fid}&format=json",
                headers=headers
            )
            data = detail_resp.json().get('food', {})
            servings = data.get('servings',[])
            for serv in servings:
                cal = serv.get('calories',0)
                fat = serv.get('fat',0)
                protein = serv.get('protein',0)
                carbs = serv.get('carbohydrate',0)
                num = required_cal / cal if cal>0 else 0
                col1, col2 = st.columns([2,1])
                col1.markdown(f"**{name}**: {cal} kcal/Portion · **{num:.2f} Portion(en)**")
                dfm = pd.DataFrame({'Makronährstoff':['Fett','Protein','Kohlenhydrate'],'Gramm':[fat,protein,carbs]})
                radar = alt.Chart(dfm).mark_area(interpolate='linear',opacity=0.5).encode(
                    theta=alt.Theta('Makronährstoff:N',sort=['Fett','Protein','Kohlenhydrate']),
                    radius=alt.Radius('Gramm:Q'),color='Makronährstoff:N',tooltip=['Makronährstoff','Gramm']
                ).properties(width=150,height=150)
                col2.altair_chart(radar, use_container_width=False)
    if not snack_query.strip(): st.markdown(f"**Vorschlag:** {q}")
    # Search using Food Search v2
    search_resp = requests.get(
        "https://platform.fatsecret.com/rest/server.api",
        params={'method':'foods.search','search_expression':q,'format':'json'},
        auth=(FS_CLIENT_ID, FS_CLIENT_SECRET)
    )
    items = search_resp.json().get('foods',{}).get('food',[])[:5]
    for item in items:
        fid = item['food_id']
        name = item['food_name']
        # Fetch details via v4 endpoint
        detail_resp = requests.get(
            f"https://platform.fatsecret.com/rest/food/v4?food_id={fid}&format=json",
            headers=headers
        )
        data = detail_resp.json().get('food', {})
        servings = data.get('servings',[])
        for serv in servings:
            cal = serv.get('calories',0)
            fat = serv.get('fat',0)
            protein = serv.get('protein',0)
            carbs = serv.get('carbohydrate',0)
            num = required_cal / cal if cal>0 else 0
            col1, col2 = st.columns([2,1])
            col1.markdown(f"**{name}**: {cal} kcal/Portion · **{num:.2f} Portion(en)**")
            dfm = pd.DataFrame({'Makronährstoff':['Fett','Protein','Kohlenhydrate'],'Gramm':[fat,protein,carbs]})
            radar = alt.Chart(dfm).mark_area(interpolate='linear',opacity=0.5).encode(
                theta=alt.Theta('Makronährstoff:N',sort=['Fett','Protein','Kohlenhydrate']),
                radius=alt.Radius('Gramm:Q'),color='Makronährstoff:N',tooltip=['Makronährstoff','Gramm']
            ).properties(width=150,height=150)
            col2.altair_chart(radar, use_container_width=False)

# --- Build time series for cumulative charts ---
mins=list(range(0,int(dauer)+1))
c_rate=cal_hr/60
f_rate=0.7/60
cal_cum_cons=[c_rate*m for m in mins]
flu_cum_cons=[f_rate*m for m in mins]
eat_events=set(range(eat_i,int(dauer)+1,eat_i))
drink_events=set(range(drink_i,int(dauer)+1,drink_i))
cal_amt=cal_tot/len(eat_events) if eat_events else 0
flu_amt=flu_tot/len(drink_events) if drink_events else 0
cum=0
cal_cum_int=[]
for m in mins:
    if m in eat_events: cum+=cal_amt
    cal_cum_int.append(cum)
cum=0
flu_cum_int=[]
for m in mins:
    if m in drink_events: cum+=flu_amt
    flu_cum_int.append(cum)
chart_df=pd.DataFrame({'Minute':mins,'Cal consumption':cal_cum_cons,'Cal intake':cal_cum_int,
                       'Flu consumption':flu_cum_cons,'Flu intake':flu_cum_int})

st.markdown("---")
st.subheader("📊 Kumulative Verbrauch vs. Zufuhr")
cal_base=alt.Chart(chart_df).encode(x='Minute:Q')
cal_line=cal_base.mark_line(color='orange').encode(y='Cal consumption:Q')
cal_int_line=cal_base.mark_line(color='red',strokeDash=[4,2]).encode(y='Cal intake:Q')
flu_base=alt.Chart(chart_df).encode(x='Minute:Q')
flu_line=flu_base.mark_line(color='blue').encode(y='Flu consumption:Q')
flu_int_line=flu_base.mark_line(color='cyan',strokeDash=[4,2]).encode(y='Flu intake:Q')
st.altair_chart(alt.hconcat((cal_line+cal_int_line).properties(width=300,title='Kalorien'),
                            (flu_line+flu_int_line).properties(width=300,title='Flüssigkeit')),
                 use_container_width=True)

# --- Interactive Map & GPX Export ---
st.markdown("---")
st.subheader("🗺️ Route & Intake-Punkte")
m=folium.Map(location=coords[0] if coords else [0,0],zoom_start=13)
if coords:
    folium.PolyLine(coords,color='blue',weight=3).add_to(m)
    for t in events:
        idx=min(int(t/dauer*len(coords)),len(coords)-1)
        lat,lon=coords[idx]
        color='orange' if t in eat_events else 'cyan'
        folium.CircleMarker(location=(lat,lon),radius=6,popup=f"{t} Min",color=color,fill=True).add_to(m)
st_folium(m,width=700,height=500)

if 'gpx_obj' in locals():
    export=gpx_module.GPX();trk=gpx_module.GPXTrack();export.tracks.append(trk)
    seg=gpx_module.GPXTrackSegment();trk.segments.append(seg)
    [seg.points.append(gpx_module.GPXTrackPoint(lat,lon)) for lat,lon in coords]
    [export.waypoints.append(gpx_module.GPXWaypoint(coords[min(int(t/dauer*len(coords)),len(coords)-1)][0],
     coords[min(int(t/dauer*len(coords)),len(coords)-1)][1],name=f"{t} Min")) for t in events]
    st.download_button("Download GPX mit Intake-Punkten",export.to_xml(),file_name="route_intake.gpx",mime="application/gpx+xml")

st.info("Workflow mit FatSecret v4 API und Altair-Visualisierung.")
