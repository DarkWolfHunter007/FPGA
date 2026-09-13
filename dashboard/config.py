"""
Configuration Constants, Sensor Thresholds & Engineering Limit Architecture
============================================================================
Centralizes all physical operating limits, nominal ratings, threshold rules,
and the three-tier validation architecture:
  1. Input Validity (Syntactic / Numeric)
  2. Physical Validity (Sensor Hardware Plausibility)
  3. Operating Health Range (FPGA Engineering Safety Boundaries)

Precedence Rule:
  Hard engineering limit violations OVERRIDE the Random Forest ML prediction.
"""

from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
from config import RO_STAGES, calculate_ro_delay_ns, validate_ro_delay, DEVICE_NAME, ARCHITECTURE


# =============================================================================
# Validation & Severity Enumerations
# =============================================================================
class LimitSeverity(str, Enum):
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    PHYSICALLY_INVALID = "PHYSICALLY_INVALID"


class ValidationStatus(str, Enum):
    VALID = "VALID"
    INVALID_INPUT = "INVALID_INPUT"
    PHYSICALLY_INVALID = "PHYSICALLY_INVALID"
    OUTSIDE_OPERATING_RANGE = "OUTSIDE_OPERATING_RANGE"


# =============================================================================
# Centralized Sensor Configuration & Comprehensive Limits
# =============================================================================
# Schema for every telemetry channel:
#   - display_name: Human-readable sensor channel title
#   - unit: Physical engineering unit
#   - nominal: Verified baseline benchmark
#   - description: Physical meaning & mechanism
#   - physical_min / physical_max: Absolute hardware/sensor physical plausibility bounds
#   - operating_min / operating_max: Expected normal/healthy operating envelope
#   - warning_low / warning_high: Boundaries triggering Warning state
#   - critical_low / critical_high: Boundaries triggering Critical/Degraded state
#   - is_hard_override: True if violation takes precedence over ML model
#   - source: Provenance of the limit (Datasheet, Aging model, or Configurable assumption)
# =============================================================================
SENSOR_CONFIG: Dict[str, Dict[str, Any]] = {
    "Temperature": {
        "display_name": "Die Temperature",
        "unit": "°C",
        "nominal": 35.0,
        "description": "On-chip junction temperature measured by 7-Series XADC sensor",
        "physical_min": -40.0,    # Xilinx DS181 minimum junction rating
        "physical_max": 125.0,    # Xilinx DS181 maximum junction rating
        "operating_min": 20.0,    # Normal commercial room/chassis operating floor
        "operating_max": 45.0,    # Upper threshold for nominal healthy operation
        "warning_low": 10.0,      # Sub-nominal operating ambient
        "warning_high": 45.0,     # Elevated thermal dissipation
        "critical_low": 0.0,      # Hard limit: abnormal refrigeration / sensor fault
        "critical_high": 52.0,    # Hard limit: severe thermal stress / accelerated aging
        "is_hard_override": True,
        "source": "Xilinx DS181 Datasheet & Thermal Aging Benchmark",
        # Backward compatibility aliases
        "warning": 45.0,
        "critical": 52.0,
        "min_valid": -40.0,
        "max_valid": 125.0
    },
    "VCCINT": {
        "display_name": "VCCINT (Core Supply)",
        "unit": "V",
        "nominal": 1.000,
        "description": "Internal FPGA core logic supply rail",
        "physical_min": 0.000,
        "physical_max": 2.000,
        "operating_min": 0.950,   # Xilinx DS181 recommended 1.0V ± 50mV (±5%)
        "operating_max": 1.050,
        "warning_low": 0.920,     # Supply voltage droop
        "warning_high": 1.050,    # Supply voltage surge
        "critical_low": 0.920,    # Hard limit: severe droop / logic failure risk
        "critical_high": 1.080,   # Hard limit: overvoltage / oxide breakdown risk
        "is_hard_override": True,
        "source": "Xilinx DS181 Artix-7 Recommended Operating Conditions (1.0V ± 5%)",
        # Backward compatibility aliases
        "tolerance_pct": 2.5,
        "min_nominal": 0.975,
        "max_nominal": 1.025,
        "min_valid": 0.5,
        "max_valid": 1.5
    },
    "VCCAUX": {
        "display_name": "VCCAUX (Auxiliary Supply)",
        "unit": "V",
        "nominal": 1.800,
        "description": "Auxiliary supply rail powering I/O circuitry and XADC reference",
        "physical_min": 0.000,
        "physical_max": 3.000,
        "operating_min": 1.710,   # Xilinx DS181 recommended 1.8V ± 5%
        "operating_max": 1.890,
        "warning_low": 1.650,
        "warning_high": 1.890,
        "critical_low": 1.650,    # Hard limit: severe aux droop
        "critical_high": 1.950,   # Hard limit: aux overvoltage
        "is_hard_override": True,
        "source": "Xilinx DS181 Artix-7 Recommended Operating Conditions (1.8V ± 5%)",
        # Backward compatibility aliases
        "tolerance_pct": 2.5,
        "min_nominal": 1.755,
        "max_nominal": 1.845,
        "min_valid": 1.0,
        "max_valid": 2.5
    },
    "VCCBRAM": {
        "display_name": "VCCBRAM (BRAM Supply)",
        "unit": "V",
        "nominal": 1.000,
        "description": "Dedicated supply rail for on-chip Block RAM cells",
        "physical_min": 0.000,
        "physical_max": 2.000,
        "operating_min": 0.950,   # Xilinx DS181 recommended 1.0V ± 5%
        "operating_max": 1.050,
        "warning_low": 0.920,
        "warning_high": 1.050,
        "critical_low": 0.920,    # Hard limit: BRAM memory data corruption risk
        "critical_high": 1.080,   # Hard limit: BRAM overvoltage
        "is_hard_override": True,
        "source": "Xilinx DS181 Artix-7 Recommended Operating Conditions (1.0V ± 5%)",
        # Backward compatibility aliases
        "tolerance_pct": 2.5,
        "min_nominal": 0.975,
        "max_nominal": 1.025,
        "min_valid": 0.5,
        "max_valid": 1.5
    },
    "RO_Frequency": {
        "display_name": "Ring Oscillator Frequency",
        "unit": "MHz",
        "nominal": 250.0,
        "description": "5-stage Ring Oscillator frequency tracking logic gate propagation delay",
        "physical_min": 10.0,
        "physical_max": 500.0,
        "operating_min": 245.0,   # Nominal healthy oscillation envelope
        "operating_max": 255.0,
        "warning_low": 238.0,     # Moderate timing degradation (drop > 2.8%)
        "warning_high": 258.0,    # Slight unexpected overclock
        "critical_low": 238.0,    # Hard limit: severe aging / NBTI slowing (drop > 4.8%)
        "critical_high": 265.0,   # Hard limit: abnormal over-frequency / clock fault
        "is_hard_override": True,
        "source": "Project 28nm BTI/HCI Aging Degradation Model",
        # Backward compatibility aliases
        "warning_drop_pct": 3.0,
        "critical_drop_pct": 5.5,
        "min_valid": 50.0,
        "max_valid": 400.0
    },
    "RO_Delay_ns": {
        "display_name": "Derived RO Stage Delay",
        "unit": "ns",
        "nominal": 0.4000,
        "description": "Derived logic propagation delay per inverter stage (tau = 100 / f_MHz)",
        "physical_min": 0.10,
        "physical_max": 2.50,
        "operating_min": 0.3920,  # Corresponds to 255 MHz
        "operating_max": 0.4082,  # Corresponds to 245 MHz
        "warning_low": 0.3876,
        "warning_high": 0.4202,   # Corresponds to 238 MHz
        "critical_low": 0.3770,   # Hard limit: impossible fast gate delay
        "critical_high": 0.4202,  # Hard limit: severe delay increase > 5.0%
        "is_hard_override": True,
        "source": "Deterministic Physical Formula (tau = 1000 / 2*N*f for N=5 stages)",
        # Backward compatibility aliases
        "warning_increase_pct": 3.0,
        "critical_increase_pct": 6.0,
        "min_valid": 0.10,
        "max_valid": 2.50
    },
    "Error_Rate": {
        "display_name": "Functional Error Rate",
        "unit": "",
        "nominal": 0.000010,
        "description": "Hardware PRBS-7 self-checking logic bit error rate",
        "physical_min": 0.0,
        "physical_max": 1.0,
        "operating_min": 0.0,
        "operating_max": 0.000500, # Negligible soft error noise floor
        "warning_low": 0.0,
        "warning_high": 0.002000,  # Elevated soft error activity
        "critical_low": 0.0,
        "critical_high": 0.002000, # Hard limit: operational functional breakdown
        "is_hard_override": True,
        "source": "Hardware PRBS-7 Self-Test Specification (Configurable Engineering Assumption)",
        # Backward compatibility aliases
        "warning": 0.0010,
        "critical": 0.0025,
        "min_valid": 0.0,
        "max_valid": 1.0
    }
}


