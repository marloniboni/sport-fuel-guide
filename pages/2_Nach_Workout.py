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
# Nach-Workout-Auswertung: FIT-Daten, Berechnungen & Vergleiche
# --------------------------------------------

# VO₂-Plan aus Pre-Workout-Seite importieren (falls benötigt)
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
    dist = session.get('total_distance', df.get('distance', pd.Series()).max())
    t_s = session.get('total_timer_time', (df['timestamp'].max() - df['timestamp'].min()).total_seconds())
    avg_hr = df['heart_rate'].mean() if 'heart_rate' in df else None
    max_hr = df['heart_rate'].max() if 'heart_rate' in df else None
    return {'df': df, 'distance_m': dist, 'time_s': t_s, 'avg_hr': avg_hr, 'max_hr': max_hr}


def calc_calories_keytel(avg_hr, weight, age, gender, duration_min):
    if None in (avg_hr, weight, age, gender): return None
    if gender == 1:
        a,b,c,d = 0.6309,0.1988,0.2017,-55.0969
    else:
        a,b,c,d = 0.4472,0.1263,0.0740,-20.4022
    e_dot = (a*avg_hr + b*weight + c*age + d)/4.184
    return e_dot * duration_min


def calc_fluid_loss(calories, hours):
    if calories is None or hours<=0: return None
    lph = 1.38e-3 * (calories/hours)
    return lph * hours


def main():
    st.title('Nach-Workout-Analyse')
    st.write('Nur einmal .fit hochladen – dann Vo2-Plan vergleichen')

    # Profil aus Session oder Eingabe
    weight = st.session_state.get('gewicht') or st.number_input('Gewicht (kg)',40,150,70)
    age    = st.session_state.get('alter') or st.number_input('Alter (Jahre)',12,80,25)
    height= st.session_state.get('groesse') or st.number_input('Größe (cm)',140,210,175)
    gender= 1 if st.session_state.get('geschlecht','Männlich')=='Männlich' else 2

    uploaded = st.file_uploader('Deine .fit-Datei auswählen',type='fit')
    if not uploaded:
        st.info('Bitte .fit zuerst hochladen')
        return

    data = parse_fit(uploaded)
    if not data: return
    df = data['df']; t_min=data['time_s']/60; t_h=data['time_s']/3600

    # Metrics
    st.subheader('FIT-Kennzahlen')
    cols=st.columns(3)
    cols[0].metric('Distanz (km)',f"{data['distance_m']/1000:.2f}")
    cols[1].metric('Dauer (min)',f"{t_min:.1f}")
    cols[2].metric('Ø-Herzfr. (bpm)',f"{data['avg_hr']:.0f}" if data['avg_hr'] else 'n/a')

    st.subheader('Berechnungen')
    actual_cal = calc_calories_keytel(data['avg_hr'],weight,age,gender,t_min)
    actual_fluid = calc_fluid_loss(actual_cal,t_h)

    # Geplanter Kalorienwert direkt aus Pre-Workout (SessionState) oder VO2-Fkt
    planned_cal = st.session_state.get('planned_calories')
    if planned_cal is None:
        stats={
            'avg_hr':data['avg_hr'],'weight_kg':weight,'age':age,'gender':gender,'total_time_s':data['time_s']
        }
        planned_cal = vor.calculate_vor_calories(stats)
    planned_fluid = st.session_state.get('fluessigkeit')

    # Unterschied berechnen
    diff_cal = (actual_cal or 0) - (planned_cal or 0)
    diff_fl  = (actual_fluid or 0) - (planned_fluid or 0)

    # Side-by-side Donuts
    st.subheader('Vergleich: Ist vs. Plan')
    fig, axes = plt.subplots(1,2,figsize=(8,4))
    # Kalorien Donut
    axes[0].pie([actual_cal or 0, planned_cal or 0], labels=['Ist','Plan'],
                autopct='%1.0f kcal', startangle=90, wedgeprops={'width':0.4})
    axes[0].set_title(f'Kalorien Δ {diff_cal:+.0f} kcal')
    # Flüssigkeit Donut
    axes[1].pie([actual_fluid or 0, planned_fluid or 0], labels=['Ist','Empf.'],
                autopct='%1.2f L', startangle=90, wedgeprops={'width':0.4})
    axes[1].set_title(f'Flüssigkeit Δ {diff_fl:+.2f} L')
    for ax in axes: ax.set(aspect='equal')
    st.pyplot(fig)

    st.markdown('---')
    st.info('Einmal hochladen, Donuts zeigen Ist vs. Plan und Differenz')

if __name__=='__main__': main()
