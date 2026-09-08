"""
Reusable UI Components for the FPGA Health Monitoring Dashboard
==============================================================
Implements modular technical components adhering strictly to the
embedded-systems laboratory aesthetic and research guidelines.
Uses st.html() to cleanly render raw HTML/SVG without CommonMark code-block parsing.
"""

import textwrap
from typing import Dict, Any, List
import pandas as pd
import streamlit as st

from dashboard.config import SENSOR_CONFIG, HEALTH_COLORS, STATUS_BG_COLORS, DEVICE_NAME, RO_STAGES
from dashboard.styles import get_fpga_chip_svg, render_primary_health_card, render_measurement_card


def render_header(status_label: str = "ACTIVE", source_label: str = "MOCK DATA", platform: str = DEVICE_NAME):
    """Renders the top centered FPGA research banner with inline SVG chip."""
    chip_svg = get_fpga_chip_svg(size=90)
    badge_source_class = "badge-mock" if "MOCK" in source_label.upper() else "badge-live"

    html = textwrap.dedent(f"""
<div class="header-box">
    <div class="header-title">AI-Assisted FPGA Health Monitoring</div>
    <div>{chip_svg}</div>
    <div class="header-subtitle">
        AI-Based Predictive Health Monitoring and Intelligent Recommendation System
    </div>
    <div class="status-badge-container">
        <div class="badge-pill badge-active">
            <span class="pulse-dot"></span>
            Monitoring Status: {status_label}
        </div>
        <div class="badge-pill {badge_source_class}">
            DATA SOURCE: {source_label}
        </div>
        <div class="badge-pill badge-chip">
            Target: {platform}
        </div>
    </div>
</div>
""").strip()
    st.html(html)


def render_primary_health_kpis(
    health_pred: str,
    confidence: float,
    temperature: float,
    error_rate: float
):
    """
    Section 2: Four primary KPI cards:
    1. FPGA Health (Color-coded: Healthy, Warning, Degraded, Critical)
    2. ML Confidence (%)
    3. Die Temperature (°C)
    4. Error Risk (Low / Medium / High / Critical)
    """
    health_color = HEALTH_COLORS.get(health_pred, "#00E676")
    bg_color = STATUS_BG_COLORS.get(health_pred, "rgba(0, 230, 118, 0.12)")

    # Derive error risk label
    if health_pred == "Degraded" or error_rate > 0.002:
        risk_label = "High"
        risk_color = HEALTH_COLORS["Degraded"]
    elif health_pred == "Warning" or error_rate > 0.0008:
        risk_label = "Medium"
        risk_color = HEALTH_COLORS["Warning"]
    else:
        risk_label = "Low"
        risk_color = HEALTH_COLORS["Healthy"]

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.html(
            render_primary_health_card(
                title="FPGA Health",
                value=health_pred,
                subtext="ML Classified State",
                state_color=health_color,
                bg_color=bg_color
            )
        )

    with c2:
        st.html(
            render_primary_health_card(
                title="ML Confidence",
                value=f"{confidence * 100:.1f} %",
                subtext="Random Forest Probability",
                state_color="#00E5FF",
                bg_color="rgba(0, 229, 255, 0.12)"
            )
        )

    with c3:
        temp_color = "#FF5252" if temperature > 50.0 else ("#FFD600" if temperature > 42.0 else "#00E676")
        st.html(
            render_primary_health_card(
                title="Die Temperature",
                value=f"{temperature:.2f} °C",
                subtext="XADC On-Chip Sensor",
                state_color=temp_color,
                bg_color="rgba(255, 82, 82, 0.12)"
            )
        )

    with c4:
        st.html(
            render_primary_health_card(
                title="Error Risk",
                value=risk_label,
                subtext=f"Rate: {error_rate:.5f}",
                state_color=risk_color,
                bg_color="rgba(255, 145, 0, 0.12)"
            )
        )