# =============================================================================
# Health State Color Palette
# =============================================================================
HEALTH_COLORS = {
    "Healthy": "#00E676",    # Vivid Green
    "Warning": "#FFD600",    # Amber Yellow
    "Degraded": "#FF9100",   # High-Visibility Orange
    "Critical": "#FF1744"    # Bright Red
}

STATUS_BG_COLORS = {
    "Healthy": "rgba(0, 230, 118, 0.12)",
    "Warning": "rgba(255, 214, 0, 0.12)",
    "Degraded": "rgba(255, 145, 0, 0.14)",
    "Critical": "rgba(255, 23, 68, 0.16)"
}


# =============================================================================
# Channel Evaluation & Engineering Limit Assessment Engine
# =============================================================================
class ChannelEvaluation:
    """Detailed evaluation record for a single sensor telemetry channel."""

    def __init__(
        self,
        channel: str,
        value: float,
        display_name: str,
        unit: str,
        nominal: float,
        operating_range_str: str,
        severity: LimitSeverity,
        status_label: str,
        is_violation: bool,
        is_hard_override: bool,
        reason: Optional[str] = None,
        provenance: str = "MEASURED"
    ):
        self.channel = channel
        self.value = value
        self.display_name = display_name
        self.unit = unit
        self.nominal = nominal
        self.operating_range_str = operating_range_str
        self.severity = severity
        self.status_label = status_label
        self.is_violation = is_violation
        self.is_hard_override = is_hard_override
        self.reason = reason
        self.provenance = provenance

    def to_dict(self) -> Dict[str, Any]:
        return {
            "channel": self.channel,
            "value": self.value,
            "display_name": self.display_name,
            "unit": self.unit,
            "nominal": self.nominal,
            "operating_range": self.operating_range_str,
            "severity": self.severity.value,
            "status": self.status_label,
            "is_violation": self.is_violation,
            "is_hard_override": self.is_hard_override,
            "reason": self.reason,
            "provenance": self.provenance
        }


