# pages/2_Nach_Workout.py
# -*- coding: utf-8 -*-

import streamlit as st
import pandas as pd
import numpy as np
from fitparse import FitFile
import importlib.util
import os
import matplotlib.pyplot as plt

# --------------------------------------------
# Nach-Workout-Auswertung: FIT-Daten & Vergleiche
# --------------------------------------------

# VO₂-Plan aus Pre-Workout-Seite importieren
spec = importlib.util.spec_from_file_location(
    "vor_module", os.path.join("pages", "1_Vor_Workout.py")
)
vor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vor)


def parse_fit(fitfile):
    """
    Liest ein FIT-File ein und extrahiert:
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
    distance = session.get('total_distance', df.get('distance', pd.Series()).max())
    timer = session.get(
        'total_timer_time',
        (df['timestamp'].max() - df['timestamp'].min()).total_seconds()
    )
    avg_hr = df['heart_rate'].mean() if 'heart_rate' in df else None
    max_hr = df['heart_rate'].max() if 'heart_rate' in df else None
    return {
        'df': df,
        'distance_m': distance,
        'time_s': timer,
        'avg_hr': avg_hr,
        'max_hr': max_hr
    }


def calc_calories_keytel(avg_hr, weight, age, gender, duration_min):
    if None in (avg_hr, weight, age, gender):
        return None
    if gender == 1:
        a, b, c, d = 0.6309, 0.1988, 0.2017, -55.0969
    else:
        a, b, c, d = 0.4472, 0.1263, 0.0740, -20.4022
    e_dot = (a * avg_hr + b * weight + c * age + d) / 4.184
    return e_dot * duration_min


def calc_fluid_loss(calories, hours):
    if calories is None or hours <= 0:
        return None
    lph = 1.38e-3 * (calories / hours)
    return lph * hours


def main():
    st.title('Nach-Workout-Analyse')
    st.write('Upload .fit und Vergleich mit vorherigem Workout-Plan')

    # Prüfen, ob Profil und Plan bereits gesetzt sind
    needed = ['gewicht', 'alter', 'groesse', 'geschlecht', 'planned_calories', 'fluessigkeit']
    missing = [k for k in needed if k not in st.session_state]
    if missing:
        st.error('Bitte zuerst Profil und Vor-Workout-Plan auf den jeweiligen Seiten ausfüllen.')
        return

    # Werte aus Session holen
    weight = st.session_state['gewicht']
    age    = st.session_state['alter']
    height = st.session_state['groesse']
    gender_str = st.session_state['geschlecht']
    gender = 1 if gender_str == 'Männlich' else 2
    planned_cal = st.session_state['planned_calories']
    planned_fluid = st.session_state['fluessigkeit']

    uploaded = st.file_uploader('Deine .fit-Datei auswählen', type='fit')
    if not uploaded:
        st.info('Bitte deine FIT-Datei hochladen.')
        return

    # FIT parsen
    data = parse_fit(uploaded)
    if not data:
        return
    df = data['df']
    t_min = data['time_s'] / 60
    t_h = data['time_s'] / 3600

    # FIT-Kennzahlen anzeigen
    st.subheader('FIT-Kennzahlen')
    c1, c2, c3 = st.columns(3)
    c1.metric('Distanz (km)', f"{data['distance_m']/1000:.2f}")
    c2.metric('Dauer (min)', f"{t_min:.1f}")
    c3.metric('Ø-Herzfr. (bpm)', f"{data['avg_hr']:.0f}" if data['avg_hr'] else 'n/a')

    # Berechnete Ist-Werte
    actual_cal = calc_calories_keytel(data['avg_hr'], weight, age, gender, t_min)
    actual_fluid= calc_fluid_loss(actual_cal, t_h)

    # Differenzen
    diff_cal = (actual_cal or 0) - (planned_cal or 0)
    diff_fl  = (actual_fluid or 0) - (planned_fluid or 0)

    # Visualisierung: Donuts nebeneinander
    st.subheader('Vergleich: Ist vs. Plan')
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    # Kalorien
    ax1.pie([actual_cal or 0, planned_cal or 0], labels=['Ist', 'Plan'],
            autopct='%1.0f kcal', startangle=90, wedgeprops={'width': 0.4})
    ax1.set_title(f'Kalorien Δ {diff_cal:+.0f} kcal')
    ax1.set(aspect='equal')
    # Flüssigkeit
    ax2.pie([actual_fluid or 0, planned_fluid or 0], labels=['Ist', 'Empf.'],
            autopct='%1.2f L', startangle=90, wedgeprops={'width': 0.4})
    ax2.set_title(f'Flüssigkeit Δ {diff_fl:+.2f} L')
    ax2.set(aspect='equal')
    st.pyplot(fig)

    st.markdown('---')
    st.info('Nur FIT hochladen – alle Vergleichswerte kommen aus vorherigen Eingaben.')

if __name__ == '__main__':
    main()
