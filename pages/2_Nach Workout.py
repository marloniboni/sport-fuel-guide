# pages/2_Nach_Workout.py

import streamlit as st
import pandas as pd
import numpy as np
from fitparse import FitFile
import importlib.util
import os

# --- VO2-Modul importieren ---
spec = importlib.util.spec_from_file_location(
    "vor_module", os.path.join("pages", "1_Vor_Workout.py")
)
vor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vor)


def parse_fit(fitfile):
    """
    Parst die .fit-Datei und extrahiert:
      - Records-DataFrame (alle Datenpunkte)
      - Session-Metriken (Distanz, Zeit, Speed, Kalorien, Aufstieg, Abstieg)
      - User-Profil (Gewicht)
    """
    fit = FitFile(fitfile)
    records = []
    session = {}
    user_profile = {}

    for msg in fit.get_messages():
        if msg.name == "record":
            rec = {f.name: f.value for f in msg.fields}
            records.append(rec)
        elif msg.name == "session":
            for f in msg.fields:
                session[f.name] = f.value
        elif msg.name == "user_profile":
            for f in msg.fields:
                user_profile[f.name] = f.value

    df = pd.DataFrame(records)

    # Basis-Metriken
    total_dist = session.get("total_distance", df["distance"].max())
    total_time = session.get(
        "total_timer_time",
        (df["timestamp"].max() - df["timestamp"].min()).total_seconds()
    )
    avg_speed = session.get("avg_speed", df["speed"].mean())
    max_speed = session.get("max_speed", df["speed"].max())

    # Höhenmeter (falls vorhanden)
    if "enhanced_altitude" in df:
        alt = df["enhanced_altitude"].to_numpy()
    elif "altitude" in df:
        alt = df["altitude"].to_numpy()
    else:
        alt = None

    ascent = descent = None
    if alt is not None:
        diffs = np.diff(alt)
        ascent = diffs[diffs > 0].sum()
        descent = -diffs[diffs < 0].sum()

    return {
        "df": df,
        "total_distance_m": total_dist,
        "total_time_s": total_time,
        "avg_speed_m_s": avg_speed,
        "max_speed_m_s": max_speed,
        "fit_calories": session.get("total_calories"),
        "weight_kg": user_profile.get("weight"),
        "ascent_m": ascent,
        "descent_m": descent
    }


def main():
    st.title("🏁 Nach-Workout Auswertung")
    st.write(
        "Upload: `.fit`-Datei → Auswertung deiner tatsächlichen " 
        "Leistungs- und Gesundheits-Kennzahlen"
    )

    uploaded = st.file_uploader("Wähle deine .fit-Datei", type="fit")
    if not uploaded:
        st.info("Bitte lade eine .fit-Datei hoch, um zu starten.")
        return

    data = parse_fit(uploaded)
    df = data["df"]

    # 1) Basis-Kennzahlen
    st.subheader("1. Basis-Metriken")
    c1, c2, c3 = st.columns(3)
    c1.metric("Distanz (km)", f"{data['total_distance_m']/1000:.2f}")
    c2.metric("Dauer (h)", f"{data['total_time_s']/3600:.2f}")
    c3.metric("Ø-Speed (km/h)", f"{data['avg_speed_m_s']*3.6:.1f}")

    c4, c5, c6 = st.columns(3)
    c4.metric("Max-Speed (km/h)", f"{data['max_speed_m_s']*3.6:.1f}")
    if data["ascent_m"]
