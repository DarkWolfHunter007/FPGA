import streamlit as st
import pandas as pd
import joblib

from pathlib import Path
import sys

# Find the FPGA project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Allow Python to find the ml package
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import pandas as pd
import joblib

from ml.feature_engineering import create_features


# ============================================================
# Page
# ============================================================

st.set_page_config(
    page_title="FPGA Health Monitor",
    layout="wide"
)


st.title(
    "AI-Assisted FPGA Health Monitoring"
)


# ============================================================
# Load model
# ============================================================

saved = joblib.load(
    "ml/models/fpga_health_model.pkl"
)

model = saved["model"]

features = saved["features"]


# ============================================================
# Load data
# ============================================================

df = pd.read_csv(
    "data/raw/mock_fpga_data.csv"
)


df = create_features(
    df
)


# ============================================================
# Predict
# ============================================================

X = df[features]

df["Prediction"] = (
    model.predict(X)
)

df["Confidence"] = (
    model.predict_proba(X)
    .max(axis=1)
)


latest = df.iloc[-1]


# ============================================================
# Current health
# ============================================================

st.subheader(
    "Current FPGA Health"
)


col1, col2, col3 = st.columns(3)


with col1:

    st.metric(
        "Health",
        latest["Prediction"]
    )


with col2:

    st.metric(
        "Confidence",
        f"{latest['Confidence'] * 100:.1f}%"
    )


with col3:

    st.metric(
        "Temperature",
        f"{latest['Temperature']:.2f} °C"
    )


# ============================================================
# Hardware measurements
# ============================================================

st.subheader(
    "FPGA Measurements"
)


col1, col2, col3, col4 = st.columns(4)


with col1:

    st.metric(
        "VCCINT",
        f"{latest['VCCINT']:.3f} V"
    )


with col2:

    st.metric(
        "VCCAUX",
        f"{latest['VCCAUX']:.3f} V"
    )


with col3:

    st.metric(
        "VCCBRAM",
        f"{latest['VCCBRAM']:.3f} V"
    )


with col4:

    st.metric(
        "RO Frequency",
        f"{latest['RO_Frequency']:.2f} MHz"
    )


# ============================================================
# Trends
# ============================================================

st.subheader(
    "FPGA Health Trends"
)


st.line_chart(
    df[
        [
            "Temperature",
            "RO_Frequency"
        ]
    ]
)


st.subheader(
    "Functional Error Rate"
)


st.line_chart(
    df[
        [
            "Error_Rate"
        ]
    ]
)


# ============================================================
# Raw data
# ============================================================

st.subheader(
    "Latest Measurements"
)


st.dataframe(
    df.tail(20)
)