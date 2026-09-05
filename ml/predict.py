import joblib
import pandas as pd

from feature_engineering import create_features


MODEL_FILE = "models/fpga_health_model.pkl"


# ============================================================
# Load model
# ============================================================

saved = joblib.load(
    MODEL_FILE
)

model = saved["model"]

features = saved["features"]


# ============================================================
# Predict health
# ============================================================

def predict_health(df):

    df = create_features(
        df.copy()
    )

    X = df[features]

    prediction = model.predict(X)

    probabilities = model.predict_proba(X)

    confidence = probabilities.max(
        axis=1
    )

    result = df.copy()

    result["Predicted_Health"] = prediction

    result["Confidence"] = confidence

    return result


# ============================================================
# Test with latest data
# ============================================================

if __name__ == "__main__":

    data = pd.read_csv(
        "../data/raw/mock_fpga_data.csv"
    )

    result = predict_health(data)

    print(
        result[
            [
                "Timestamp",
                "Predicted_Health",
                "Confidence"
            ]
        ].tail(10)
    )