def render_measurements_grid(latest: pd.Series, baseline: Dict[str, float], sample_num: int = 0):
    """
    Section 3: Grid of 8 FPGA physical sensor telemetry cards with units & deltas.
    """
    c1, c2, c3, c4 = st.columns(4)
    c5, c6, c7, c8 = st.columns(4)

    temp_base = baseline.get("Temperature", 35.0)
    temp_delta = latest["Temperature"] - temp_base

    vccint_base = baseline.get("VCCINT", 1.000)
    vccint_delta = latest["VCCINT"] - vccint_base

    vccaux_base = baseline.get("VCCAUX", 1.800)
    vccaux_delta = latest["VCCAUX"] - vccaux_base

    vccbram_base = baseline.get("VCCBRAM", 1.000)
    vccbram_delta = latest["VCCBRAM"] - vccbram_base

    ro_freq_base = baseline.get("RO_Frequency", 250.0)
    ro_freq_delta = latest["RO_Frequency"] - ro_freq_base

    ro_delay_base = baseline.get("RO_Delay_ns", 0.4000)
    ro_delay_delta = latest["RO_Delay_ns"] - ro_delay_base

    with c1:
        st.html(
            render_measurement_card(
                label="Die Temperature",
                value_str=f"{latest['Temperature']:.2f}",
                unit="°C",
                delta_str=f"Δ {temp_delta:+.2f} °C",
                delta_color="#FF5252" if temp_delta > 5 else "#00E676"
            )
        )

    with c2:
        st.html(
            render_measurement_card(
                label="VCCINT (Core)",
                value_str=f"{latest['VCCINT']:.3f}",
                unit="V",
                delta_str=f"Δ {vccint_delta:+.3f} V",
                delta_color="#94A3B8"
            )
        )

    with c3:
        st.html(
            render_measurement_card(
                label="VCCAUX (Aux)",
                value_str=f"{latest['VCCAUX']:.3f}",
                unit="V",
                delta_str=f"Δ {vccaux_delta:+.3f} V",
                delta_color="#94A3B8"
            )
        )

    with c4:
        st.html(
            render_measurement_card(
                label="VCCBRAM (Block RAM)",
                value_str=f"{latest['VCCBRAM']:.3f}",
                unit="V",
                delta_str=f"Δ {vccbram_delta:+.3f} V",
                delta_color="#94A3B8"
            )
        )

    with c5:
        st.html(
            render_measurement_card(
                label="RO Frequency",
                value_str=f"{latest['RO_Frequency']:.2f}",
                unit="MHz",
                delta_str=f"Δ {ro_freq_delta:+.2f} MHz",
                delta_color="#FF9100" if ro_freq_delta < -3.0 else "#00E676"
            )
        )

    with c6:
        st.html(
            render_measurement_card(
                label="Derived RO Stage Delay",
                value_str=f"{latest['RO_Delay_ns']:.4f}",
                unit="ns/stage",
                delta_str=f"Δ {ro_delay_delta:+.4f} ns",
                delta_color="#D946EF"
            )
        )

    with c7:
        st.html(
            render_measurement_card(
                label="Functional Error Rate",
                value_str=f"{latest['Error_Rate']:.5f}",
                unit="",
                delta_str=f"{'ELEVATED' if latest['Error_Rate'] > 0.001 else 'NOMINAL'}",
                delta_color="#FF9100" if latest['Error_Rate'] > 0.001 else "#00E676"
            )
        )

    with c8:
        st.html(
            render_measurement_card(
                label="Telemetry Cycle / Sample",
                value_str=f"#{sample_num}",
                unit="",
                delta_str="Synchronized",
                delta_color="#00E5FF"
            )
        )


