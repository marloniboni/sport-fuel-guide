# pages/2_Nach_Workout.py


import streamlit as st
import pandas as pd
import numpy as np
from fitparse import FitFile
import importlib.util
import os
import matplotlib.pyplot as plt

# Nach-Workout-Auswertung: FIT-Daten, Berechnungen & Vergleiche


# VO₂-Plan aus Pre-Workout-Seite importieren
spec = importlib.util.spec_from_file_location(
    "vor_module", os.path.join("pages", "1_Vor_Workout.py")
)
vor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vor)


def parse_fit(fitfile):
    """
    Liest ein FIT-File ein und extrahiert:
      - DataFrame mit allen 'record'-Daten
      - Basis-Metriken: Distanz, Zeit, Herzfrequenz (avg/max)
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
    timer = session.get(
        'total_timer_time',
        (df['timestamp'].max() - df['timestamp'].min()).total_seconds() if 'timestamp' in df else 0
    )
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
    st.write('Upload einer .fit-Datei → Analysiere Ride & vergleiche mit Vor-Workout-Plan')

    # Profildaten aus session_state
    weight = st.session_state.get('gewicht')
    age = st.session_state.get('alter')
    height = st.session_state.get('groesse')
    gender_str = st.session_state.get('geschlecht')
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

    # FIT-Datei Kennzahlen
    st.subheader('1️⃣ FIT-Datei Kennzahlen')
    c1, c2, c3 = st.columns(3)
    c1.metric('Distanz (km)', f"{data['total_distance_m']/1000:.2f}")
    c2.metric('Dauer (min)', f"{duration_min:.1f}")
    c3.metric('Ø-Herzfrequenz (bpm)', f"{data['avg_hr']:.0f}" if data['avg_hr'] else 'n/a')

    c4, c5, c6 = st.columns(3)
    c4.metric('Max-Herzfrequenz (bpm)', f"{data['max_hr']:.0f}" if data['max_hr'] else 'n/a')
    c5.metric('Gewicht (kg)', f"{weight:.1f}" if weight else 'n/a')
    c6.metric('Alter (Jahre)', f"{age}" if age else 'n/a')
    st.metric('Körpergröße (cm)', f"{height}" if height else 'n/a')

    # Berechnungen
    actual_cal = calc_calories_keytel(data['avg_hr'], weight, age, gender, duration_min)
    actual_fluid = calc_fluid_loss(actual_cal, duration_h)

    # Vor-Workout-Plan Werte
    stats_for_vor = {
        'avg_hr': data['avg_hr'],
        'weight_kg': weight,
        'age': age,
        'gender': gender,
        'total_time_s': duration_s
    }
    try:
        planned_cal = vor.calculate_vor_calories(stats_for_vor)
    except Exception:
        planned_cal = None
    planned_fluid = st.session_state.get('fluessigkeit')

    # Visualisierung mit Donut-Charts
    st.subheader('2️⃣ Vergleich: Gemessen vs. Geplant')

    # Kalorienvergleich als Donut
    labels_cal = ['Gemessen', 'Geplant']
    vals_cal = [actual_cal or 0, planned_cal or 0]
    fig1, ax1 = plt.subplots()
    ax1.pie(vals_cal, labels=labels_cal, autopct='%1.1f%%', startangle=90, wedgeprops={'width': 0.4})
    ax1.set(aspect='equal')
    st.pyplot(fig1)

    # Flüssigkeitsvergleich als Donut
    labels_fl = ['Verloren', 'Empfohlen']
    vals_fl = [actual_fluid or 0, planned_fluid or 0]
    fig2, ax2 = plt.subplots()
    ax2.pie(vals_fl, labels=labels_fl, autopct='%1.1f%%', startangle=90, wedgeprops={'width': 0.4})
    ax2.set(aspect='equal')
    st.pyplot(fig2)

    st.markdown('---')
    st.info('Visualisierung: Donut-Charts für Kalorien & Flüssigkeit')

if __name__ == '__main__':
    main()
