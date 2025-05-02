# pages/2_Nach_Workout.py
# -*- coding: utf-8 -*-

import streamlit as st
import pandas as pd
import numpy as np
from fitparse import FitFile

# --------------------------------------------
# Nach-Workout-Auswertung: FIT-Daten & Berechnungen
# --------------------------------------------

def parse_fit(fitfile):
    """
    Liest ein FIT-File ein und extrahiert:
      - DataFrame mit allen 'record'-Daten
      - Basis-Metriken: Distanz, Zeit, Herzfrequenz (avg/max)
      - Optional: Geschwindigkeit, Leistung, Kadenz, Temperatur, Höhenmeter
    """
    fit = FitFile(fitfile)
    records = []
    session = {}

    for msg in fit.get_messages():
        if msg.name == 'record':
            records.append({f.name: f.value for f in msg.fields})
        elif msg.name == 'session':
            session.update({f.name: f.value for f in msg.fields})

    if not records:
        st.error('Keine Daten im FIT-File gefunden.')
        return {}

    df = pd.DataFrame(records)
    distance = session.get('total_distance', df['distance'].max() if 'distance' in df else 0)
    timer = session.get('total_timer_time', (df['timestamp'].max() - df['timestamp'].min()).total_seconds() if 'timestamp' in df else 0)
    avg_hr = df['heart_rate'].mean() if 'heart_rate' in df else None
    max_hr = df['heart_rate'].max() if 'heart_rate' in df else None

    return {
        'df': df,
        'total_distance_m': distance,
        'total_time_s': timer,
        'avg_hr': avg_hr,
        'max_hr': max_hr
    }


def calc_calories_keytel(avg_hr, weight, age, gender, duration_min):
    """
    Keytel-Formel zur Schätzung des Kalorienverbrauchs (kcal/min).
    gender: 1=male, 2=female
    """
    if None in (avg_hr, weight, age, gender):
        return None
    if gender == 1:
        a, b, c, d = 0.6309, 0.1988, 0.2017, -55.0969
    else:
        a, b, c, d = 0.4472, 0.1263, 0.0740, -20.4022
    e_dot = (a * avg_hr + b * weight + c * age + d) / 4.184
    return e_dot * duration_min


def calc_fluid_loss(calories_total, duration_h):
    """
    Schätzung des Flüssigkeitsverlusts (Liter):
      V_sw [L/h] ≈ 1.38e-3 * E [kcal/h]
    """
    if calories_total is None or duration_h <= 0:
        return None
    kcal_per_h = calories_total / duration_h
    sweat_l_per_h = 1.38e-3 * kcal_per_h
    return sweat_l_per_h * duration_h


def main():
    st.title('Nach-Workout-Analyse')
    st.write('Lade deine .fit-Datei hoch und ergänze ggf. Profildaten für Berechnungen')

    # Profildaten aus session_state oder Eingabe
    weight = st.session_state.get('gewicht')
    if weight is None:
        weight = st.number_input('Gewicht (kg)', min_value=40.0, max_value=150.0, value=70.0)
        st.session_state['gewicht'] = weight
    age = st.session_state.get('alter')
    if age is None:
        age = st.number_input('Alter (Jahre)', min_value=12, max_value=80, value=25)
        st.session_state['alter'] = age
    height = st.session_state.get('groesse')
    if height is None:
        height = st.number_input('Körpergröße (cm)', min_value=140, max_value=210, value=175)
        st.session_state['groesse'] = height
    gender_str = st.session_state.get('geschlecht')
    if gender_str is None:
        gender_str = st.selectbox('Geschlecht', ['Männlich', 'Weiblich'])
        st.session_state['geschlecht'] = gender_str
    gender = 1 if gender_str == 'Männlich' else 2

    uploaded = st.file_uploader('Deine .fit-Datei auswählen', type='fit')
    if not uploaded:
        st.info('Bitte lade zuerst eine .fit-Datei hoch.')
        return

    data = parse_fit(uploaded)
    if not data:
        return

    df = data['df']
    duration_s = data['total_time_s']
    duration_min = duration_s / 60.0
    duration_h = duration_s / 3600.0

    # Anzeige FIT-Werte
    st.subheader('FIT-Datei Kennzahlen')
    c1, c2, c3 = st.columns(3)
    c1.metric('Distanz (km)', f"{data['total_distance_m']/1000:.2f}")
    c2.metric('Dauer (min)', f"{duration_min:.1f}")
    c3.metric('Ø-Herzfrequenz (bpm)', f"{data['avg_hr']:.0f}" if data['avg_hr'] else 'n/a')
    c4, c5, c6 = st.columns(3)
    c4.metric('Max-Herzfrequenz (bpm)', f"{data['max_hr']:.0f}" if data['max_hr'] else 'n/a')
    c5.metric('Gewicht (kg)', f"{weight:.1f}")
    c6.metric('Alter (Jahre)', f"{age}")
    st.metric('Körpergröße (cm)', f"{height}")

    # Berechnungen
    calories = calc_calories_keytel(data['avg_hr'], weight, age, gender, duration_min)
    fluid = calc_fluid_loss(calories, duration_h)

    st.subheader('Berechnete Werte')
    d1, d2 = st.columns(2)
    d1.metric('Kalorien (Keytel)', f"{calories:.0f} kcal" if calories else 'n/a')
    d2.metric('Flüssigkeitsverlust (L)', f"{fluid:.2f}" if fluid else 'n/a')

    st.markdown('---')
    st.info('Formeln: Keytel et al. für Kalorien; Schweißrate-Schätzung für Flüssigkeit')

if __name__ == '__main__':
    main()
