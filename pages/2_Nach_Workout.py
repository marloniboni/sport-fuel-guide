# pages/2_Nach_Workout.py
# -*- coding: utf-8 -*-

import streamlit as st
import pandas as pd
import numpy as np
from fitparse import FitFile

# --------------------------------------------
# Nach-Workout-Auswertung: FIT-Daten & Berechnungen
# - Liest Kennzahlen aus .fit-Datei aus
# - Berechnet Kalorienverbrauch (Keytel-Formel)
# - Schätzt Flüssigkeitsverlust (Schweißrate)
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
            session.update({f.name: f.value for f in msg.fields})
        elif msg.name == 'user_profile':
            user_profile.update({f.name: f.value for f in msg.fields})

    if not records:
        st.error('Keine Daten im FIT-File gefunden.')
        return {}

    df = pd.DataFrame(records)

    # Basismetriken
    total_distance = session.get('total_distance', df.get('distance', pd.Series()).max())
    total_time = session.get(
        'total_timer_time',
        (df['timestamp'].max() - df['timestamp'].min()).total_seconds()
    )
    avg_hr = df['heart_rate'].mean() if 'heart_rate' in df else None
    max_hr = df['heart_rate'].max() if 'heart_rate' in df else None

    # Profildaten
    weight = user_profile.get('weight')  # kg
    age = user_profile.get('age')       # Jahre
    gender = user_profile.get('gender') # 1=male,2=female

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
