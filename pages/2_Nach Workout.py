# pages/2_Nach_Workout.py

import streamlit as st
import pandas as pd
from fitparse import FitFile
import importlib.util
import os

# Dynamisch das VO₂-Modul importieren
spec = importlib.util.spec_from_file_location(
    "vor_module", os.path.join("pages", "1_Vor_Workout.py")
)
vor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vor)


def parse_fit(fitfile) -> dict:
    """
    Parst die .fit-Datei und extrahiert zentrale Metriken:
      - Distanz (m)
      - Dauer (s)
      - Durchschnitts-/Max-Geschwindigkeit (m/s)
      - Durchschnitts-/Max-Herzfrequenz (bpm)
      - vom FIT-File geloggte Kalorien
      - Gewicht aus User-Profil (kg)
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

    df = pd.DataFrame(records)
    total_dist = session.get("total_distance", df["distance"].max())
    total_time = session.get("total_timer_time",
                             (df["timestamp"].max() - df["timestamp"].min()).total_seconds())
    avg_speed = session.get("avg_speed", df["speed"].mean())
    max_speed = session.get("max_speed", df["speed"].max())
    avg_hr = df["heart_rate"].mean() if "heart_rate" in df else None
    max_hr = df["heart_rate"].max() if "heart_rate" in df else None

    return {
        "total_distance_m": total_dist,
        "total_time_s": total_time,
        "avg_speed_m_s": avg_speed,
        "max_speed_m_s": max_speed,
        "avg_hr": avg_hr,
        "max_hr": max_hr,
        "fit_calories": session.get("total_calories", None),
        "weight_kg": user_profile.get("weight", None),
    }


def main():
    st.title("🏁 Nach Workout Auswertung")
    st.write("Lade deine .fit-Datei hoch, um dein Training auszuwerten.")

    uploaded = st.file_uploader("Deine .fit-Datei", type="fit")
    if not uploaded:
        st.info("Bitte lade zuerst eine .fit-Datei hoch.")
        return

    stats = parse_fit(uploaded)

    st.subheader("🚴‍♂️ Trainingsdaten")
    st.metric("Entfernung (km)", f"{stats['total_distance_m']/1000:.2f}")
    st.metric("Dauer (h)", f"{stats['total_time_s']/3600:.2f}")
    st.metric("Durchschn. Speed (km/h)", f"{stats['avg_speed_m_s']*3.6:.1f}")
    st.metric("Max. Speed (km/h)", f"{stats['max_speed_m_s']*3.6:.1f}")

    if stats["avg_hr"] is not None:
        st.metric("Durchschn. HF (bpm)", f"{stats['avg_hr']:.0f}")
        st.metric("Max. HF (bpm)", f"{stats['max_hr']:.0f}")

    # VO₂-basierte Kalorienberechnung
    calories_vor = vor.calculate_vor_calories(stats)

    st.subheader("🔥 Kalorienverbrauch")
    c1, c2 = st.columns(2)
    c1.metric("FIT-file gemeldet", stats["fit_calories"] or "n/a")
    c2.metric("VO₂-Formel", f"{calories_vor:.0f}")

    if stats["fit_calories"] is not None:
        diff = calories_vor - stats["fit_calories"]
        sign = "+" if diff >= 0 else ""
        st.write(f"Unterschied: {sign}{diff:.0f} kcal")

    st.markdown("---")
    st.write(
        "Hier kannst du später noch zusätzliche Auswertungen hinzufügen, z.B. Herzfrequenz-Zonen, Leistungsdaten, Höhenmeter usw."
    )


if __name__ == "__main__":
    main()
