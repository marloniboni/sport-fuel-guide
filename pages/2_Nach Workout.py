# main.py
import streamlit as st
import pandas as pd
from fitparse import FitFile
import importlib.util
import os

# Dynamically import the 1_Vor_Workout module (filename starts with a digit)
spec = importlib.util.spec_from_file_location(
    "vor_module", os.path.join("pages", "1_Vor_Workout.py")
)
vor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vor)


def parse_fit(fitfile) -> dict:
    """
    Parse the uploaded .fit file and extract key ride metrics.
    Returns a dict with distance (m), duration (s), avg/max speed (m/s),
    avg/max heart rate (bpm), and (if available) FIT's own calorie tally.
    """
    fit = FitFile(fitfile)
    # Containers
    records = []
    session_data = {}
    user_profile = {}

    # Iterate over messages
    for msg in fit.get_messages():
        name = msg.name
        if name == "record":
            rec = {f.name: f.value for f in msg.fields}
            records.append(rec)
        elif name == "session":
            for f in msg.fields:
                session_data[f.name] = f.value
        elif name == "user_profile":
            for f in msg.fields:
                user_profile[f.name] = f.value

    # Build DataFrame of records for easy stats
    df = pd.DataFrame(records)
    stats = {
        "total_distance_m": session_data.get("total_distance", df["distance"].max()),
        "total_time_s": session_data.get("total_timer_time", (df["timestamp"].max() - df["timestamp"].min()).total_seconds()),
        "avg_speed_m_s": session_data.get("avg_speed", df["speed"].mean()),
        "max_speed_m_s": session_data.get("max_speed", df["speed"].max()),
        "avg_hr": df["heart_rate"].mean() if "heart_rate" in df else None,
        "max_hr": df["heart_rate"].max() if "heart_rate" in df else None,
        "fit_calories": session_data.get("total_calories", None),
        "weight_kg": user_profile.get("weight", None),
    }
    return stats


def main():
    st.title("🚴‍♀️ Ride Analyzer")
    st.write("Upload your .fit file to see your ride metrics and calorie comparison.")

    uploaded = st.file_uploader("Choose a .fit file", type="fit")
    if uploaded is None:
        st.info("Waiting for .fit file upload …")
        return

    # Parse the file
    stats = parse_fit(uploaded)
    st.subheader("Your ride summary")
    st.metric("Distance (km)", f"{stats['total_distance_m']/1000:.2f}")
    st.metric("Duration", f"{stats['total_time_s']/3600:.2f} h")
    st.metric("Avg Speed (km/h)", f"{stats['avg_speed_m_s']*3.6:.1f}")
    st.metric("Max Speed (km/h)", f"{stats['max_speed_m_s']*3.6:.1f}")
    if stats["avg_hr"]:
        st.metric("Avg Heart Rate (bpm)", f"{stats['avg_hr']:.0f}")
        st.metric("Max Heart Rate (bpm)", f"{stats['max_hr']:.0f}")

    # Calculate calories via your VO2‐based formula
    vor_cal = vor.calculate_vor_calories(stats)
    st.subheader("Calories burned")
    col1, col2 = st.columns(2)
    col1.metric("FIT-file reported", stats["fit_calories"] or "n/a")
    col2.metric("Via your VO₂ formula", f"{vor_cal:.0f}")

    # Comparison
    if stats["fit_calories"] is not None:
        diff = vor_cal - stats["fit_calories"]
        sign = "+" if diff >= 0 else ""
        st.write(f"Difference: {sign}{diff:.0f} kcal")

    # Further breakdown based on heart‐rate zones, etc.
    st.write("---")
    st.write("⚙️ _Advanced metrics coming soon…_")
    # You can extend here: parse df zones, power data, elevation, etc.


if __name__ == "__main__":
    main()
