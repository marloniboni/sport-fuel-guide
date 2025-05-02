# pages/2_Nach_Workout.py
# -*- coding: utf-8 -*-

import streamlit as st
import pandas as pd
import numpy as np
from fitparse import FitFile
import importlib.util
import os

# VO2-Modul aus 1_Vor_Workout.py laden
spec = importlib.util.spec_from_file_location(
    "vor_module", os.path.join("pages", "1_Vor_Workout.py")
)
vor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vor)

def parse_fit(fitfile):
    """
    Parst die FIT-Datei und gibt zurück:
      - df: DataFrame aller Records
      - Session-Metriken (Distanz, Zeit, Speed, Kalorien, Auf-/Abstieg)
      - User-Profil (Gewicht, HF-Metriken)
    """
    fit = FitFile(fitfile)
    records = []
    session = {}
    user_profile = {}

    for msg in fit.get_messages():
        if msg.name == "record":
            records.append({f.name: f.value for f in msg.fields})
        elif msg.name == "session":
            for f in msg.fields:
                session[f.name] = f.value
        elif msg.name == "user_profile":
            for f in msg.fields:
                user_profile[f.name] = f.value

    if not records:
        st.error("Keine Daten im FIT-File gefunden.")
        return {}

    df = pd.DataFrame(records)

    # 1) Basis-Metriken
    total_distance = session.get("total_distance", df["distance"].max())
    total_time = session.get(
        "total_timer_time",
        (df["timestamp"].max() - df["timestamp"].min()).total_seconds()
    )

    # Speed nur, wenn im DataFrame vorhanden
    if "speed" in df.columns:
        avg_speed = session.get("avg_speed", df["speed"].mean())
        max_speed = session.get("max_speed", df["speed"].max())
    else:
        avg_speed = None
        max_speed = None

    # Herzfrequenz
    if "heart_rate" in df.columns:
        avg_hr = session.get("avg_heart_rate", df["heart_rate"].mean())
        max_hr = session.get("max_heart_rate", df["heart_rate"].max())
    else:
        avg_hr = None
        max_hr = None

    # Auf- und Abstieg
    alt_col = None
    if "enhanced_altitude" in df.columns:
        alt_col = "enhanced_altitude"
    elif "altitude" in df.columns:
        alt_col = "altitude"

    ascent = descent = None
    if alt_col:
        alt = df[alt_col].to_numpy()
        diffs = np.diff(alt)
        ascent = diffs[diffs > 0].sum()
        descent = -diffs[diffs < 0].sum()

    return {
        "df": df,
        "total_distance_m": total_distance,
        "total_time_s": total_time,
        "avg_speed_m_s": avg_speed,
        "max_speed_m_s": max_speed,
        "avg_hr": avg_hr,
        "max_hr": max_hr,
        "fit_calories": session.get("total_calories"),
        "weight_kg": user_profile.get("weight"),
        "ascent_m": ascent,
        "descent_m": descent
    }

def main():
    st.title("Nach-Workout Auswertung")
    st.write("Lade deine .fit-Datei hoch, um eine detaillierte Nach-Workout-Analyse zu erhalten.")

    uploaded_file = st.file_uploader("Deine .fit-Datei auswählen", type="fit")
    if uploaded_file is None:
        st.info("Bitte lade eine .fit-Datei hoch, um zu starten.")
        return

    data = parse_fit(uploaded_file)
    if not data:
        return
    df = data["df"]

    # 1) Basis-Metriken
    st.subheader("1. Basis-Metriken")
    c1, c2, c3 = st.columns(3)
    c1.metric("Distanz (km)", f"{data['total_distance_m']/1000:.2f}")
    c2.metric("Dauer (h)", f"{data['total_time_s']/3600:.2f}")
    # Speed sicher anzeigen oder "n/a"
    if data["avg_speed_m_s"] is not None:
        c3.metric("Ø-Speed (km/h)", f"{data['avg_speed_m_s']*3.6:.1f}")
    else:
        c3.metric("Ø-Speed (km/h)", "n/a")

    c4, c5, c6 = st.columns(3)
    if data["max_speed_m_s"] is not None:
        c4.metric("Max-Speed (km/h)", f"{data['max_speed_m_s']*3.6:.1f}")
    else:
        c4.metric("Max-Speed (km/h)", "n/a")
    if data["ascent_m"] is not None:
        c5.metric("Aufstieg (m)", f"{data['ascent_m']:.0f}")
        c6.metric("Abstieg (m)", f"{data['descent_m']:.0f}")

    # 2) Zusätzliche Kennzahlen
    st.subheader("2. Zusätzliche Kennzahlen")
    extras = st.columns(2)
    if data["avg_hr"] is not None:
        extras[0].metric("Ø-Herzfrequenz (bpm)", f"{data['avg_hr']:.0f}")
        extras[1].metric("Max. Herzfrequenz (bpm)", f"{data['max_hr']:.0f}")
    if "cadence" in df.columns:
        extras[0].metric("Ø-Kadenz (rpm)", f"{df['cadence'].mean():.0f}")
        extras[1].metric("Max. Kadenz (rpm)", f"{df['cadence'].max():.0f}")
    if "power" in df.columns:
        extras[0].metric("Ø-Power (W)", f"{df['power'].mean():.0f}")
        extras[1].metric("Max. Power (W)", f"{df['power'].max():.0f}")
    if "temperature" in df.columns:
        extras[0].metric("Ø-Temperatur (°C)", f"{df['temperature'].mean():.1f}")

    # 3) Kalorienverbrauch
    st.subheader("3. Kalorienverbrauch")
    calories_vor = vor.calculate_vor_calories(data)
    ca, cb = st.columns(2)
    ca.metric("FIT-File gemeldet", data["fit_calories"] or "n/a")
    cb.metric("VO₂-Formel berechnet", f"{calories_vor:.0f}")
    if data["fit_calories"] is not None:
        diff = calories_vor - data["fit_calories"]
        sign = "+" if diff >= 0 else ""
        st.write(f"Unterschied: {sign}{diff:.0f} kcal")

    # 4) Herzfrequenz-Zonen
    if "heart_rate" in df.columns and data.get("max_hr"):
        st.subheader("4. Herzfrequenz-Zonen")
        max_hr = data["max_hr"]
        bins = [0.6, 0.7, 0.8, 0.9, 1.0]
        labels = [
            "Zone 1 (<60%)", "Zone 2 (60-70%)", "Zone 3 (70-80%)",
            "Zone 4 (80-90%)", "Zone 5 (>90%)"
        ]
        hr = df["heart_rate"]
        zones = {}
        for i, label in enumerate(labels):
            low = 0 if i == 0 else bins[i-1]
            high = bins[i]
            count = hr[(hr > low*max_hr) & (hr <= high*max_hr)].count()
            zones[label] = count
        total = sum(zones.values())
        for label, count in zones.items():
            st.write(f"{label}: {count/total*100:.1f}%")

    st.markdown("---")
    st.info("Weitere Analysen folgen in späteren Updates.")

if __name__ == "__main__":
    main()
