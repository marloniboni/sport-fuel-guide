import joblib
import pandas as pd

model = joblib.load("models/calorie_predictor.pkl")

X = pd.DataFrame([{
    "Activity": "Running",
    "Gewicht": 70,
    "Dauer": 60
}])

print("🔎 Prediction für 60 Min Laufen, 70kg:")
print(model.predict(X)[0])
