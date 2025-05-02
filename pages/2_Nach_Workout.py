# pages/2_Nach_Workout.py
# -*- coding: utf-8 -*-

import streamlit as st
import pandas as pd
import numpy as np
from fitparse import FitFile
import importlib.util
import os

# --- VO2-Modul laden (Dateiname ohne Leerzeichen!) ---
spec = importlib.util.spec_from_file_location(
    "vor_module", os.path.join("pages", "1_Vor_Workout.py")
)
vor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vor)


def parse_fit(fitfile):
    """
    Parst das FIT-File und liefert:
      - df: DataFrame aller Records
      - Session-Daten (Distanz, Zeit, Speed, Kalorien, Auf-/Abstieg)
      - User-Profil (Gewicht, HF)
    """
    fit = FitFile(fitfile)
    records, session, user_profile = [], {}, {}

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
        st.error("Keine GPS-/Sensor-Daten im FIT-File gefunden.")
        return {}

    df = pd.DataFrame(records)

    # Basis
    total_distance = session.get("total_distance", df["distance"].max())
    total_time = session.get(
        "total_timer_time",
        (df["timestamp"].max() - df["timestamp"].min()).total_seconds()
    )

    # Speed (optional)
    if "speed" in df:
        avg_speed = session.get("avg_speed", df["speed"].mean())
        max_speed = session.get("max_speed", df["speed"].max())
    else:
        avg_speed = max_speed = None

    # Herzfrequenz (optional)
    if "heart_rate" in df:
        avg_hr = session.get("avg_heart_rate", df["heart_rate"].mean())
        max_hr = session.get("max_heart_rate", df["heart_rate"].max())
    else:
        avg_hr = max_hr = None

    # Auf-/Abstieg (optional)
    alt_col = "enhanced_altitude" if "enhanced_altitude" in df else \
              "altitude" if "altitude" in df else None
    ascent = descent = None
    if alt_col:
        diff = np.diff(df[alt_col].to_numpy())
        ascent = diff[diff > 0].sum()
        descent = -diff[diff < 0].sum()

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
    st.write("Lade deine .fit-Datei hoch und ergänze Gewichtswerte, um Kalorien und Flüssigkeits-verlust zu sehen.")

    uploaded = st.file_uploader("Deine .fit-Datei auswählen", type="fit")
    if not uploaded:
        st.info("Bitte zuerst eine .fit-Datei hochladen.")
        return

    data = parse_fit(uploaded)
    if not data:
        return
    df = data["df"]

    # 1) Basis-Metriken
    st.subheader("1. Basis-Metriken")
    c1, c2, c3 = st.columns(3)
    c1.metric("Distanz (km)", f"{data['total_distance_m']/1000:.2f}")
    c2.metric("Dauer (h)", f"{data['total_time_s']/3600:.2f}")
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
    st.subheader("2. Weitere Kennzahlen")
    extras = st.columns(2)
    if data["avg_hr"] is not None:
        extras[0].metric("Ø-Herzfrequenz (bpm)", f"{data['avg_hr']:.0f}")
        extras[1].metric("Max. Herzfrequenz (bpm)", f"{data['max_hr']:.0f}")
    if "cadence" in df:
        extras[0].metric("Ø-Kadenz (rpm)", f"{df['cadence'].mean():.0f}")
        extras[1].metric("Max. Kadenz (rpm)", f"{df['cadence'].max():.0f}")
    if "power" in df:
        extras[0].metric("Ø-Power (W)", f"{df['power'].mean():.0f}")
        extras[1].metric("Max. Power (W)", f"{df['power'].max():.0f}")
    if "temperature" in df:
        extras[0].metric("Ø-Temperatur (°C)", f"{df['temperature'].mean():.1f}")

    # 3) Kalorienverbrauch
    st.subheader("3. Kalorienverbrauch")
    try:
        calories_vor = vor.calculate_vor_calories(data)
    except Exception as e:
        st.error(f"Fehler bei VO₂-Berechnung: {e}")
        calories_vor = None

    colA, colB = st.columns(2)
    colA.metric("FIT-File gemeldet", data["fit_calories"] or "n/a")
    colB.metric("VO₂-Formel berechnet", f"{calories_vor:.0f}" if calories_vor else "n/a")
    if data["fit_calories"] and calories_vor:
        diff = calories_vor - data["fit_calories"]
        sign = "+" if diff >= 0 else ""
        st.write(f"Unterschied: {sign}{diff:.0f} kcal")

    # 4) Flüssigkeitsverlust
    st.subheader("4. Flüssigkeitsverlust")
    w_pre = st.number_input(
        "Gewicht vor dem Training (kg)",
        value=float(data.get("weight_kg") or 70.0)
    )
    w_post = st.number_input(
        "Gewicht nach dem Training (kg)",
        value=w_pre - 0.5
    )
    loss = w_pre - w_post
    st.metric("Verlorene Flüssigkeit (L)", f"{loss:.2f}")

    st.markdown("---")
    st.info("Weitere Analysen (HF-Zonen, Leistungskurve etc.) folgen in künftigen Updates.")


if __name__ == "__main__":
    main()
