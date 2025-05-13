import streamlit as st       #Importiert Streamlit zur Erstellung einer Web-App (Grundvoraussetzung)
import requests              #Wird für HTTP-Anfragen verwendet
import urllib                #Wird zur URL-Verarbeitung verwendet


# Seiteneinstellungen also Titel, Icon, Layoutbreite -> für eine ästhetische Ansicht
st.set_page_config(
    page_title="Sport Fuel Guide",
    page_icon=None,
    layout="wide"
)

st.title("Sport Fuel Guide")                                                                            #Titel der Home-Seite
st.info("Diese App hilft dir bei der Planung deiner Trainings- und Wettkampfernährung.")                #Infobox unterhalb des Titels

with st.expander("Gib deine Daten ein"):                                        #Aufklappbarer Eingabereich
    col1, col2 = st.columns(2)                                                  #Bildung von 2 Spalten: wobei 1. Spalte mit Gewicht und Alter per Slider bestimmt werden kann und Spalte 2 
    with col1:                                                                  #Wobei 1. Spalte mit Gewicht und Alter per Slider bestimmt werden kann
        gewicht    = st.slider("Gewicht (kg)", 40, 150, 70)                     #Spalte 2 Grösse per Slider und Geschlecht mit Auswahlbox gewählt werden kann
        alter      = st.slider("Alter (Jahre)", 12, 80, 25)
    with col2:
        groesse    = st.slider("Körpergröße (cm)", 140, 210, 175)
        geschlecht = st.selectbox("Geschlecht", ["Männlich", "Weiblich"])
        
# Grundumsatz & Flüssigkeitsbedarf Berechnungen
if geschlecht == "Männlich":
    grundumsatz = 66.47 + (13.7 * gewicht) + (5.0 * groesse) - (6.8 * alter)    #Grundumsatz Kcal abhängig von Geschlecht, Gewicht, Alter und Grösse
else:                                                                           #Berechnung nach Harris-Benedict Formel. Quelle: Wikipedia, https://de.wikipedia.org/wiki/Grundumsatz
    grundumsatz = 655.1 + (9.6 * gewicht) + (1.8 * groesse) - (4.7 * alter)

fluessigkeit = gewicht * 0.035                                                  #Berechnung Flüssigkeitsbedarf. Quelle: Migros, https://impuls.migros.ch/de/ernaehrung/nahrungsmittel/getraenke/wasser-trinken

#Speichern der Werte im Session-State, damit sie anschliessend wieder abgerufen werden können.
st.session_state['gewicht']    = gewicht
st.session_state['groesse']    = groesse
st.session_state['alter']      = alter
st.session_state['geschlecht'] = geschlecht
st.session_state['grundumsatz'] = grundumsatz
st.session_state['fluessigkeit'] = fluessigkeit

#Abschnittstrennung und anschliessendes Anzeigen des Grundumsatzes und Flüssigkeitsbedarf
st.markdown("---")
st.success("Deine berechneten Werte")
r1, r2 = st.columns(2)
r1.metric("Grundumsatz (kcal/Tag)", f"{int(grundumsatz)}")
r2.metric("Flüssigkeitsbedarf (L/Tag)", f"{fluessigkeit:.2f} L")

#Zusätzliche Darstellung von Grundumsatz und Flüssigkeitsbedarf
st.markdown("<p style='font-weight:bold; font-size:1.2rem; margin-top:-0.5rem;'>Mit deinen Zahlen hört das Rätselraten auf </p>", unsafe_allow_html=True)
st.write(f"**Grundumsatz**: ca. `{int(grundumsatz)} kcal` pro Tag")
st.write(f"**Täglicher Flüssigkeitsbedarf**: ca. `{fluessigkeit:.2f} Liter`")

#Abspeichern von Gewicht, Grundumsatz und Flüssigkeitsbedarf in Session-State, zur Weiterverwendung auf anderen Seiten
st.session_state.gewicht = gewicht
st.session_state.grundumsatz = grundumsatz
st.session_state.fluessigkeit = fluessigkeit

# Navigation zur Vorbereitungsseite (Vor Workout)
st.markdown("---")
st.markdown("### Hast du ein Workout geplant?")

if left.button("Zur Vorbereitungsseite"): #Button zur Navigation zur Vor Workout Seite
    # Session-State updaten (wie gehabt)
    st.session_state.update({                #Speicherung der Daten in Session-Satate sicherstellen.
        "gewicht":      gewicht,
        "groesse":      groesse,
        "alter":        alter,
        "geschlecht":   geschlecht,
        "grundumsatz":  grundumsatz,
        "fluessigkeit": fluessigkeit
    })
    st.switch_page("pages/1_Vor_Workout.py")    #Link wechselt zur Seite "Vor-Workout.py"
