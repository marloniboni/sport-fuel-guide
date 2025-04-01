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
st.header("📊 Was wir analysieren")

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

import streamlit as st
import pandas as pd
import numpy as np

# Constants for fluid intake recommendation
FLUID_INTAKE_PER_LITER_LOST = 1.5  # Rehydrate 150% of fluid lost

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

uploaded_file = st.file_uploader("📤 Upload Your Garmin CSV File", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    
    # Display uploaded data
    st.write("📊 **Preview of Uploaded Data:**", df.head())

    # Ensure necessary columns exist
    if "Fluid Loss" in df.columns and "Duration (Minutes)" in df.columns:
        total_fluid_loss = df["Fluid Loss"].sum()
        total_duration = df["Duration (Minutes)"].sum()
        
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
        st.error("❌ CSV file must contain 'Fluid Loss' and 'Duration (Minutes)' columns.")