def evaluate_single_channel(
    channel: str,
    value: Any,
    provenance: str = "MEASURED"
) -> ChannelEvaluation:
    """
    Evaluates a telemetry channel against the three-tier validation architecture:
      1. Input Validity
      2. Physical Validity
      3. Operating Health Range
    """
    cfg = SENSOR_CONFIG.get(channel)
    if not cfg:
        return ChannelEvaluation(
            channel=channel,
            value=0.0,
            display_name=channel,
            unit="",
            nominal=0.0,
            operating_range_str="N/A",
            severity=LimitSeverity.NORMAL,
            status_label="UNKNOWN",
            is_violation=False,
            is_hard_override=False,
            provenance=provenance
        )

    disp = cfg["display_name"]
    unit = cfg["unit"]
    nom = cfg["nominal"]
    op_min = cfg["operating_min"]
    op_max = cfg["operating_max"]
    op_str = f"{op_min:.2f} – {op_max:.2f} {unit}".strip()

    # --- 1. Input Validity Check ---
    try:
        val_float = float(value)
    except (ValueError, TypeError):
        return ChannelEvaluation(
            channel=channel,
            value=0.0,
            display_name=disp,
            unit=unit,
            nominal=nom,
            operating_range_str=op_str,
            severity=LimitSeverity.PHYSICALLY_INVALID,
            status_label="INVALID INPUT",
            is_violation=True,
            is_hard_override=True,
            reason=f"{disp} is not a valid numeric value ('{value}').",
            provenance=provenance
        )

    # --- 2. Physical Sensor Validity Check ---
    phys_min = cfg["physical_min"]
    phys_max = cfg["physical_max"]
    if not (phys_min <= val_float <= phys_max):
        return ChannelEvaluation(
            channel=channel,
            value=val_float,
            display_name=disp,
            unit=unit,
            nominal=nom,
            operating_range_str=op_str,
            severity=LimitSeverity.PHYSICALLY_INVALID,
            status_label="PHYSICALLY IMPOSSIBLE",
            is_violation=True,
            is_hard_override=True,
            reason=f"{disp} ({val_float} {unit}) exceeds absolute physical limits [{phys_min}, {phys_max}].",
            provenance=provenance
        )

    # --- 3. Operating Health Range & Hard Limits Check ---
    crit_low = cfg["critical_low"]
    crit_high = cfg["critical_high"]
    warn_low = cfg["warning_low"]
    warn_high = cfg["warning_high"]

    # Critical Conditions (e.g. Temp <= 0.0 or Temp >= 52.0, VCCINT < 0.92, RO < 238, Error > 0.002)
    if channel == "Temperature":
        if val_float <= crit_low:
            return ChannelEvaluation(
                channel=channel,
                value=val_float,
                display_name=disp,
                unit=unit,
                nominal=nom,
                operating_range_str=op_str,
                severity=LimitSeverity.CRITICAL,
                status_label="CRITICAL (SUB-ZERO / FREEZE FAULT)",
                is_violation=True,
                is_hard_override=True,
                reason=f"Temperature ({val_float:.1f}°C) is at or below 0°C (abnormal refrigeration / sensor fault, expected {op_str}).",
                provenance=provenance
            )
        elif val_float >= crit_high:
            return ChannelEvaluation(
                channel=channel,
                value=val_float,
                display_name=disp,
                unit=unit,
                nominal=nom,
                operating_range_str=op_str,
                severity=LimitSeverity.CRITICAL,
                status_label="CRITICAL (SEVERE THERMAL STRESS)",
                is_violation=True,
                is_hard_override=True,
                reason=f"Temperature ({val_float:.1f}°C) exceeds critical thermal threshold {crit_high}°C.",
                provenance=provenance
            )
        elif val_float >= warn_high:
            return ChannelEvaluation(
                channel=channel,
                value=val_float,
                display_name=disp,
                unit=unit,
                nominal=nom,
                operating_range_str=op_str,
                severity=LimitSeverity.WARNING,
                status_label="WARNING (ELEVATED TEMPERATURE)",
                is_violation=True,
                is_hard_override=True,
                reason=f"Temperature ({val_float:.1f}°C) exceeds nominal operating range {op_str}.",
                provenance=provenance
            )
        elif val_float < warn_low:
            return ChannelEvaluation(
                channel=channel,
                value=val_float,
                display_name=disp,
                unit=unit,
                nominal=nom,
                operating_range_str=op_str,
                severity=LimitSeverity.WARNING,
                status_label="WARNING (SUB-NOMINAL AMBIENT)",
                is_violation=True,
                is_hard_override=True,
                reason=f"Temperature ({val_float:.1f}°C) is below standard operating ambient {op_str}.",
                provenance=provenance
            )

    elif channel in ("VCCINT", "VCCAUX", "VCCBRAM"):
        if val_float <= crit_low:
            return ChannelEvaluation(
                channel=channel,
                value=val_float,
                display_name=disp,
                unit=unit,
                nominal=nom,
                operating_range_str=op_str,
                severity=LimitSeverity.CRITICAL,
                status_label="CRITICAL (VOLTAGE DROOP)",
                is_violation=True,
                is_hard_override=True,
                reason=f"{disp} ({val_float:.3f}V) dropped below critical threshold {crit_low:.3f}V.",
                provenance=provenance
            )
        elif val_float >= crit_high:
            return ChannelEvaluation(
                channel=channel,
                value=val_float,
                display_name=disp,
                unit=unit,
                nominal=nom,
                operating_range_str=op_str,
                severity=LimitSeverity.CRITICAL,
                status_label="CRITICAL (OVERVOLTAGE)",
                is_violation=True,
                is_hard_override=True,
                reason=f"{disp} ({val_float:.3f}V) exceeds maximum safe voltage {crit_high:.3f}V.",
                provenance=provenance
            )
        elif val_float < op_min or val_float > op_max:
            return ChannelEvaluation(
                channel=channel,
                value=val_float,
                display_name=disp,
                unit=unit,
                nominal=nom,
                operating_range_str=op_str,
                severity=LimitSeverity.WARNING,
                status_label="WARNING (OUT OF TOLERANCE)",
                is_violation=True,
                is_hard_override=True,
                reason=f"{disp} ({val_float:.3f}V) is outside recommended operating tolerance {op_str}.",
                provenance=provenance
            )

    elif channel == "RO_Frequency":
        if val_float <= crit_low:
            return ChannelEvaluation(
                channel=channel,
                value=val_float,
                display_name=disp,
                unit=unit,
                nominal=nom,
                operating_range_str=op_str,
                severity=LimitSeverity.CRITICAL,
                status_label="CRITICAL (SEVERE TIMING DEGRADATION)",
                is_violation=True,
                is_hard_override=True,
                reason=f"RO Frequency ({val_float:.1f} MHz) slowed past critical boundary {crit_low:.1f} MHz.",
                provenance=provenance
            )
        elif val_float >= crit_high:
            return ChannelEvaluation(
                channel=channel,
                value=val_float,
                display_name=disp,
                unit=unit,
                nominal=nom,
                operating_range_str=op_str,
                severity=LimitSeverity.CRITICAL,
                status_label="CRITICAL (ABNORMAL OVER-FREQUENCY)",
                is_violation=True,
                is_hard_override=True,
                reason=f"RO Frequency ({val_float:.1f} MHz) abnormally high (expected {op_str}).",
                provenance=provenance
            )
        elif val_float < op_min:
            return ChannelEvaluation(
                channel=channel,
                value=val_float,
                display_name=disp,
                unit=unit,
                nominal=nom,
                operating_range_str=op_str,
                severity=LimitSeverity.WARNING,
                status_label="WARNING (TIMING DELAY DRIFT)",
                is_violation=True,
                is_hard_override=True,
                reason=f"RO Frequency ({val_float:.1f} MHz) shows measurable timing degradation from nominal {nom:.1f} MHz.",
                provenance=provenance
            )

    elif channel == "RO_Delay_ns":
        if val_float >= crit_high:
            return ChannelEvaluation(
                channel=channel,
                value=val_float,
                display_name=disp,
                unit=unit,
                nominal=nom,
                operating_range_str=op_str,
                severity=LimitSeverity.CRITICAL,
                status_label="CRITICAL (PROPAGATION DELAY SLOWED)",
                is_violation=True,
                is_hard_override=True,
                reason=f"Derived stage delay ({val_float:.4f} ns) exceeds critical timing margin {crit_high:.4f} ns.",
                provenance=provenance
            )
        elif val_float > op_max:
            return ChannelEvaluation(
                channel=channel,
                value=val_float,
                display_name=disp,
                unit=unit,
                nominal=nom,
                operating_range_str=op_str,
                severity=LimitSeverity.WARNING,
                status_label="WARNING (TIMING MARGIN REDUCTION)",
                is_violation=True,
                is_hard_override=True,
                reason=f"Derived stage delay ({val_float:.4f} ns) is elevated above nominal {nom:.4f} ns.",
                provenance=provenance
            )

    elif channel == "Error_Rate":
        if val_float >= crit_high:
            return ChannelEvaluation(
                channel=channel,
                value=val_float,
                display_name=disp,
                unit=unit,
                nominal=nom,
                operating_range_str=op_str,
                severity=LimitSeverity.CRITICAL,
                status_label="CRITICAL (HIGH ERROR RATE)",
                is_violation=True,
                is_hard_override=True,
                reason=f"Functional Error Rate ({val_float:.6f}) exceeds critical limit {crit_high:.6f}.",
                provenance=provenance
            )
        elif val_float > op_max:
            return ChannelEvaluation(
                channel=channel,
                value=val_float,
                display_name=disp,
                unit=unit,
                nominal=nom,
                operating_range_str=op_str,
                severity=LimitSeverity.WARNING,
                status_label="WARNING (ELEVATED ERROR RATE)",
                is_violation=True,
                is_hard_override=True,
                reason=f"Functional Error Rate ({val_float:.6f}) is elevated above normal floor {op_max:.6f}.",
                provenance=provenance
            )

    # Nominal healthy condition
    return ChannelEvaluation(
        channel=channel,
        value=val_float,
        display_name=disp,
        unit=unit,
        nominal=nom,
        operating_range_str=op_str,
        severity=LimitSeverity.NORMAL,
        status_label="NORMAL",
        is_violation=False,
        is_hard_override=False,
        provenance=provenance
    )


