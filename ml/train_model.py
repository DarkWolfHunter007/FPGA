import os
import sys

import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier

from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix
)

# Allow import from current directory

from ml.feature_engineering import create_features


# ============================================================
# Configuration
# ============================================================

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_FILE = PROJECT_ROOT / "data" / "raw" / "mock_fpga_data.csv"
MODEL_FILE = PROJECT_ROOT / "ml" / "models" / "fpga_health_model.pkl"

# ============================================================
# Load data
# ============================================================

print("Loading dataset...")

df = pd.read_csv(DATA_FILE)

print(f"Dataset size: {df.shape}")


# ============================================================
# Feature engineering
# ============================================================

df = create_features(df)


# ============================================================
# Features
# ============================================================

FEATURES = [

    "Temperature",

    "VCCINT",
    "VCCAUX",
    "VCCBRAM",

    "RO_Frequency",
    "RO_Delay_ns",

    "Error_Rate",

    "Temperature_change",

    "RO_Frequency_change",
    "RO_Delay_change",

    "Error_Rate_change",

    "Temperature_mean",
    "Temperature_std",

    "RO_Frequency_mean",
    "RO_Frequency_std",

    "Error_Rate_mean"
]


TARGET = "Health"


X = df[FEATURES]

y = df[TARGET]


# ============================================================
# Train/test split
# ============================================================

X_train, X_test, y_train, y_test = train_test_split(

    X,
    y,

    test_size=0.20,

    random_state=42,

    stratify=y
)


print("\nTraining samples:", len(X_train))
print("Testing samples:", len(X_test))


# ============================================================
# Random Forest
# ============================================================

model = RandomForestClassifier(

    n_estimators=200,

    max_depth=12,

    random_state=42,

    class_weight="balanced"

)


print("\nTraining Random Forest...")

model.fit(
    X_train,
    y_train
)


# ============================================================
# Evaluation
# ============================================================

predictions = model.predict(X_test)


accuracy = accuracy_score(
    y_test,
    predictions
)


print("\n==============================")
print("MODEL RESULTS")
print("==============================")

print(
    f"Accuracy: {accuracy:.4f}"
)


print("\nClassification Report:")

print(
    classification_report(
        y_test,
        predictions
    )
)


print("\nConfusion Matrix:")

print(
    confusion_matrix(
        y_test,
        predictions
    )
)


# ============================================================
# Feature importance
# ============================================================

print("\nFeature importance:")

importance = model.feature_importances_

for feature, value in sorted(
    zip(FEATURES, importance),
    key=lambda x: x[1],
    reverse=True
):

    print(
        f"{feature:30s} {value:.4f}"
    )


# ============================================================
# Save model
# ============================================================

os.makedirs(
    "models",
    exist_ok=True
)


joblib.dump(

    {
        "model": model,
        "features": FEATURES
    },

    MODEL_FILE
)


print("\nModel saved to:")

print(MODEL_FILE)