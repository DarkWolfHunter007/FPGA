"""
LangGraph Diagnostic & Advisory Agent for FPGA Health Management
================================================================
Performs diagnostic reasoning, causal indicator analysis, risk evaluation,
and lifetime extension recommendations based on physical telemetry and
machine learning model inference.

Distinction of roles:
- ML Model: Performs numerical classification (Healthy, Warning, Degraded).
- LangGraph Agent: Interprets physical telemetry, explains causal factors,
  evaluates risk level, and synthesizes engineering recommendations.
"""

import sys
from pathlib import Path
from typing import TypedDict, List, Dict, Any, Optional

# Allow import from project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import RO_STAGES


# ============================================================
# Agent State Definition
# ============================================================

class FPGAState(TypedDict, total=False):
    # Inputs: ML Inference & Telemetry
    health: str
    confidence: float
    temperature: float
    vccint: float
    vccaux: float
    vccbram: float
    ro_frequency: float
    ro_delay: float
    error_rate: float

    # Engineering Limit & Override Metadata
    ml_prediction: str
    override_applied: bool
    override_title: str
    override_explanation: str
    override_reasons: List[str]
    engineering_assessment: Dict[str, Any]
    
    # Baseline Comparison & Dynamics
    ro_freq_shift_pct: float
    ro_delay_shift_pct: float
    temp_shift: float
    temp_trend: str
    ro_freq_trend: str
    error_trend: str

    # Source & Estimation Provenance Metadata
    source: str
    completeness_str: str
    completeness_count: int
    reliability_score: float
    user_provided_channels: List[str]
    assumed_channels: List[str]
    is_estimated: bool

    # Intermediate / Outputs
    condition_summary: str
    primary_indicators: List[str]
    risk_level: str
    recommended_actions: Dict[str, str]
    life_extension_suggestions: Dict[str, List[str]]
    recommendation: str


# ============================================================
# Graph Node 1: Indicator & Condition Analysis
# ============================================================

