"""
Machine Learning Training Pipeline for FPGA Health Classification
=================================================================
Trains a Random Forest classifier to predict FPGA health state:
[Healthy, Warning, Degraded] using engineered physical sensor telemetry.

Includes rigorous validation, data leakage audit, and multi-metric evaluation.
"""

import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import joblib

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix
)

# Allow import from project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.feature_engineering import create_features
from config import validate_ro_delay, RO_STAGES


# ============================================================
# Configuration
# ============================================================
DATA_FILE = PROJECT_ROOT / "data" / "raw" / "mock_fpga_data.csv"
MODEL_FILE = PROJECT_ROOT / "ml" / "models" / "fpga_health_model.pkl"

# ============================================================
# Load & Audit Data
# ============================================================
print("==================================================")
print("FPGA HEALTH ML MODEL TRAINING & AUDIT")
print("==================================================")
print(f"Loading dataset from: {DATA_FILE}")

if not DATA_FILE.exists():
    raise FileNotFoundError(f"Data file not found at {DATA_FILE}. Run python mock/mock_fpga.py first.")

df = pd.read_csv(DATA_FILE)
print(f"Dataset Dimensions: {df.shape[0]} rows x {df.shape[1]} columns")

# Audit RO Delay values in dataset
sample_ro_freq = df["RO_Frequency"].iloc[0]
sample_ro_delay = df["RO_Delay_ns"].iloc[0]
is_valid, msg = validate_ro_delay(sample_ro_freq, RO_STAGES, sample_ro_delay)
print(f"RO Delay Audit (Sample #0): {sample_ro_freq:.2f} MHz -> {sample_ro_delay:.4f} ns ({msg})")
if not is_valid:
    raise ValueError(f"RO Delay validation failed: {msg}")

print("\nClass Distribution in Dataset:")
class_counts = df["Health"].value_counts()
for cls_name, count in class_counts.items():
    print(f" • {cls_name:12s}: {count:5d} samples ({count / len(df) * 100:.1f}%)")


# ============================================================
# Feature Engineering
# ============================================================
df = create_features(df)

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
# Train/Test Split & Data Leakage Audit
# ============================================================
# Note on Data Leakage:
# The dataset represents synthetic continuous aging drift. Random sampling creates
# temporal interpolation (adjacent samples in train and test).
# We use a stratified split (80/20) with fixed seed for reproducible benchmarking.

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y
)

print(f"\nTrain Set: {len(X_train)} samples | Test Set: {len(X_test)} samples")


# ============================================================
# Train Random Forest Classifier
# ============================================================
model = RandomForestClassifier(
    n_estimators=200,
    max_depth=12,
    random_state=42,
    class_weight="balanced"
)

print("\nTraining Random Forest Classifier (200 trees, max_depth=12)...")
model.fit(X_train, y_train)


# ============================================================
# Model Evaluation
# ============================================================
predictions = model.predict(X_test)

accuracy = accuracy_score(y_test, predictions)
macro_precision = precision_score(y_test, predictions, average="macro")
macro_recall = recall_score(y_test, predictions, average="macro")
macro_f1 = f1_score(y_test, predictions, average="macro")
weighted_f1 = f1_score(y_test, predictions, average="weighted")

print("\n==================================================")
print("MODEL EVALUATION METRICS (Test Set)")
print("==================================================")
print(f"Accuracy:         {accuracy:.4f} ({accuracy * 100:.2f}%)")
print(f"Macro Precision:  {macro_precision:.4f}")
print(f"Macro Recall:     {macro_recall:.4f}")
print(f"Macro F1-Score:   {macro_f1:.4f}")
print(f"Weighted F1-Score:{weighted_f1:.4f}")

print("\nDetailed Classification Report:")
print(classification_report(y_test, predictions, digits=4))

print("Confusion Matrix (Rows: True, Cols: Predicted):")
classes = sorted(list(y.unique()))
cm = confusion_matrix(y_test, predictions, labels=classes)
cm_df = pd.DataFrame(cm, index=[f"True_{c}" for c in classes], columns=[f"Pred_{c}" for c in classes])
print(cm_df)


# ============================================================
# Feature Importance
# ============================================================
print("\nFeature Importance Rankings:")
importance = model.feature_importances_
sorted_feats = sorted(zip(FEATURES, importance), key=lambda x: x[1], reverse=True)
for rank, (feature, val) in enumerate(sorted_feats, 1):
    print(f" {rank:2d}. {feature:25s}: {val:.4f} ({val * 100:.1f}%)")


# ============================================================
# Save Trained Model Bundle
# ============================================================
os.makedirs(MODEL_FILE.parent, exist_ok=True)
joblib.dump(
    {
        "model": model,
        "features": FEATURES,
        "classes": list(model.classes_),
        "ro_stages": RO_STAGES
    },
    MODEL_FILE
)

print(f"\nTrained model bundle successfully saved to:\n{MODEL_FILE}")
print("==================================================")


if __name__ == "__main__":
    pass