def render_ring_oscillator_section(latest: pd.Series, baseline: Dict[str, float]):
    """
    Section 4: Dedicated Ring Oscillator Aging Indicator.
    Calculates Frequency Shift (%) and Delay Shift (%), and presents the mathematical model.
    """
    curr_freq = latest["RO_Frequency"]
    base_freq = baseline.get("RO_Frequency", 250.0)
    freq_shift_pct = ((curr_freq - base_freq) / base_freq) * 100.0

    curr_delay = latest["RO_Delay_ns"]
    base_delay = baseline.get("RO_Delay_ns", 0.4000)
    delay_shift_pct = ((curr_delay - base_delay) / base_delay) * 100.0

    c1, c2, c3 = st.columns(3)

    with c1:
        st.html(
            render_primary_health_card(
                title="RO Frequency Shift",
                value=f"{freq_shift_pct:+.2f} %",
                subtext=f"Current: {curr_freq:.2f} MHz | Baseline: {base_freq:.2f} MHz",
                state_color="#FF9100" if freq_shift_pct < -3.0 else "#00E676",
                bg_color="rgba(255, 145, 0, 0.12)"
            )
        )

    with c2:
        st.html(
            render_primary_health_card(
                title="RO Delay Shift (Derived)",
                value=f"{delay_shift_pct:+.2f} %",
                subtext=f"Current: {curr_delay:.4f} ns | Baseline: {base_delay:.4f} ns",
                state_color="#D946EF" if delay_shift_pct > 3.0 else "#00E676",
                bg_color="rgba(217, 70, 239, 0.12)"
            )
        )

    with c3:
        status_text = "Severe Aging Drift" if freq_shift_pct < -5.0 else ("Moderate Degradation" if freq_shift_pct < -2.5 else "Nominal Frequency")
        status_color = HEALTH_COLORS["Degraded"] if freq_shift_pct < -5.0 else (HEALTH_COLORS["Warning"] if freq_shift_pct < -2.5 else HEALTH_COLORS["Healthy"])
        st.html(
            render_primary_health_card(
                title="Timing Degradation Status",
                value=status_text,
                subtext=f"Aging Signature: {'Positive (Gate Slowing)' if freq_shift_pct < -2.0 else 'None'}",
                state_color=status_color,
                bg_color="rgba(0, 229, 255, 0.12)"
            )
        )


def render_baseline_comparison(latest: pd.Series, baseline: Dict[str, float]):
    """
    Section 18: Baseline Comparison Table.
    """
    rows = []

    # Temperature
    t_curr = latest["Temperature"]
    t_base = baseline.get("Temperature", 35.0)
    t_delta = t_curr - t_base
    rows.append({
        "Sensor Channel": "Die Temperature",
        "Current Measurement": f"{t_curr:.2f} °C",
        "Baseline Benchmark": f"{t_base:.2f} °C",
        "Absolute / Relative Shift": f"{t_delta:+.2f} °C ({(t_delta/t_base)*100:+.1f}%)",
        "Assessment": "Elevated Thermal Dissipation" if t_delta > 10 else "Nominal Operating Temp"
    })

    # RO Frequency
    f_curr = latest["RO_Frequency"]
    f_base = baseline.get("RO_Frequency", 250.0)
    f_shift = ((f_curr - f_base) / f_base) * 100.0
    rows.append({
        "Sensor Channel": "Ring Oscillator Frequency",
        "Current Measurement": f"{f_curr:.2f} MHz",
        "Baseline Benchmark": f"{f_base:.2f} MHz",
        "Absolute / Relative Shift": f"{f_curr - f_base:+.2f} MHz ({f_shift:+.2f}%)",
        "Assessment": "Degraded Logic Speed" if f_shift < -3.5 else "Nominal Oscillation"
    })

    # RO Delay
    d_curr = latest["RO_Delay_ns"]
    d_base = baseline.get("RO_Delay_ns", 0.4000)
    d_shift = ((d_curr - d_base) / d_base) * 100.0
    rows.append({
        "Sensor Channel": "Derived RO Stage Delay",
        "Current Measurement": f"{d_curr:.4f} ns",
        "Baseline Benchmark": f"{d_base:.4f} ns",
        "Absolute / Relative Shift": f"{d_curr - d_base:+.4f} ns ({d_shift:+.2f}%)",
        "Assessment": "Timing Margin Degradation" if d_shift > 3.5 else "Nominal Timing"
    })

    # VCCINT
    v_curr = latest["VCCINT"]
    v_base = baseline.get("VCCINT", 1.000)
    v_delta = v_curr - v_base
    rows.append({
        "Sensor Channel": "VCCINT (Internal Core Voltage)",
        "Current Measurement": f"{v_curr:.4f} V",
        "Baseline Benchmark": f"{v_base:.4f} V",
        "Absolute / Relative Shift": f"{v_delta:+.4f} V ({(v_delta/v_base)*100:+.2f}%)",
        "Assessment": "Stable Within Tolerance" if abs(v_delta) < 0.02 else "Voltage Droop"
    })

    # Error Rate
    e_curr = latest["Error_Rate"]
    e_base = baseline.get("Error_Rate", 0.00001)
    rows.append({
        "Sensor Channel": "Functional Error Rate",
        "Current Measurement": f"{e_curr:.6f}",
        "Baseline Benchmark": f"{e_base:.6f}",
        "Absolute / Relative Shift": f"{e_curr - e_base:+.6f}",
        "Assessment": "Elevated Error Stress" if e_curr > 0.001 else "Negligible Soft Errors"
    })

    df_comp = pd.DataFrame(rows)
    st.dataframe(df_comp, width="stretch", hide_index=True)


