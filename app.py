#now comes the Homepage

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
