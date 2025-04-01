#now comes the Homepage

import streamlit as st

# --- Titel ---
st.title("🏃‍♂️ Triathlon Fuel Guide")
st.subheader("Dein persönlicher Ernährungsassistent für Training und Wettkampf")

# --- Beschreibung ---
st.markdown("""
Unsere App analysiert deine Garmin-Daten, um dir personalisierte Strategien zur Ernährung und Flüssigkeitszufuhr zu bieten –
damit du dein volles Potenzial im Training und Wettkampf ausschöpfen kannst.
""")

# --- Abschnitt: Die drei Schlüsselmetriken ---
st.header("📊 Was wir ANALysieren")

st.image("https://symposium.org/wp-content/uploads/2023/12/Mauro-300x283.jpg", 
         caption="Mauro", 
         use_column_width=True)

st.markdown("### 1️⃣ Kohlenhydratverbrauch (Carbohydrate Burn)")
st.write("Wie viele Kohlenhydrate du während der Aktivität verbrennst – abhängig von Intensität, Dauer und Trainingszone.")

st.markdown("### 2️⃣ Kohlenhydratverfügbarkeit (Carbohydrate Availability)")
st.write("Wie viele Kohlenhydrate du vor und während der Aktivität verfügbar hattest – wichtig für Leistung und Regeneration.")

st.markdown("### 3️⃣ Flüssigkeitsverlust (Fluid Loss)")
st.write("Wie viel Flüssigkeit du basierend auf Temperatur, Anstrengung, Dauer und deinem FTP verlierst.")

# --- Platzhalter: Garmin-Daten Upload ---
st.header("📥 Garmin-Daten hochladen (in Kürze verfügbar)")
st.info("Hier kannst du bald deine Trainingsdaten im .fit oder .csv-Format hochladen.")

# --- Platzhalter: Analyse & Empfehlungen ---
st.header("🧠 Deine persönliche Analyse (in Kürze)")
st.warning("Nach dem Upload bekommst du hier deine individuellen Ernährungsstrategien.")

# --- Footer ---
st.markdown("---")
st.caption("🚀 Triathlon Fuel Guide – smarter trainieren, besser performen.")


def main():
    st.title("GitHub App: Select Age")
    
    # Dropdown selection for age
    age = st.selectbox("Select your age:", list(range(18, 100)))
    
    # Display selected age
    st.write(f"You selected: {age}")
    
    # GitHub connection placeholder
    st.write("This app is connected to GitHub!")

if __name__ == "__main__":
    main()

import pandas as pd
import numpy as np
from fitparse import FitFile
import io

# Constants for fluid intake recommendation
FLUID_INTAKE_PER_LITER_LOST = 1.5  # Rehydrate 150% of fluid lost

def parse_fit_file(uploaded_file):
    """Parse .FIT file and extract necessary data."""
    fitfile = FitFile(uploaded_file)
    data = []
    
    for record in fitfile.get_messages("record"):
        record_data = {}
        for data_field in record:
            record_data[data_field.name] = data_field.value
        data.append(record_data)
    
    return pd.DataFrame(data)

def calculate_hydration_plan(fluid_loss, duration):
    """Calculate a hydration refuel plan based on fluid loss and run duration."""
    if fluid_loss <= 0 or duration <= 0:
        return "No significant fluid loss detected. Stay hydrated!"
    
    # Convert duration to hours
    duration_hours = duration / 60  
    
    # Fluid loss rate per hour
    fluid_loss_per_hour = fluid_loss / duration_hours
    
    # Recommended fluid intake
    total_rehydration = fluid_loss * FLUID_INTAKE_PER_LITER_LOST
    
    # Breakdown hydration strategy per interval (every 15 minutes)
    intervals = np.arange(0, duration + 1, 15)  # Time points in minutes
    fluid_per_interval = total_rehydration / len(intervals)
    
    hydration_schedule = {f"At {int(t)} min": round(fluid_per_interval, 2) for t in intervals}
    
    return {
        "Total Fluid Loss (L)": round(fluid_loss, 2),
        "Fluid Loss per Hour (L)": round(fluid_loss_per_hour, 2),
        "Recommended Fluid Intake (L)": round(total_rehydration, 2),
        "Hydration Strategy": f"Drink {round(total_rehydration / duration_hours, 2)} L per hour during your run.",
        "Hydration Schedule": hydration_schedule
    }

# Streamlit UI
st.title("🏃 Garmin Fluid Refuel Plan")

uploaded_file = st.file_uploader("📤 Upload Your Garmin .FIT File", type=["fit"])

if uploaded_file:
    df = parse_fit_file(uploaded_file)
    
    if not df.empty:
        st.write("📊 **Preview of Uploaded Data:**", df.head())
        
        # Ensure necessary columns exist
        if "fluid_loss" in df.columns and "timestamp" in df.columns:
            total_fluid_loss = df["fluid_loss"].sum()
            total_duration = (df["timestamp"].max() - df["timestamp"].min()).total_seconds() / 60  # Convert seconds to minutes
            
            # Generate hydration plan
            hydration_plan = calculate_hydration_plan(total_fluid_loss, total_duration)
            
            # Display results
            st.subheader("💧 Hydration Plan")
            st.write(f"**Total Fluid Loss:** {hydration_plan['Total Fluid Loss (L)']} L")
            st.write(f"**Fluid Loss Per Hour:** {hydration_plan['Fluid Loss per Hour (L)']} L")
            st.write(f"**Recommended Intake:** {hydration_plan['Recommended Fluid Intake (L)']} L")
            st.write(f"**Strategy:** {hydration_plan['Hydration Strategy']}")
            
            # Display hydration breakdown
            st.subheader("📅 Hydration Schedule")
            for time, amount in hydration_plan["Hydration Schedule"].items():
                st.write(f"{time}: {amount} L")
        
        else:
            st.error("❌ FIT file must contain 'fluid_loss' and 'timestamp' fields.")
    else:
        st.error("❌ Could not parse the FIT file. Please check the format.")
