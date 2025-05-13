#Module und Libraries -> requirements.txt
import pandas as pd
import os
import joblib
from math import sqrt
#Trainingsmodule für ML Learning Modelle. Quelle: scikit learn, https://scikit-learn.org/stable/#
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error

#CSV einlesen und verarbeiten. CSV-Datei von Fernando Fernandez, kaggle, https://www.kaggle.com/datasets/fmendes/fmendesdat263xdemos
with open("sport-fuel-ml/exercise_dataset.csv", encoding="utf-8") as f:    #Lesen der Datei Zeile für Zeile und Trennung der Daten durch Komma.
    lines = f.readlines()

data = []
for line in lines[1:]:    #Erste Zeile nicht relevant, danach Trennung jeder Zeile in Aktivität + Werte
    parts = line.strip().split(',')
    if len(parts) > 6:
        activity = ",".join(parts[:-5]).strip()       #Fasst die Teile vor diesen 5 Zahlen zu einem String zusammen
        try:
            vals = list(map(float, parts[-5:]))
            data.append([activity] + vals)
        except ValueError:                            #Fahre auch bei Fehlern fort
            continue
#Erstellt DataFrame aus den verarbeiteten Daten
raw = pd.DataFrame(data, columns=["Activity", "kcal_130lb", "kcal_155lb", "kcal_180lb", "kcal_205lb", "kcal_per_kg"])

#Trainingsdaten erzeugen
activities = raw["Activity"]
kcal_per_kg = raw["kcal_per_kg"]

gewicht_list = list(range(55, 96, 5))  #Simulation von Sporteinheiten mit unterschiedlichen Gewichten
dauer_list = list(range(30, 151, 20))  #Simutation von Sporteinheiten mit unterschiedlichen Dauern

records = []               #Jetzt wird jede Aktivität mit jedem Gewicht & jeder Dauer kombiniert
for act, kcal_kg in zip(activities, kcal_per_kg):
    for g in gewicht_list:
        for d in dauer_list:
            # Aktivitätsbasierter Verstärkungsfaktor wurde definiert um genauere Ergebnisse am Schluss zu erhalten mit Hilfe von OpenAI. (2025). ChatGPT 4o (Version vom 01.05.2025) [Large language model]. https://chat.openai.com/chat.
            if "Running" in act:
                faktor = 4.3
                distanz = d * 0.1  # grob 10 km/h
            elif "Cycling" in act:
                faktor = 4.5
                distanz = d * 0.25  # grob 15 km/h
            elif "Swimming" in act:
                faktor = 10.0
                distanz = d * 0.05  # grob 3 km/h
            else:
                faktor = 1.0
                distanz = d * 0.1

            kcal = d * g * kcal_kg / 60 * faktor #Berechnung des geschätzten Kalorienverbrauchs
            records.append({
                "Activity": act,
                "Gewicht": g,
                "Dauer": d,
                "Distanz": distanz,
                "kcal": kcal
            })

# Modell trainieren
df = pd.DataFrame(records)
X = df[["Activity", "Gewicht", "Dauer", "Distanz"]] #Eingabedaten vorbereiten
y = df["kcal"]                  #Zielwert vorbereiten

#Verarbeitung der Eingabedaten Quelle: scikit learn, https://scikit-learn.org/stable/#
preprocessor = ColumnTransformer([
    ("activity", OneHotEncoder(handle_unknown="ignore"), ["Activity"])
], remainder="passthrough")

#Nun werden Verarbeitung und das Modell kombiniert
model = make_pipeline(preprocessor, RandomForestRegressor(n_estimators=100, random_state=42))
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
model.fit(X_train, y_train)    #trainiert das Modell

#Modell evaluieren
preds = model.predict(X_test)
rmse = sqrt(mean_squared_error(y_test, preds))    #Bewertet das Modell mit RMSE
print(f"Modell finito du bisch eh geile Siech = RMSE: {rmse:.2f} kcal")    #Stellt dar, das das Modell fertig ist

#Modell speichern und .pkl Datei erstellen sowie komprimieren aufgrund grosser Datenmenge. Mit Hilfe von OpenAI. (2025). ChatGPT 4o (Version vom 01.05.2025) [Large language model]. https://chat.openai.com/chat.
os.makedirs("models", exist_ok=True)
joblib.dump(model, "models/calorie_predictor.pkl", compress=3)
print("🗃️ Modell gespeichert in models/calorie_predictor.pkl (komprimiert)")
