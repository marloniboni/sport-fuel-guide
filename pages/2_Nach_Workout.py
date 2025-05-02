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
    user_profile = {}

    for msg in fit.get_messages():
        if msg.name == 'record':
            records.append({f.name: f.value for f in msg.fields})
        elif msg.name == 'session':
            for f in msg.fields:
                session[f.name] = f.value
        elif msg.name == 'user_profile':
            for f in msg.fields:
                user_profile[f.name] = f.value

    if not records:
        st.error('Keine Daten im FIT-File gefunden.')
        return {}

    df = pd.DataFrame(records)

    # Basismetriken
    total_distance = session.get(
        'total_distance',
        df['distance'].max() if 'distance' in df else 0
    )
    total_time = session.get(
        'total_timer_time',
        (df['timestamp'].max() - df['timestamp'].min()).total_seconds()
        if 'timestamp' in df else 0
    )

    # Herzfrequenz
    avg_hr = df['heart_rate'].mean() if 'heart_rate' in df else None
    max_hr = df['heart_rate'].max() if 'heart_rate' in df else None

    # Profildaten
    weight = user_profile.get('weight')  # kg
    age = user_profile.get('age')        # Jahre
    gender = user_profile.get('gender')  # 1=male, 2=female

    return {
        'df': df,
        'total_distance_m': total_distance,
        'total_time_s': total_time,
        'avg_hr': avg_hr,
        'max_hr': max_hr,
        'weight_kg': weight,
        'age': age,
        'gender': gender
    }


def calc_calories_keytel(avg_hr, weight, age, gender, duration_min):
    """
    Keytel-Formel zur Schätzung des Kalorienverbrauchs (kcal/min).
    gender: 1=male, 2=female per FIT-Profil
    """
    if None in (avg_hr, weight, age, gender):
        return None

    # Parameter laut Keytel et al. (2005)
    if gender == 1:
        a, b, c, d = 0.6309, 0.1988, 0.2017, -55.0969
    else:
        a, b, c, d = 0.4472, 0.1263, 0.0740, -20.4022

    # kcal/min
    e_dot = (a * avg_hr + b * weight + c * age + d) / 4.184
    # Gesamtverbrauch kcal
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
    st.write('Upload einer .fit-Datei → Kennzahlen anzeigen & Formeln anwenden')

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

    # FIT-Datei Werte anzeigen
    st.subheader('FIT-Datei Kennzahlen')
    col1, col2, col3 = st.columns(3)
    col1.metric('Distanz (km)', f"{data['total_distance_m'] / 1000:.2f}")
    col2.metric('Dauer (min)', f"{duration_min:.1f}")
    col3.metric(
        'Ø-Herzfrequenz (bpm)',
        f"{data['avg_hr']:.0f}" if data['avg_hr'] else 'n/a'
    )

    col4, col5, col6 = st.columns(3)
    col4.metric(
        'Max-Herzfrequenz (bpm)',
        f"{data['max_hr']:.0f}" if data['max_hr'] else 'n/a'
    )
    col5.metric(
        'Gewicht (kg)',
        f"{data['weight_kg']:.1f}" if data['weight_kg'] else 'n/a'
    )
    col6.metric(
        'Alter (Jahre)',
        f"{data['age']}" if data['age'] else 'n/a'
    )

    # Berechnungen
    calories = calc_calories_keytel(
        data['avg_hr'],
        data['weight_kg'],
        data['age'],
        data['gender'],
        duration_min
    )
    fluid_loss = calc_fluid_loss(calories, duration_h)

    st.subheader('Berechnete Werte')
    c1, c2 = st.columns(2)
    c1.metric(
        'Kalorien (Keytel)',
        f"{calories:.0f} kcal" if calories else 'n/a'
    )
    c2.metric(
        'Flüssigkeitsverlust',
        f"{fluid_loss:.2f} L" if fluid_loss else 'n/a'
    )

    st.markdown('---')
    st.info('Formeln: Keytel et al. für Kalorien; Schweißrate-Schätzung für Flüssigkeit')


if __name__ == '__main__':
    main()