def analyze_indicators(state: FPGAState) -> FPGAState:
    """Analyze observed hardware telemetry against physical and aging baselines."""
    health = state.get("health", "Healthy")
    conf = state.get("confidence", 0.0)
    ml_pred = state.get("ml_prediction", health)
    override_applied = state.get("override_applied", False)
    override_explanation = state.get("override_explanation", "")
    override_reasons = state.get("override_reasons", [])

    temp = state.get("temperature", 35.0)
    vccint = state.get("vccint", 1.000)
    vccaux = state.get("vccaux", 1.800)
    vccbram = state.get("vccbram", 1.000)
    ro_freq = state.get("ro_frequency", 250.0)
    ro_delay = state.get("ro_delay", 0.4000)
    error_rate = state.get("error_rate", 0.0)
    
    ro_freq_shift = state.get("ro_freq_shift_pct", 0.0)
    ro_delay_shift = state.get("ro_delay_shift_pct", 0.0)
    temp_shift = state.get("temp_shift", 0.0)
    
    indicators: List[str] = []

    # 0. Engineering Safety Override Notice
    if override_applied:
        indicators.append(
            f"⚠️ HARD ENGINEERING LIMIT OVERRIDE: {override_explanation or 'Physical operating boundary breached'}. "
            f"(ML Predicted: '{ml_pred}' with {conf * 100:.1f}% confidence)."
        )

    # 1. Ring Oscillator Aging / Timing Degradation Indicator
    if ro_freq < 238.0 or ro_freq_shift <= -4.8:
        indicators.append(
            f"Significant Ring Oscillator frequency degradation: {ro_freq:.2f} MHz ({ro_freq_shift:+.2f}% from baseline), "
            f"indicating derived logic stage propagation delay increase ({ro_delay:.4f} ns/stage, {ro_delay_shift:+.2f}%)."
        )
    elif ro_freq > 265.0:
        indicators.append(
            f"Abnormal Ring Oscillator over-frequency: {ro_freq:.2f} MHz (+{ro_freq_shift:+.2f}% above nominal), "
            "indicating anomalous clock measurement or sub-ambient clock skew."
        )
    elif ro_freq < 245.0 or ro_freq_shift <= -2.0:
        indicators.append(
            f"Moderate Ring Oscillator frequency drop: {ro_freq:.2f} MHz ({ro_freq_shift:+.2f}% from baseline), "
            f"suggesting onset of timing drift ({ro_delay:.4f} ns/stage)."
        )
    else:
        indicators.append(f"Ring Oscillator frequency is nominal: {ro_freq:.2f} MHz ({ro_freq_shift:+.2f}% shift, delay {ro_delay:.4f} ns/stage).")

    # 2. Thermal Footprint & Operating Envelope
    if temp <= 0.0:
        indicators.append(
            f"Die temperature is abnormal at {temp:.2f} °C (at or below 0°C freezing threshold, expected 20.0–45.0 °C). "
            "Represents an abnormal operating condition or sensor freeze fault."
        )
    elif temp >= 52.0:
        indicators.append(
            f"Die temperature is critically elevated at {temp:.2f} °C ({temp_shift:+.2f} °C above baseline), "
            f"accelerating thermal wear-out mechanisms (e.g., BTI, Electromigration)."
        )
    elif temp >= 45.0:
        indicators.append(f"Die temperature is elevated at {temp:.2f} °C ({temp_shift:+.2f} °C shift, expected 20.0–45.0 °C).")
    elif temp < 20.0:
        indicators.append(f"Die temperature is cool at {temp:.2f} °C (below nominal operating floor 20.0 °C).")
    else:
        indicators.append(f"Die temperature is within normal operating limits: {temp:.2f} °C.")

    # 3. Voltage Rail Stability & Hard Bounds
    voltage_anomalies = []
    if vccint < 0.920:
        voltage_anomalies.append(f"VCCINT critical droop ({vccint:.3f}V < 0.920V min)")
    elif abs(vccint - 1.000) >= 0.050:
        voltage_anomalies.append(f"VCCINT={vccint:.3f}V (nom 1.000V ±5%)")

    if vccaux < 1.650:
        voltage_anomalies.append(f"VCCAUX critical droop ({vccaux:.3f}V < 1.650V min)")
    elif abs(vccaux - 1.800) >= 0.090:
        voltage_anomalies.append(f"VCCAUX={vccaux:.3f}V (nom 1.800V ±5%)")

    if vccbram < 0.920:
        voltage_anomalies.append(f"VCCBRAM critical droop ({vccbram:.3f}V < 0.920V min)")
    elif abs(vccbram - 1.000) >= 0.050:
        voltage_anomalies.append(f"VCCBRAM={vccbram:.3f}V (nom 1.000V ±5%)")

    if voltage_anomalies:
        indicators.append(f"Power rail voltage violations observed: {', '.join(voltage_anomalies)}.")
    else:
        indicators.append(f"Supply voltage rails (VCCINT, VCCAUX, VCCBRAM) are stable within ±5% recommended operating tolerance.")

    # 4. Functional Reliability & Error Rates
    if error_rate >= 0.002:
        indicators.append(f"Functional error rate is critically elevated at {error_rate:.5f}, representing operational stress.")
    elif error_rate >= 0.0005:
        indicators.append(f"Minor increase in functional error rate: {error_rate:.5f}.")
    else:
        indicators.append(f"Functional error rate is negligible ({error_rate:.5f}).")

    # Condition Summary Synthesis
    if override_applied:
        summary = (
            f"FPGA health is governed by an engineering safety override: {health.upper()}. "
            f"{override_explanation or 'Physical operating constraints take precedence over learned ML prediction.'}"
        )
    elif health in ("Degraded", "Critical"):
        summary = (
            f"FPGA exhibits pronounced degradation indicators across timing and thermal domains "
            f"(ML confidence: {conf * 100:.1f}%). Multi-parameter aging signatures indicate elevated operating stress."
        )
    elif health == "Warning":
        summary = (
            f"FPGA is exhibiting early warning signatures of stress/aging (ML confidence: {conf * 100:.1f}%). "
            f"Ring oscillator delay and operating temperatures show measurable shifts from nominal baseline."
        )
    else:
        summary = (
            f"FPGA is operating in a healthy nominal state (ML confidence: {conf * 100:.1f}%). "
            f"All tracked telemetry parameters remain within normal operating envelopes."
        )

    # Telemetry Source & Estimation Caveat Handling
    is_estimated = state.get("is_estimated", False) or state.get("source") == "ESTIMATED"
    if is_estimated:
        comp_str = state.get("completeness_str", "")
        user_channels = state.get("user_provided_channels", [])
        assumed_channels = state.get("assumed_channels", [])
        
        if comp_str:
            indicators.append(f"Input completeness: {comp_str} sensor channels provided by operator ({', '.join(user_channels)}).")
        if assumed_channels:
            indicators.append(f"Assumed nominal baseline parameters: {', '.join(assumed_channels)}.")
        
        if not override_applied:
            summary = f"[Estimated Assessment: {comp_str or 'Partial'}] {summary}"

    state["primary_indicators"] = indicators
    state["condition_summary"] = summary
    return state


