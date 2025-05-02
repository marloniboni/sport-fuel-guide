import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
import joblib
import os

# 1. CSV laden (Pfad anpassen, wenn nötig)
with open("sport-fuel-ml/exercise_dataset.csv", encoding="utf-8") as f:
    lines = f.readlines()

data = []
for line in lines[1:]:  # skip header
    parts = line.strip().split(',')
    if len(parts) >= 6:
        activity = ",".join(parts[:-5]).strip()
        try:
            vals = list(map(float, parts[-5:]))
            data.append([activity] + vals)
        except ValueError:
            continue  # Zeile überspringen bei Fehlern

import pandas as pd
df = pd.DataFrame(data, columns=["Activity", "kcal_130lb", "kcal_155lb", "kcal_180lb", "kcal_205lb", "kcal_per_kg"])

df.columns = ["Activity", "kcal_130lb", "kcal_155lb", "kcal_180lb", "kcal_205lb", "kcal_per_kg"]

# 2. Zusätzliche Features hinzufügen
df["Gewicht"] = 130 * 0.453592  # 130 lb ≈ 59 kg
df["Dauer"] = 60  # Minuten

# 3. Features & Ziel definieren
X = df[["Activity", "Gewicht", "Dauer"]]
y = df["kcal_130lb"]

# 4. Pipeline bauen
preprocessor = ColumnTransformer([
    ("activity", OneHotEncoder(handle_unknown="ignore"), ["Activity"])
], remainder="passthrough")

model = make_pipeline(preprocessor, RandomForestRegressor(n_estimators=100, random_state=42))

# 5. Modell trainieren
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
model.fit(X_train, y_train)

# 6. Modell bewerten
preds = model.predict(X_test)
from math import sqrt
mse = mean_squared_error(y_test, preds)
rmse = sqrt(mse)
print(f"✅ Modell fertig – RMSE: {rmse:.2f} kcal")

# 7. Modell speichern
os.makedirs("models", exist_ok=True)
joblib.dump(model, "models/calorie_predictor.pkl")
print("💾 Modell gespeichert in models/calorie_predictor.pkl")