class EngineeringAssessment:
    """Comprehensive engineering assessment aggregating all sensor limit checks."""

    def __init__(
        self,
        is_input_valid: bool,
        is_physically_valid: bool,
        has_hard_violations: bool,
        max_severity: LimitSeverity,
        override_reasons: List[str],
        channel_evaluations: Dict[str, ChannelEvaluation]
    ):
        self.is_input_valid = is_input_valid
        self.is_physically_valid = is_physically_valid
        self.has_hard_violations = has_hard_violations
        self.max_severity = max_severity
        self.override_reasons = override_reasons
        self.channel_evaluations = channel_evaluations
        self.has_critical = (max_severity in (LimitSeverity.CRITICAL, LimitSeverity.PHYSICALLY_INVALID))
        self.has_warning = (max_severity == LimitSeverity.WARNING)

    def __getitem__(self, item: str) -> Any:
        mapping = {
            "is_input_valid": self.is_input_valid,
            "is_physically_valid": self.is_physically_valid,
            "has_hard_violations": self.has_hard_violations,
            "has_critical": self.has_critical,
            "has_warning": self.has_warning,
            "max_severity": self.max_severity,
            "override_reasons": self.override_reasons,
            "reasons": self.override_reasons,
            "channel_evaluations": self.channel_evaluations,
            "evaluations": self.channel_evaluations,
            "channels": {k: v.to_dict() for k, v in self.channel_evaluations.items()}
        }
        if item in mapping:
            return mapping[item]
        raise KeyError(f"EngineeringAssessment has no key '{item}'")

    def get(self, item: str, default: Any = None) -> Any:
        try:
            return self[item]
        except KeyError:
            return default

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_input_valid": self.is_input_valid,
            "is_physically_valid": self.is_physically_valid,
            "has_hard_violations": self.has_hard_violations,
            "has_critical": self.has_critical,
            "has_warning": self.has_warning,
            "max_severity": self.max_severity.value,
            "override_reasons": self.override_reasons,
            "reasons": self.override_reasons,
            "channels": {k: v.to_dict() for k, v in self.channel_evaluations.items()},
            "evaluations": {k: v.to_dict() for k, v in self.channel_evaluations.items()}
        }