# ============================================================
# Graph Node 2: Risk Assessment
# ============================================================

def assess_risk(state: FPGAState) -> FPGAState:
    """Determine risk category and operational severity based on ML prediction & sensor anomalies."""
    health = state.get("health", "Healthy")
    temp = state.get("temperature", 35.0)
    error_rate = state.get("error_rate", 0.0)
    ro_freq_shift = state.get("ro_freq_shift_pct", 0.0)
    conf = state.get("confidence", 0.0)

    # Risk evaluation hierarchy
    if health == "Degraded" and (temp > 52.0 or error_rate > 0.0025 or ro_freq_shift < -6.0):
        risk = "CRITICAL"
    elif health == "Degraded":
        risk = "HIGH"
    elif health == "Warning" or temp > 48.0 or ro_freq_shift < -3.5:
        risk = "MODERATE"
    else:
        risk = "LOW"

    if conf < 0.70 and risk in ["HIGH", "CRITICAL"]:
        risk += " (LOW CONFIDENCE)"

    if state.get("is_estimated") and state.get("completeness_count", 6) <= 2:
        risk += " (PARTIAL TELEMETRY)"

    state["risk_level"] = risk
    return state


# ============================================================
# Graph Node 3: Recommendations & Life Extension Suggestions
# ============================================================

