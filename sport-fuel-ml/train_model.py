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

# 1. CSV-Datei laden und vorbereiten
raw = pd.read_csv("exercise_dataset.csv", encoding="utf-8", skiprows=1, header=None)

# Spaltennamen zuweisen
raw.columns = ["Activity", "kcal_130lb", "kcal_155lb", "kcal_180lb", "kcal_205lb", "kcal_per_kg"]

# 2. Synthetische Trainingsdaten erzeugen
activities = raw["Activity"]
kcal_per_kg = raw["kcal_per_kg"]

gewicht_list = list(range(50, 101, 5))  # kg
dauer_list = list(range(30, 181, 15))   # Minuten

records = []
for act, kcal_kg in zip(activities, kcal_per_kg):
    for g in gewicht_list:
        for d in dauer_list:
            kcal = d * g * kcal_kg / 60
            records.append({
                "Activity": act,
                "Gewicht": g,
                "Dauer": d,
                "kcal": kcal
            })

df = pd.DataFrame(records)

# 3. Features und Ziel definieren
X = df[["Activity", "Gewicht", "Dauer"]]
y = df["kcal"]

# 4. Pipeline mit OneHotEncoding + RandomForest
preprocessor = ColumnTransformer([
    ("activity", OneHotEncoder(handle_unknown="ignore"), ["Activity"])
], remainder="passthrough")

model = make_pipeline(preprocessor, RandomForestRegressor(n_estimators=100, random_state=42))

# 5. Train/Test-Split und Training
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
model.fit(X_train, y_train)

# 6. Evaluation
preds = model.predict(X_test)
rmse = sqrt(mean_squared_error(y_test, preds))
print(f"✅ Modell fertig – RMSE: {rmse:.2f} kcal")

# 7. Modell speichern
os.makedirs("models", exist_ok=True)
joblib.dump(model, "models/calorie_predictor.pkl")
print("💾 Modell gespeichert in models/calorie_predictor.pkl")