def evaluate_engineering_limits(
    telemetry: Dict[str, Any],
    provenance_map: Optional[Dict[str, str]] = None
) -> EngineeringAssessment:
    """
    Evaluates a full telemetry record against all centralized engineering boundaries.
    """
    provenance_map = provenance_map or {}
    evals: Dict[str, ChannelEvaluation] = {}
    reasons: List[str] = []
    max_sev = LimitSeverity.NORMAL
    is_input_valid = True
    is_phys_valid = True
    has_hard_viol = False

    channels = ["Temperature", "VCCINT", "VCCAUX", "VCCBRAM", "RO_Frequency", "RO_Delay_ns", "Error_Rate"]

    for ch in channels:
        if ch in telemetry:
            val = telemetry[ch]
            prov = provenance_map.get(ch, "MEASURED")
            eval_res = evaluate_single_channel(ch, val, provenance=prov)
            evals[ch] = eval_res

            if eval_res.severity == LimitSeverity.PHYSICALLY_INVALID:
                is_phys_valid = False
                is_input_valid = False
                max_sev = LimitSeverity.PHYSICALLY_INVALID
                if eval_res.reason:
                    reasons.append(eval_res.reason)
            elif eval_res.severity == LimitSeverity.CRITICAL:
                if max_sev != LimitSeverity.PHYSICALLY_INVALID:
                    max_sev = LimitSeverity.CRITICAL
                has_hard_viol = True
                if eval_res.reason:
                    reasons.append(eval_res.reason)
            elif eval_res.severity == LimitSeverity.WARNING:
                if max_sev == LimitSeverity.NORMAL:
                    max_sev = LimitSeverity.WARNING
                has_hard_viol = True
                if eval_res.reason:
                    reasons.append(eval_res.reason)

    return EngineeringAssessment(
        is_input_valid=is_input_valid,
        is_physically_valid=is_phys_valid,
        has_hard_violations=has_hard_viol,
        max_severity=max_sev,
        override_reasons=reasons,
        channel_evaluations=evals
    )