def formulate_recommendations(state: FPGAState) -> FPGAState:
    """Synthesize structured, actionable recommendations and life-extension guidance."""
    health = state.get("health", "Healthy")
    risk = state.get("risk_level", "LOW")
    temp = state.get("temperature", 35.0)
    error_rate = state.get("error_rate", 0.0)
    ro_freq_shift = state.get("ro_freq_shift_pct", 0.0)
    conf = state.get("confidence", 0.0)

    actions: Dict[str, str] = {}

    # 1. Thermal Actions
    if temp >= 50.0:
        actions["Thermal"] = (
            "Investigate elevated operating temperature immediately. Inspect cooling heatsink contact, "
            "verify chassis airflow, and reduce ambient thermal buildup."
        )
    elif temp >= 42.0:
        actions["Thermal"] = (
            "Monitor thermal dissipation trends and ensure adequate ventilation around the FPGA enclosure."
        )
    else:
        actions["Thermal"] = "Maintain current thermal cooling and ambient monitoring."

    # 2. Timing Actions
    if ro_freq_shift <= -4.0:
        actions["Timing"] = (
            "Review critical path timing margins in synthesis constraints. As gate propagation delay increases, "
            "timing slack diminishes; consider re-evaluating setup/hold margins."
        )
    elif ro_freq_shift <= -2.0:
        actions["Timing"] = "Track RO delay trends closely to detect any progressive timing degradation."
    else:
        actions["Timing"] = "Timing margins are nominal; continue standard periodic verification."

    # 3. Power Actions
    actions["Power"] = (
        "Verify internal supply rail stability (VCCINT, VCCAUX, VCCBRAM) using board power monitors or oscilloscope "
        "to ensure voltage ripple remains within manufacturer tolerances."
    )

    # 4. Reliability Actions
    if error_rate >= 0.001:
        actions["Reliability"] = (
            "Increase functional diagnostic test frequency to isolate any intermittent logic faults or memory bit flips."
        )
    else:
        actions["Reliability"] = "Routine diagnostic cycle frequency is sufficient."

    # 5. Predictive Maintenance Actions
    actions["Predictive Maintenance"] = (
        "Continue logging continuous telemetry to update aging trend models and capture longitudinal drift."
    )

    # Life Extension Engineering Suggestions (Non-guarantee, scientific phrasing)
    life_extension: Dict[str, List[str]] = {
        "Thermal Management": [
            "Improving active airflow and heatsink thermal interface may reduce junction temperature and slow thermal wear-out.",
            "Avoiding sustained operation near upper thermal boundaries can help mitigate Bias Temperature Instability (BTI).",
            "Ensuring clean ventilation in the chassis reduces hot-spot accumulation."
        ],
        "Voltage Stability": [
            "Maintaining core voltage (VCCINT) tightly regulated within specified limits reduces unnecessary dielectric stress.",
            "Mitigating excessive power-supply ripple can prevent accelerated gate-oxide wear."
        ],
        "Workload Management": [
            "Applying dynamic clock gating to inactive logic modules can reduce overall switching activity.",
            "Optimizing high-toggle netlists may lower dynamic power dissipation and local hot spots."
        ],
        "Timing Health": [
            "Re-evaluating timing constraints and slack margins helps prevent timing faults as logic gates age.",
            "Periodically tracking on-chip Ring Oscillator frequency provides an effective early indicator of propagation delay drift."
        ],
        "Functional Reliability": [
            "Conducting automated periodic diagnostic self-tests helps detect intermittent anomalies early.",
            "Verifying error-correction code (ECC) logs on Block RAM resources can capture single-event or aging upsets."
        ],
        "Predictive Maintenance": [
            "Comparing live sensor readings against initial healthy baseline establishes clear degradation trajectories.",
            "Setting early alert thresholds enables planned inspection before severe operational degradation occurs."
        ]
    }

    # Consolidated recommendation text
    rec_text = (
        f"AI Health Assessment: {health.upper()} | Risk Level: {risk}\n"
        f"• {state.get('condition_summary', '')}\n\n"
        f"Key Action: {actions.get('Thermal', '')} {actions.get('Timing', '')}"
    )

    if conf < 0.75:
        rec_text += " Note: Model prediction confidence is relatively low; collect additional telemetry frames."

    if state.get("is_estimated"):
        comp_str = state.get("completeness_str", "partial")
        rec_text += f"\n\n[Notice: Assessment derived from user-provided telemetry ({comp_str} channels). Unsupplied channels assumed nominal baseline.]"

    state["recommended_actions"] = actions
    state["life_extension_suggestions"] = life_extension
    state["recommendation"] = rec_text

    return state


# ============================================================
# Diagnostic Reasoning Pipeline
# ============================================================

class DiagnosticPipeline:
    """Sequential diagnostic reasoning and advisory pipeline."""

    @staticmethod
    def invoke(state: FPGAState) -> FPGAState:
        s = analyze_indicators(dict(state))
        s = assess_risk(s)
        return formulate_recommendations(s)


app = DiagnosticPipeline()


