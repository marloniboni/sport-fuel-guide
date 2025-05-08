import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
import joblib
import os
from math import sqrt


# 1. CSV-Datei einlesen (wegen Kommas in Activity manuell)
with open("sport-fuel-ml/exercise_dataset.csv", encoding="utf-8") as f:
    lines = f.readlines()


data = []
for line in lines[1:]:
    parts = line.strip().split(',')
    if len(parts) >= 6:
        activity = ",".join(parts[:-5]).strip()
        try:
            vals = list(map(float, parts[-5:]))
            data.append([activity] + vals)
        except ValueError:
            continue

raw = pd.DataFrame(data, columns=["Activity", "kcal_130lb", "kcal_155lb", "kcal_180lb", "kcal_205lb", "kcal_per_kg"])


# 2. Synthetische Trainingsdaten erzeugen (mit Aktivitätsfaktor)
activities = raw["Activity"]
kcal_per_kg = raw["kcal_per_kg"]


gewicht_list = list(range(55, 96, 10))   # z. B. 55, 65, 75, 85, 95 kg
dauer_list = list(range(30, 151, 20))    # z. B. 30, 50, ..., 150 Min


records = []
for act, kcal_kg in zip(activities, kcal_per_kg):
    for g in gewicht_list:
        for d in dauer_list:
            # Aktivitätsbasierter Verstärkungsfaktor
            faktor = 1.0
            if act == "Running":
                faktor = 6.0
            elif "Cycling" in act:
                faktor = 4.5
            elif "Swimming" in act:
                faktor = 5.0

            kcal = d * g * kcal_kg / 60 * faktor
            records.append({
                "Activity": act,
                "Gewicht": g,
                "Dauer": d,
                "kcal": kcal
            })



df = pd.DataFrame(records)


# 3. Features und Ziel
X = df[["Activity", "Gewicht", "Dauer"]]
y = df["kcal"]


# 4. Pipeline mit reduziertem Random Forest
preprocessor = ColumnTransformer([
    ("activity", OneHotEncoder(handle_unknown="ignore"), ["Activity"])
], remainder="passthrough")


model = make_pipeline(preprocessor, RandomForestRegressor(n_estimators=20, random_state=42))


# 5. Train/Test-Split und Training
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
model.fit(X_train, y_train)


# 6. Evaluation
preds = model.predict(X_test)
rmse = sqrt(mean_squared_error(y_test, preds))
print(f"✅ Modell fertig – RMSE: {rmse:.2f} kcal")


# 7. Modell speichern mit Kompression
os.makedirs("models", exist_ok=True)
joblib.dump(model, "models/calorie_predictor.pkl", compress=3)
print("💾 Modell gespeichert in models/calorie_predictor.pkl (komprimiert)")