def determine_final_health(
    ml_prediction: str,
    ml_confidence: float,
    engineering_assessment: Any
) -> Dict[str, Any]:
    """
    Combines Random Forest ML prediction with Engineering Limit Assessment.
    If hard limits are breached, engineering safety overrides ML prediction.

    Precedence:
      1. Physically Invalid -> Final: 'Degraded' / Critical, Override: True
      2. Critical Operating Breach -> Final: 'Degraded' / Critical, Override: True (if ML != Degraded)
      3. Warning Operating Breach -> Final: 'Warning' (if ML == Healthy), Override: True
      4. Normal -> Final: ML Prediction, Override: False
    """
    ml_pred_clean = str(ml_prediction).strip()
    override_applied = False
    override_title = ""
    override_explanation = ""
    final_health = ml_pred_clean

    if isinstance(engineering_assessment, dict):
        max_sev_val = engineering_assessment.get("max_severity", "NORMAL")
        if isinstance(max_sev_val, LimitSeverity):
            max_sev = max_sev_val
        else:
            try:
                max_sev = LimitSeverity(max_sev_val)
            except Exception:
                max_sev = LimitSeverity.NORMAL
        reasons = engineering_assessment.get("override_reasons") or engineering_assessment.get("reasons", [])
        evals = engineering_assessment.get("evaluations") or engineering_assessment.get("channel_evaluations", {})
        eng_dict = engineering_assessment
    else:
        max_sev = engineering_assessment.max_severity
        reasons = engineering_assessment.override_reasons
        evals = engineering_assessment.channel_evaluations
        eng_dict = engineering_assessment.to_dict()

    if max_sev == LimitSeverity.PHYSICALLY_INVALID:
        final_health = "Degraded"
        override_applied = True
        override_title = "CRITICAL — PHYSICAL VALIDITY OVERRIDE"
        override_explanation = (
            f"Telemetry values violate physical sensor limits ({'; '.join(reasons)}). "
            f"The Random Forest predicted '{ml_pred_clean}' ({ml_confidence * 100:.1f}%), "
            "but physical sensor validity takes absolute precedence."
        )

    elif max_sev == LimitSeverity.CRITICAL:
        final_health = "Degraded"
        if ml_pred_clean != "Degraded":
            override_applied = True
            override_title = "CRITICAL — HARD OPERATING LIMIT OVERRIDE"
            override_explanation = (
                f"Hard engineering safety constraints violated ({'; '.join(reasons)}). "
                f"The Random Forest predicted '{ml_pred_clean}' ({ml_confidence * 100:.1f}%), "
                "but engineering operating limits take precedence."
            )

    elif max_sev == LimitSeverity.WARNING:
        if ml_pred_clean == "Healthy":
            final_health = "Warning"
            override_applied = True
            override_title = "WARNING — OPERATING THRESHOLD OVERRIDE"
            override_explanation = (
                f"Sensor telemetry breached normal operating range ({'; '.join(reasons)}). "
                f"The Random Forest predicted '{ml_pred_clean}' ({ml_confidence * 100:.1f}%), "
                "which has been elevated to Warning based on engineering constraints."
            )

    return {
        "ml_prediction": ml_pred_clean,
        "ml_confidence": float(ml_confidence),
        "confidence": float(ml_confidence),
        "final_health": final_health,
        "override_applied": override_applied,
        "override_title": override_title,
        "override_explanation": override_explanation,
        "override_reasons": reasons,
        "reasons": reasons,
        "evaluations": evals,
        "engineering_assessment": eng_dict
    }
