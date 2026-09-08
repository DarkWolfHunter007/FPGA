"""
AI-Assisted FPGA Health Monitoring and Predictive Health Management System
========================================================================
Main Streamlit Research & Demonstration Application
"""

import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional

import streamlit as st
import pandas as pd
import numpy as np
import joblib

# -----------------------------------------------------------------------------
# Workspace Path Configuration
# -----------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import RO_STAGES
from dashboard.config import (
    DEVICE_NAME,
    ARCHITECTURE,
    HEALTH_COLORS,
    STATUS_BG_COLORS,
    SENSOR_CONFIG
)
from dashboard.styles import get_custom_css
from dashboard.data_source import (
    MockCSVDataSource,
    LiveSimulationDataSource,
    LiveUARTDataSource,
    validate_and_clean_data
)
from dashboard.components import (
    render_header,
    render_primary_health_kpis,
    render_measurements_grid,
    render_ring_oscillator_section,
    render_baseline_comparison,
    render_sensor_status_table,
    render_agent_recommendations_section,
    render_life_extension_section
)
from dashboard.charts import (
    create_temperature_chart,
    create_ro_frequency_chart,
    create_ro_delay_chart,
    create_error_rate_chart,
    create_voltage_chart,
    create_health_prediction_trend_chart,
    create_normalized_indicators_chart,
    create_feature_importance_chart
)
from dashboard.health_map import (
    calculate_aggregate_risk_score,
    generate_risk_cells,
    render_health_risk_map_html
)
from agent.langgraph_agent import evaluate_fpga_health


