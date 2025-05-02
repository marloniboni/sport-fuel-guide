# pages/2_Nach_Workout.py
# -*- coding: utf-8 -*-

import streamlit as st
import pandas as pd
import numpy as np
from fitparse import FitFile
import matplotlib.pyplot as plt

# --------------------------------------------
# Nach-Workout-Auswertung: FIT-Daten & Vergleiche
# --------------------------------------------

def parse_fit(fitfile):
    """
    Liest .fit-Datei ein und extrahiert:
      - DataFrame aller Records
      - Basis-Metriken: Distanz, Dauer, Herzfrequenz (avg/max)
    """
    fit = FitFile(fitfile)
    records, session = [], {}
    for msg in fit.get_messages():
        if msg.name == 'record':
            records.append({f.name: f.value for f in msg.fields})
        elif msg.name == 'session':
            session.update({f.name: f.value for f in msg.fields})
    if not records:
        st.error('Keine Daten im FIT-File gefunden.')
        return {}

    df = pd.DataFrame(records)
    dist = session.get('total_distance', df.get('distance', pd.Series()).max())
    t_s = session.get(
        'total_timer_time',
        (df['timestamp'].max() - df['timestamp'].min()).total_seconds()
        if 'timestamp' in df else 0
    )
    avg_hr = df['heart_rate'].mean() if 'heart_rate' in df else None
    max_hr = df['heart_rate'].max() if 'heart_rate' in df else None
    return {'df': df, 'distance_m': dist, 'time_s': t_s, 'avg_hr': avg_hr, 'max_hr': max_hr}


def calc_calories_keytel(hr, weight, age, gender, duration_min):
    """Keytel-Formel (kcal/min)"""
    if None in (hr, weight, age, gender):
        return None
    if gender == 'Männlich':
        a,b,c,d = 0.6309,0.1988,0.2017,-55.0969
    else:
        a,b,c,d = 0.4472,0.1263,0.0740,-20.4022
    e_dot = (a*hr + b*weight + c*age + d) / 4.184
    return e_dot * duration_min


def calc_fluid_loss(calories, hours):
    """Flüssigkeitsverlust (L) ~1.38e-3 * kcal/h"""
    if calories is None or hours<=0:
        return None
    return (1.38e-3 * (calories/hours)) * hours


def main():
    st.title('Nach-Workout-Analyse')
    st.write('Nur .fit hochladen – Rest kommt aus vorherigem Plan')

    # Prüfen Session-State
    keys = ['gewicht','alter','groesse','geschlecht','planned_calories','fluessigkeit']
    missing = [k for k in keys if k not in st.session_state]
    if missing:
        st.error('Bitte zuerst Profil & Vor-Workout-Plan auf den entsprechenden Seiten ausfüllen: ' + ', '.join(missing))
        return

    # Session-Werte
    weight = st.session_state['gewicht']
    age = st.session_state['alter']
    height = st.session_state['groesse']
    gender = st.session_state['geschlecht']
    planned_cal = st.session_state['planned_calories']
    planned_fluid = st.session_state['fluessigkeit']

    # FIT-Upload
    uploaded = st.file_uploader('Deine .fit-Datei auswählen', type='fit')
    if not uploaded:
        st.info('Bitte .fit-Datei hochladen')
        return

    data = parse_fit(uploaded)
    if not data:
        return
    t_min = data['time_s']/60
    t_h = data['time_s']/3600

    # Anzeige FIT-Werte
    st.subheader('FIT-Kennzahlen')
    cols = st.columns(3)
    cols[0].metric('Distanz (km)', f"{data['distance_m']/1000:.2f}")
    cols[1].metric('Dauer (min)', f"{t_min:.1f}")
    cols[2].metric('Ø-Herzfr. (bpm)', f"{data['avg_hr']:.0f}" if data['avg_hr'] else 'n/a')

    st.subheader('Berechnete Ist-Werte')
    actual_cal = calc_calories_keytel(data['avg_hr'], weight, age, gender, t_min)
    actual_fluid = calc_fluid_loss(actual_cal, t_h)

    # Differenzen
    dcal = (actual_cal or 0) - planned_cal
    dflu = (actual_fluid or 0) - planned_fluid

    # Donut-Charts nebeneinander
    st.subheader('Vergleich Ist vs. Plan')
    fig, axes = plt.subplots(1,2,figsize=(10,4))
    # Kalorien
    axes[0].pie([actual_cal, planned_cal], labels=['Ist','Plan'],
                autopct=lambda pct: f"{(pct/100)*(actual_cal+planned_cal):.0f} kcal",
                startangle=90, wedgeprops={'width':0.4})
    axes[0].set_title(f'Δ {dcal:+.0f} kcal')
    axes[0].set(aspect='equal')
    # Flüssigkeit
    axes[1].pie([actual_fluid, planned_fluid], labels=['Ist','Empf.'],
                autopct=lambda pct: f"{(pct/100)*(actual_fluid+planned_fluid):.2f} L",
                startangle=90, wedgeprops={'width':0.4})
    axes[1].set_title(f'Δ {dflu:+.2f} L')
    axes[1].set(aspect='equal')
    st.pyplot(fig)

    st.markdown('---')
    st.info('Profil & Plan: Home- und Vor-Workout-Seite; hier nur .fit ergänzen.')

if __name__ == '__main__':
    main()
