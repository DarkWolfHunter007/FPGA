from pathlib import Path
import joblib
import pandas as pd

try:
    from ml.feature_engineering import create_features
except ImportError:
    from feature_engineering import create_features

ML_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = ML_DIR.parent
MODEL_FILE = ML_DIR / "models" / "fpga_health_model.pkl"
DATA_FILE = PROJECT_ROOT / "data" / "raw" / "mock_fpga_data.csv"

# ============================================================
# Load model
# ============================================================

saved = joblib.load(MODEL_FILE)
model = saved["model"]
features = saved["features"]


# ============================================================
# Predict health
# ============================================================

def predict_health(df: pd.DataFrame) -> pd.DataFrame:
    df = create_features(df.copy())
    X = df[features]
    prediction = model.predict(X)
    probabilities = model.predict_proba(X)
    confidence = probabilities.max(axis=1)

    result = df.copy()
    result["Predicted_Health"] = prediction
    result["Confidence"] = confidence
    return result


# ============================================================
# Test with latest data
# ============================================================

if __name__ == "__main__":
    if DATA_FILE.exists():
        data = pd.read_csv(DATA_FILE)
        result = predict_health(data)
        print("\n--- ML Health Prediction Sample Output ---")
        print(
            result[
                [
                    "Timestamp",
                    "Temperature",
                    "RO_Frequency",
                    "Predicted_Health",
                    "Confidence"
                ]
            ].tail(10)
        )