# =============================================================================
# Streamlit Page Setup
# =============================================================================
st.set_page_config(
    page_title="AI-Assisted FPGA Health Monitoring",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject Custom Embedded Dark Theme CSS via st.html
st.html(get_custom_css())


# =============================================================================
# Model & Pipeline Loader (Cached)
# =============================================================================
@st.cache_resource(show_spinner=False)
def load_ml_pipeline():
    model_path = PROJECT_ROOT / "ml" / "models" / "fpga_health_model.pkl"
    if not model_path.exists():
        return None, None, f"Model file not found at: {model_path}"
    try:
        saved = joblib.load(model_path)
        return saved.get("model"), saved.get("features"), None
    except Exception as e:
        return None, None, f"Failed to deserialize model: {str(e)}"


# =============================================================================
# Session State Initialization
# =============================================================================
if "data_mode" not in st.session_state:
    st.session_state.data_mode = "Mock Dataset (CSV Replay)"
if "sample_index" not in st.session_state:
    st.session_state.sample_index = 3500  # Default to an interesting transitional state
if "auto_refresh" not in st.session_state:
    st.session_state.auto_refresh = False
if "refresh_rate" not in st.session_state:
    st.session_state.refresh_rate = 2
if "sim_source" not in st.session_state:
    st.session_state.sim_source = LiveSimulationDataSource()
if "mock_source" not in st.session_state:
    try:
        st.session_state.mock_source = MockCSVDataSource()
    except Exception:
        st.session_state.mock_source = None
if "uart_source" not in st.session_state:
    st.session_state.uart_source = LiveUARTDataSource(port="COM3")


# =============================================================================
# Sidebar Control Panel
# =============================================================================
with st.sidebar:
    st.markdown("### 🎛️ Telemetry Source & Controls")
    
    data_mode = st.selectbox(
        "Select Telemetry Source",
        ["Mock Dataset (CSV Replay)", "Dynamic Simulation Stream", "Physical UART Stream (Artix-7)"],
        index=0 if st.session_state.data_mode == "Mock Dataset (CSV Replay)" else (1 if "Simulation" in st.session_state.data_mode else 2)
    )
    st.session_state.data_mode = data_mode

    st.markdown("---")

    # Mode-specific controls
    if "Mock Dataset" in data_mode:
        if st.session_state.mock_source is not None:
            total_samples = len(st.session_state.mock_source.raw_df)
            st.session_state.sample_index = st.slider(
                "Historical Sample Timeline Scrubber",
                min_value=0,
                max_value=total_samples - 1,
                value=min(st.session_state.sample_index, total_samples - 1),
                step=50,
                help="Slide to simulate FPGA transition across healthy, warning, and degraded aging lifecycle."
            )

            col_p1, col_p2, col_p3 = st.columns(3)
            with col_p1:
                if st.button("🟢 Healthy", width="stretch"):
                    st.session_state.sample_index = 1000
                    st.rerun()
            with col_p2:
                if st.button("🟡 Warning", width="stretch"):
                    st.session_state.sample_index = 5000
                    st.rerun()
            with col_p3:
                if st.button("🟠 Degraded", width="stretch"):
                    st.session_state.sample_index = 9200
                    st.rerun()

    elif "Simulation" in data_mode:
        sim_deg = st.slider("Simulated Aging Degradation Factor", 0.0, 1.0, 0.45, 0.05)
        if st.button("⚡ Inject Step Measurement", width="stretch"):
            st.session_state.sim_source.step(degradation=sim_deg)
            st.rerun()
        if st.button("🔄 Reset Simulation Buffer", width="stretch"):
            st.session_state.sim_source.reset()
            st.rerun()

    elif "Physical UART" in data_mode:
        available_ports = LiveUARTDataSource.receiver.list_available_ports() if hasattr(LiveUARTDataSource, "receiver") else ["COM3"]
        selected_port = st.selectbox("UART COM Port", available_ports, index=0)
        st.session_state.uart_source.receiver.port = selected_port

        col_u1, col_u2 = st.columns(2)
        with col_u1:
            if st.button("🔌 Connect", width="stretch"):
                success = st.session_state.uart_source.connect()
                if success:
                    st.success(f"Connected to {selected_port}")
                else:
                    st.warning("Hardware port unavailable; streaming in offline mock fallback.")
        with col_u2:
            if st.button("Disconnect", width="stretch"):
                st.session_state.uart_source.disconnect()
                st.info("Disconnected.")

    st.markdown("---")
    st.markdown("### ⏱️ Live Auto-Refresh")
    st.session_state.auto_refresh = st.toggle("Enable Live Auto-Poll", value=st.session_state.auto_refresh)
    if st.session_state.auto_refresh:
        st.session_state.refresh_rate = st.select_slider(
            "Poll Interval (seconds)",
            options=[1, 2, 5, 10],
            value=st.session_state.refresh_rate
        )

    st.markdown("---")
    st.markdown("### 📋 Hardware Target")
    st.caption(f"**Device**: {DEVICE_NAME}\n\n**Process Node**: {ARCHITECTURE}\n\n**RO Inverter Stages (N)**: {RO_STAGES}\n\n**Sensor Package**: XADC Dual 12-bit 1MSPS + Ring Oscillator Aging Sensor")


# =============================================================================
# Data Acquisition & Feature Transformation
# =============================================================================
model, model_features, model_error = load_ml_pipeline()

if model_error:
    st.error(f"⚠️ {model_error}")
    st.stop()

# Select appropriate data source
try:
    if "Mock Dataset" in data_mode:
        if st.session_state.mock_source is None:
            st.session_state.mock_source = MockCSVDataSource()
        history_df, latest, meta = st.session_state.mock_source.get_data(
            window_size=150,
            sample_idx=st.session_state.sample_index
        )
        source_badge = "MOCK (CSV REPLAY)"

    elif "Simulation" in data_mode:
        if st.session_state.auto_refresh:
            st.session_state.sim_source.step(degradation=0.55)
        history_df, latest, meta = st.session_state.sim_source.get_data(window_size=150)
        source_badge = "LIVE SIMULATION"

    else:
        st.session_state.uart_source.poll_hardware()
        history_df, latest, meta = st.session_state.uart_source.get_data(window_size=150)
        source_badge = f"LIVE UART ({st.session_state.uart_source.receiver.port})"

except Exception as e:
    st.error(f"Sensor data stream unavailable: {str(e)}")
    st.info("Waiting for valid FPGA telemetry stream...")
    st.stop()


# =============================================================================
# ML Inference & Health Classification
# =============================================================================
try:
    missing_feats = [f for f in model_features if f not in history_df.columns]
    if missing_feats:
        st.error(f"Missing required engineered features: {missing_feats}")
        st.stop()

    X_window = history_df[model_features]
    history_df["Predicted_Health"] = model.predict(X_window)
    probs = model.predict_proba(X_window)
    history_df["Confidence"] = probs.max(axis=1)

    latest_pred = str(history_df["Predicted_Health"].iloc[-1])
    latest_conf = float(history_df["Confidence"].iloc[-1])

    classes = list(model.classes_)
    latest_probs = probs[-1]
    prob_dict = {cls: float(latest_probs[i]) for i, cls in enumerate(classes)}

except Exception as e:
    st.error(f"ML Model inference error: {str(e)}")
    st.stop()


# Baseline and shift metrics
baseline = meta.get("baseline", {})
curr_ro_freq = float(latest["RO_Frequency"])
base_ro_freq = float(baseline.get("RO_Frequency", 250.0))
ro_freq_shift = ((curr_ro_freq - base_ro_freq) / base_ro_freq) * 100.0

curr_ro_delay = float(latest["RO_Delay_ns"])
base_ro_delay = float(baseline.get("RO_Delay_ns", 0.4000))
ro_delay_shift = ((curr_ro_delay - base_ro_delay) / base_ro_delay) * 100.0

curr_temp = float(latest["Temperature"])
base_temp = float(baseline.get("Temperature", 35.0))
temp_shift = curr_temp - base_temp

def compute_trend(series: pd.Series) -> str:
    if len(series) < 3:
        return "Stable"
    diff = series.iloc[-1] - series.iloc[-3]
    if diff > 0.05 * (abs(series.iloc[-3]) + 1e-6):
        return "Increasing"
    elif diff < -0.05 * (abs(series.iloc[-3]) + 1e-6):
        return "Decreasing"
    return "Stable"

temp_trend = compute_trend(history_df["Temperature"])
ro_freq_trend = compute_trend(history_df["RO_Frequency"])
error_trend = compute_trend(history_df["Error_Rate"])


# =============================================================================
# LangGraph AI Diagnostic Agent Invocation
# =============================================================================
try:
    agent_telemetry = {
        "health": latest_pred,
        "confidence": latest_conf,
        "temperature": curr_temp,
        "vccint": float(latest["VCCINT"]),
        "vccaux": float(latest["VCCAUX"]),
        "vccbram": float(latest["VCCBRAM"]),
        "ro_frequency": curr_ro_freq,
        "ro_delay": curr_ro_delay,
        "error_rate": float(latest["Error_Rate"]),
        "ro_freq_shift_pct": ro_freq_shift,
        "ro_delay_shift_pct": ro_delay_shift,
        "temp_shift": temp_shift,
        "temp_trend": temp_trend,
        "ro_freq_trend": ro_freq_trend,
        "error_trend": error_trend
    }
    agent_report = evaluate_fpga_health(agent_telemetry)
except Exception as e:
    agent_report = {
        "risk_level": "UNKNOWN",
        "condition_summary": f"Agent diagnostic unavailable ({str(e)})",
        "primary_indicators": ["Live telemetry available, agentic node returned an exception."],
        "recommended_actions": {"Monitoring": "Continue tracking telemetry channels manually."},
        "life_extension_suggestions": {}
    }


# =============================================================================
# DASHBOARD PRESENTATION (Audited Structure & Separate Graphs)
# =============================================================================

# 1. Header, FPGA Chip Logo, Monitoring Status
render_header(
    status_label="ACTIVE",
    source_label=source_badge,
    platform=DEVICE_NAME
)

# 2. CURRENT FPGA HEALTH
st.html('<div class="section-header">⚡ Current FPGA Health <span class="tag">REAL-TIME STATUS</span></div>')
render_primary_health_kpis(
    health_pred=latest_pred,
    confidence=latest_conf,
    temperature=curr_temp,
    error_rate=float(latest["Error_Rate"])
)

# 3. FPGA MEASUREMENTS
st.html('<div class="section-header">📊 FPGA Measurements <span class="tag">XADC & LOGIC TELEMETRY</span></div>')
render_measurements_grid(
    latest=latest,
    baseline=baseline,
    sample_num=meta.get("current_index", len(history_df))
)

# 4. RING OSCILLATOR MONITORING
st.html('<div class="section-header">⏱️ Ring Oscillator Aging Indicator <span class="tag">TIMING DEGRADATION</span></div>')
render_ring_oscillator_section(
    latest=latest,
    baseline=baseline
)

# 5. FPGA HEALTH TRENDS (Dedicated Independent Graphs)
st.html('<div class="section-header">📈 FPGA Health Trends <span class="tag">INDEPENDENT SENSOR DYNAMICS</span></div>')

trend_tab1, trend_tab2, trend_tab3, trend_tab4, trend_tab5 = st.tabs([
    "⏱️ RO Frequency & Timing Delay",
    "🌡️ Die Temperature",
    "⚡ Supply Voltage Rails",
    "⚠️ Functional Error Rate",
    "🏷️ ML State & Multi-Sensor Index"
])

with trend_tab1:
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.caption("**Ring Oscillator Frequency Trend (MHz)** (Cyan line: measurement, Blue dashed: baseline)")
        st.altair_chart(create_ro_frequency_chart(history_df, baseline_freq=base_ro_freq), width="stretch")
    with col_g2:
        st.caption("**Ring Oscillator Delay Trend (Derived RO Stage Delay in ns)** (Magenta line: measurement, Purple dashed: baseline)")
        st.altair_chart(create_ro_delay_chart(history_df, baseline_delay=base_ro_delay), width="stretch")

with trend_tab2:
    st.caption("**FPGA Die Temperature Trend (°C)** (Red line: measurement, Green dashed: baseline 35°C, Orange dashed: 50°C warning)")
    st.altair_chart(create_temperature_chart(history_df, baseline_temp=base_temp), width="stretch")

with trend_tab3:
    col_v1, col_v2, col_v3 = st.columns(3)
    with col_v1:
        st.caption("**VCCINT (1.000V Core Rail)**")
        st.altair_chart(create_voltage_chart(history_df, "VCCINT", 1.000), width="stretch")
    with col_v2:
        st.caption("**VCCAUX (1.800V Auxiliary Rail)**")
        st.altair_chart(create_voltage_chart(history_df, "VCCAUX", 1.800), width="stretch")
    with col_v3:
        st.caption("**VCCBRAM (1.000V BRAM Rail)**")
        st.altair_chart(create_voltage_chart(history_df, "VCCBRAM", 1.000), width="stretch")

with trend_tab4:
    st.caption("**Functional Error Rate Trend** (Amber area: soft error probability)")
    st.altair_chart(create_error_rate_chart(history_df), width="stretch")

with trend_tab5:
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.caption("**FPGA Health Prediction Trend** (Healthy, Warning, Degraded)")
        st.altair_chart(create_health_prediction_trend_chart(history_df), width="stretch")
    with col_s2:
        st.caption("**Normalized FPGA Health Indicators** (Normalized sensor indicators: 0.0=nominal, 1.0=stress)")
        st.altair_chart(create_normalized_indicators_chart(history_df), width="stretch")


# 6. BASELINE COMPARISON
st.html('<div class="section-header">⚖️ Baseline Comparison <span class="tag">DRIFT ANALYSIS</span></div>')
render_baseline_comparison(
    latest=latest,
    baseline=baseline
)

# 7. SENSOR STATUS EVALUATION
st.html('<div class="section-header">🔍 Current Sensor Status <span class="tag">THRESHOLD EVALUATION</span></div>')
render_sensor_status_table(latest=latest, history_df=history_df)

# 8. ML HEALTH PREDICTION
st.html('<div class="section-header">🤖 Machine Learning Prediction <span class="tag">RANDOM FOREST INFERENCE</span></div>')
col_m1, col_m2 = st.columns([1, 1])

with col_m1:
    st.html(f"""
    <div style="background: #111827; border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 16px; height: 100%;">
        <div style="font-size: 0.8rem; color: #94A3B8; text-transform: uppercase; font-family: 'JetBrains Mono', monospace; margin-bottom: 6px;">
            ML Classifier Architecture
        </div>
        <div style="font-size: 1.25rem; font-weight: 700; color: #F8FAFC; margin-bottom: 12px;">
            Random Forest Ensemble (200 Estimators)
        </div>
        <div style="margin-bottom: 10px;">
            <span style="color: #94A3B8; font-size: 0.85rem;">Predicted Health Class:</span>
            <span style="color: {HEALTH_COLORS.get(latest_pred, '#00E676')}; font-weight: 700; font-family: 'JetBrains Mono', monospace; font-size: 1.05rem; margin-left: 6px;">
                {latest_pred.upper()}
            </span>
        </div>
        <div style="margin-bottom: 14px;">
            <span style="color: #94A3B8; font-size: 0.85rem;">Classification Confidence:</span>
            <span style="color: #00E5FF; font-weight: 700; font-family: 'JetBrains Mono', monospace; font-size: 1.05rem; margin-left: 6px;">
                {latest_conf * 100:.1f} %
            </span>
        </div>
        <div style="font-size: 0.8rem; color: #94A3B8; margin-bottom: 6px;">Class Probability Breakdown:</div>
    </div>
    """)

    for cls_name in classes:
        prob_val = prob_dict.get(cls_name, 0.0)
        st.write(f"**{cls_name}**: {prob_val * 100:.1f}%")
        st.progress(min(1.0, max(0.0, prob_val)))

with col_m2:
    if hasattr(model, "feature_importances_"):
        st.caption("**Top Engineered Features Contributing to Prediction**")
        st.altair_chart(
            create_feature_importance_chart(model_features, model.feature_importances_, top_n=7),
            width="stretch"
        )


# 9. FPGA HEALTH RISK MAP
st.html('<div class="section-header">🗺️ FPGA Health Risk Map <span class="tag">VIRTUAL LOGIC FABRIC</span></div>')
composite_risk = calculate_aggregate_risk_score(
    health_pred=latest_pred,
    confidence=latest_conf,
    temp=curr_temp,
    ro_freq_shift_pct=ro_freq_shift,
    error_rate=float(latest["Error_Rate"])
)
risk_cells = generate_risk_cells(composite_risk)
st.html(render_health_risk_map_html(risk_cells, composite_risk))


# 10. AI AGENT RECOMMENDATIONS (LangGraph)
st.html('<div class="section-header">🧠 AI Agent Diagnostic Recommendations <span class="tag">LANGGRAPH REASONING</span></div>')
render_agent_recommendations_section(agent_report)


# 11. FPGA LIFE EXTENSION SUGGESTIONS
st.html('<div class="section-header">🛡️ FPGA Lifetime Extension Guidelines <span class="tag">PROACTIVE MAINTENANCE</span></div>')
render_life_extension_section(agent_report)


# 12. LATEST MEASUREMENTS TABLE & ENGINEERED FEATURES EXPANDER
st.html('<div class="section-header">📋 Latest Telemetry Records <span class="tag">HISTORICAL BUFFER</span></div>')

raw_display_cols = [
    "Temperature", "VCCINT", "VCCAUX", "VCCBRAM",
    "RO_Frequency", "RO_Delay_ns", "Error_Rate"
]
if "Predicted_Health" in history_df.columns:
    raw_display_cols.append("Predicted_Health")
if "Confidence" in history_df.columns:
    raw_display_cols.append("Confidence")

st.dataframe(
    history_df[raw_display_cols].tail(15).style.format({
        "Temperature": "{:.2f} °C",
        "VCCINT": "{:.4f} V",
        "VCCAUX": "{:.4f} V",
        "VCCBRAM": "{:.4f} V",
        "RO_Frequency": "{:.2f} MHz",
        "RO_Delay_ns": "{:.4f} ns",
        "Error_Rate": "{:.6f}",
        "Confidence": "{:.1%}"
    }),
    width="stretch"
)

with st.expander("🔬 Show Engineered ML Features (Differences & Rolling Statistics)"):
    st.dataframe(history_df.tail(15), width="stretch")


# 13. RESEARCH TRANSPARENCY & SYSTEM INFORMATION
with st.expander("ℹ️ System Information & Scientific Research Methodology"):
    st.markdown(f"""
    ### 🔬 System Architecture Pipeline
    ```
    +-----------------------------------------------------------------------------------+
    |                             DIGILENT BASYS 3 ARTIX-7                              |
    |  +-----------------------+   +----------------------+   +-----------------------+ |
    |  |  Ring Oscillator (RO) |   |    XADC Temp/Voltage |   |   Functional Error    | |
    |  |  Aging Delay Sensor   |   |   Die Monitor (1MSPS)|   |    Monitor Engine     | |
    |  +-----------+-----------+   +----------+-----------+   +-----------+-----------+ |
    +--------------|--------------------------|---------------------------|-------------+
                   +--------------------------+---------------------------+
                                              | UART Serial (115200 Baud)
                                              v
    +-----------------------------------------------------------------------------------+
    |                              HOST PROCESSING PIPELINE                             |
    |  +-----------------------+   +----------------------+   +-----------------------+ |
    |  |  Data Validation &    |-->| Feature Engineering  |-->| ML Model (Random      | |
    |  |  Sanitization Layer   |   | (Delta + Rolling Std)|   | Forest Classifier)    | |
    |  +-----------------------+   +----------------------+   +-----------+-----------+ |
    |                                                                     |             |
    |                                                                     v             |
    |  +-----------------------+   +----------------------+   +-----------------------+ |
    |  |  Streamlit Visual     |<--| Actionable Life-     |<--| LangGraph Diagnostic  | |
    |  |  Research Dashboard   |   | Extension Advisory   |   | Reasoning Agent       | |
    |  +-----------------------+   +----------------------+   +-----------------------+ |
    +-----------------------------------------------------------------------------------+
    ```

    **Key Technical Distinctions:**
    - **Observed Telemetry**: Measured hardware signals (XADC die temperature, supply voltages, RO frequency, and soft error rates).
    - **Inferred Health**: Numerical classification state generated by the trained Random Forest classifier (**Healthy**, **Warning**, **Degraded**).
    - **Recommended Actions**: Diagnostic hypotheses and operational life-extension strategies formulated by the LangGraph agentic reasoning graph.
    - **Non-Self-Healing System**: This system performs continuous monitoring, anomaly prediction, risk assessment, and recommendation. It does *not* autonomously repair or reconfigure on-chip hardware logic.

    **Development & Simulation Notice:**
    *Development mode: predictions and demonstrations currently utilize validated synthetic/mock FPGA aging data. Final hardware validation requires continuous accelerated aging data acquired from the physical Artix-7 board.*
    """)


# =============================================================================
# Auto-Refresh Handler
# =============================================================================
if st.session_state.auto_refresh:
    time.sleep(st.session_state.refresh_rate)
    st.rerun()