def render_sensor_status_table(latest: pd.Series, history_df: pd.DataFrame):
    """
    Section 7: Current Sensor Status Table with Centralized Config Thresholds and Trends.
    """
    rows = []

    def get_trend_str(series: pd.Series) -> str:
        if len(series) < 3:
            return "→ Stable"
        diff = series.iloc[-1] - series.iloc[-3]
        pct = (diff / (abs(series.iloc[-3]) + 1e-9)) * 100.0
        if pct > 0.5:
            return "↑ Increasing"
        elif pct < -0.5:
            return "↓ Decreasing"
        return "→ Stable"

    for param, cfg in SENSOR_CONFIG.items():
        if param not in latest:
            continue
        val = latest[param]
        trend = get_trend_str(history_df[param]) if param in history_df.columns else "→ Stable"

        status = "NORMAL"
        if param == "Temperature":
            if val >= cfg["critical"]:
                status = "CRITICAL (HIGH)"
            elif val >= cfg["warning"]:
                status = "WARNING (ELEVATED)"
        elif param == "RO_Frequency":
            nom = cfg["nominal"]
            drop_pct = ((nom - val) / nom) * 100.0
            if drop_pct >= cfg["critical_drop_pct"]:
                status = "CRITICAL (DEGRADED)"
            elif drop_pct >= cfg["warning_drop_pct"]:
                status = "WARNING (SHIFTED)"
        elif param == "RO_Delay_ns":
            nom = cfg["nominal"]
            inc_pct = ((val - nom) / nom) * 100.0
            if inc_pct >= cfg["critical_increase_pct"]:
                status = "CRITICAL (SLOWED)"
            elif inc_pct >= cfg["warning_increase_pct"]:
                status = "WARNING (DRIFT)"
        elif param == "Error_Rate":
            if val >= cfg["critical"]:
                status = "CRITICAL (HIGH)"
            elif val >= cfg["warning"]:
                status = "ELEVATED"
        elif "min_nominal" in cfg and "max_nominal" in cfg:
            if not (cfg["min_nominal"] <= val <= cfg["max_nominal"]):
                status = "OUT OF TOLERANCE"

        rows.append({
            "Parameter Channel": cfg["display_name"],
            "Current Reading": f"{val:.4f} {cfg['unit']}".strip(),
            "Nominal Value": f"{cfg['nominal']:.4f} {cfg['unit']}".strip(),
            "Status Evaluation": status,
            "Temporal Trend": trend
        })

    status_df = pd.DataFrame(rows)
    st.dataframe(status_df, width="stretch", hide_index=True)


