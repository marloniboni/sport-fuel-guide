import pandas as pd
import os
import joblib
from math import sqrt
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error

# 1. CSV einlesen
with open("sport-fuel-ml/exercise_dataset.csv", encoding="utf-8") as f:
    lines = f.readlines()

data = []
for line in lines[1:]:
    parts = line.strip().split(',')
    if len(parts) > 6:
        activity = ",".join(parts[:-5]).strip()
        try:
            vals = list(map(float, parts[-5:]))
            data.append([activity] + vals)
        except ValueError:
            continue

raw = pd.DataFrame(data, columns=["Activity", "kcal_130lb", "kcal_155lb", "kcal_180lb", "kcal_205lb", "kcal_per_kg"])

# 2. Trainingsdaten erzeugen
activities = raw["Activity"]
kcal_per_kg = raw["kcal_per_kg"]

gewicht_list = list(range(55, 96, 5))  # 55–95 kg
dauer_list = list(range(30, 151, 20))  # 30–150 Min

records = []
for act, kcal_kg in zip(activities, kcal_per_kg):
    for g in gewicht_list:
        for d in dauer_list:
            # Aktivitätsbasierter Verstärkungsfaktor
            if "Running" in act:
                faktor = 6.0
                distanz = d * 0.1  # grob 10 km/h
            elif "Cycling" in act:
                faktor = 4.5
                distanz = d * 0.25  # grob 15 km/h
            elif "Swimming" in act:
                faktor = 5.0
                distanz = d * 0.05  # grob 3 km/h
            else:
                faktor = 1.0
                distanz = d * 0.1

            kcal = d * g * kcal_kg / 60 * faktor
            records.append({
                "Activity": act,
                "Gewicht": g,
                "Dauer": d,
                "Distanz": distanz,
                "kcal": kcal
            })

# 3. Modell trainieren
df = pd.DataFrame(records)
X = df[["Activity", "Gewicht", "Dauer", "Distanz"]]
y = df["kcal"]

preprocessor = ColumnTransformer([
    ("activity", OneHotEncoder(handle_unknown="ignore"), ["Activity"])
], remainder="passthrough")

model = make_pipeline(preprocessor, RandomForestRegressor(n_estimators=100, random_state=42))
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
model.fit(X_train, y_train)

# 4. Modell evaluieren
preds = model.predict(X_test)
rmse = sqrt(mean_squared_error(y_test, preds))
print(f"🎉 Modell fertig = RMSE: {rmse:.2f} kcal")

# 5. Modell speichern
os.makedirs("models", exist_ok=True)
joblib.dump(model, "models/calorie_predictor.pkl", compress=3)
print("🗃️ Modell gespeichert in models/calorie_predictor.pkl (komprimiert)")