def evaluate_fpga_health(telemetry: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience helper to invoke the LangGraph agent on a telemetry dictionary."""
    state_input: FPGAState = {
        "health": str(telemetry.get("health", telemetry.get("final_health", telemetry.get("Predicted_Health", "Healthy")))),
        "confidence": float(telemetry.get("confidence", telemetry.get("ml_confidence", telemetry.get("Confidence", 0.95)))),
        "ml_prediction": str(telemetry.get("ml_prediction", telemetry.get("Predicted_Health", telemetry.get("health", "Healthy")))),
        "override_applied": bool(telemetry.get("override_applied", False)),
        "override_title": str(telemetry.get("override_title", "")),
        "override_explanation": str(telemetry.get("override_explanation", "")),
        "override_reasons": list(telemetry.get("override_reasons", [])),
        "engineering_assessment": dict(telemetry.get("engineering_assessment", {})),
        "temperature": float(telemetry.get("temperature", telemetry.get("Temperature", 35.0))),
        "vccint": float(telemetry.get("vccint", telemetry.get("VCCINT", 1.000))),
        "vccaux": float(telemetry.get("vccaux", telemetry.get("VCCAUX", 1.800))),
        "vccbram": float(telemetry.get("vccbram", telemetry.get("VCCBRAM", 1.000))),
        "ro_frequency": float(telemetry.get("ro_frequency", telemetry.get("RO_Frequency", 250.0))),
        "ro_delay": float(telemetry.get("ro_delay", telemetry.get("RO_Delay_ns", 0.4000))),
        "error_rate": float(telemetry.get("error_rate", telemetry.get("Error_Rate", 0.0))),
        "ro_freq_shift_pct": float(telemetry.get("ro_freq_shift_pct", 0.0)),
        "ro_delay_shift_pct": float(telemetry.get("ro_delay_shift_pct", 0.0)),
        "temp_shift": float(telemetry.get("temp_shift", 0.0)),
        "temp_trend": str(telemetry.get("temp_trend", "Stable")),
        "ro_freq_trend": str(telemetry.get("ro_freq_trend", "Stable")),
        "error_trend": str(telemetry.get("error_trend", "Stable")),
        "source": str(telemetry.get("source", telemetry.get("source_type", "LIVE"))),
        "completeness_str": str(telemetry.get("completeness_str", "")),
        "completeness_count": int(telemetry.get("completeness_count", 6)),
        "reliability_score": float(telemetry.get("reliability_score", 1.0)),
        "user_provided_channels": list(telemetry.get("user_provided", telemetry.get("user_provided_channels", []))),
        "assumed_channels": list(telemetry.get("assumed", telemetry.get("assumed_channels", []))),
        "is_estimated": bool(telemetry.get("is_estimated", telemetry.get("source_type") == "ESTIMATED")),
    }
    return app.invoke(state_input)


if __name__ == "__main__":
    sample_state = {
        "health": "Warning",
        "confidence": 0.91,
        "temperature": 48.5,
        "vccint": 0.992,
        "vccaux": 1.792,
        "vccbram": 0.994,
        "ro_frequency": 241.2,
        "ro_delay": 0.4146,
        "error_rate": 0.0015,
        "ro_freq_shift_pct": -3.52,
        "ro_delay_shift_pct": 3.65,
        "temp_shift": 13.5,
        "temp_trend": "Increasing",
        "ro_freq_trend": "Decreasing",
        "error_trend": "Increasing"
    }

    result = app.invoke(sample_state)
    print("\n--- AI Agent Health Assessment ---")
    print("Risk Level:", result["risk_level"])
    print("Condition Summary:", result["condition_summary"])
    print("\nPrimary Indicators:")
    for ind in result["primary_indicators"]:
        print(" •", ind)
    print("\nRecommended Actions:")
    for cat, action in result["recommended_actions"].items():
        print(f" [{cat}]: {action}")