def render_agent_recommendations_section(agent_res: Dict[str, Any]):
    """
    Section 10-13: LangGraph Agent AI Health Assessment & Recommendations.
    """
    risk_level = agent_res.get("risk_level", "LOW")
    summary = agent_res.get("condition_summary", "")
    indicators = agent_res.get("primary_indicators", [])
    actions = agent_res.get("recommended_actions", {})

    risk_color = (
        HEALTH_COLORS["Critical"] if "CRITICAL" in risk_level else (
            HEALTH_COLORS["Degraded"] if "HIGH" in risk_level else (
                HEALTH_COLORS["Warning"] if "MODERATE" in risk_level else HEALTH_COLORS["Healthy"]
            )
        )
    )

    indicators_html = "".join([f"<li style='margin-bottom: 6px;'>{ind}</li>" for ind in indicators])

    actions_html = ""
    for category, desc in actions.items():
        actions_html += f"""
        <div class="action-card">
            <div class="action-category">{category} Advisory</div>
            <div>{desc}</div>
        </div>
        """

    html = textwrap.dedent(f"""
<div class="agent-container">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap;">
        <div class="agent-badge">AI AGENTIC DIAGNOSTIC REASONING &bull; LANGGRAPH ENGINE</div>
        <div style="font-family: 'JetBrains Mono', monospace; font-weight: 700; color: {risk_color};">
            OPERATIONAL RISK: {risk_level}
        </div>
    </div>

    <div style="font-size: 1.05rem; font-weight: 600; color: #F8FAFC; margin-bottom: 14px;">
        {summary}
    </div>

    <div style="margin: 14px 0 16px 0;">
        <div style="font-size: 0.85rem; font-weight: 700; color: #00E5FF; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px;">
            Observed Physical & Telemetry Indicators:
        </div>
        <ul style="color: #CBD5E1; font-size: 0.9rem; padding-left: 20px;">
            {indicators_html}
        </ul>
    </div>

    <div style="margin-top: 18px;">
        <div style="font-size: 0.85rem; font-weight: 700; color: #38BDF8; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">
            Targeted Engineering Recommendations:
        </div>
        {actions_html}
    </div>
</div>
""").strip()
    st.html(html)


def render_life_extension_section(agent_res: Dict[str, Any]):
    """
    Section 12: FPGA Life Extension Suggestions (Categorized Practical Tips).
    Uses proper non-guarantee scientific phrasing.
    """
    suggestions = agent_res.get("life_extension_suggestions", {})
    if not suggestions:
        return

    c1, c2 = st.columns(2)
    categories = list(suggestions.keys())

    half = (len(categories) + 1) // 2
    left_cats = categories[:half]
    right_cats = categories[half:]

    def build_cat_card(cat_name: str, tips: List[str]) -> str:
        tips_li = "".join([f"<li style='margin-bottom: 4px;'>{t}</li>" for t in tips])
        return textwrap.dedent(f"""
<div style="background: #111827; border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 14px 16px; margin-bottom: 12px;">
    <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.82rem; font-weight: 700; color: #00E5FF; text-transform: uppercase; margin-bottom: 6px;">
        ⚙️ {cat_name}
    </div>
    <ul style="color: #94A3B8; font-size: 0.84rem; padding-left: 18px; margin: 0;">
        {tips_li}
    </ul>
</div>
""").strip()

    with c1:
        for cat in left_cats:
            st.html(build_cat_card(cat, suggestions[cat]))

    with c2:
        for cat in right_cats:
            st.html(build_cat_card(cat, suggestions[cat]))

    st.caption(
        "💡 *Notice: Recommendations are based on accelerated silicon aging principles (e.g. Arrhenius thermal acceleration, BTI, and dynamic power scaling) and serve to guide operational optimization.*"
    )
