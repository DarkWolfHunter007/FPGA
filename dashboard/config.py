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
from config import (
    RO_STAGES,
    calculate_ro_delay_ns,
    validate_ro_delay,
    DEVICE_NAME,
    ARCHITECTURE,
    RO_NOMINAL_MHZ,
    RO_NOMINAL_DELAY_NS,
    RO_FREQ_NOMINAL_MHZ,
    RO_FREQ_OPERATING_MIN_MHZ,
    RO_FREQ_OPERATING_MAX_MHZ,
    RO_FREQ_WARNING_LOW_MHZ,
    RO_FREQ_WARNING_HIGH_MHZ,
    RO_FREQ_CRITICAL_LOW_MHZ,
    RO_FREQ_CRITICAL_HIGH_MHZ,
    RO_DELAY_NOMINAL_NS,
    RO_DELAY_OPERATING_MIN_NS,
    RO_DELAY_OPERATING_MAX_NS,
    RO_DELAY_WARNING_LOW_NS,
    RO_DELAY_WARNING_HIGH_NS,
    RO_DELAY_CRITICAL_LOW_NS,
    RO_DELAY_CRITICAL_HIGH_NS
)


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
        "nominal": RO_FREQ_NOMINAL_MHZ,
        "description": "5-stage Ring Oscillator frequency tracking logic gate propagation delay (canonical timing metric)",
        "physical_min": 10.0,
        "physical_max": 800.0,
        "operating_min": RO_FREQ_OPERATING_MIN_MHZ,
        "operating_max": RO_FREQ_OPERATING_MAX_MHZ,
        "warning_low": RO_FREQ_WARNING_LOW_MHZ,
        "warning_high": RO_FREQ_WARNING_HIGH_MHZ,
        "critical_low": RO_FREQ_CRITICAL_LOW_MHZ,
        "critical_high": RO_FREQ_CRITICAL_HIGH_MHZ,
        "is_hard_override": True,
        "is_derived": False,
        "source": "Basys 3 Physical Measurement & 28nm Artix-7 Propagation Model",
        # Backward compatibility aliases
        "warning_drop_pct": 3.0,
        "critical_drop_pct": 5.5,
        "min_valid": 50.0,
        "max_valid": 800.0
    },
    "RO_Delay_ns": {
        "display_name": "Derived RO Stage Delay",
        "unit": "ns",
        "nominal": RO_DELAY_NOMINAL_NS,
        "description": "Derived logic propagation delay per inverter stage (tau = 100 / f_MHz, derived from RO frequency)",
        "physical_min": 0.05,
        "physical_max": 2.50,
        "operating_min": RO_DELAY_OPERATING_MIN_NS,
        "operating_max": RO_DELAY_OPERATING_MAX_NS,
        "warning_low": RO_DELAY_WARNING_LOW_NS,
        "warning_high": RO_DELAY_WARNING_HIGH_NS,
        "critical_low": RO_DELAY_CRITICAL_LOW_NS,
        "critical_high": RO_DELAY_CRITICAL_HIGH_NS,
        "is_hard_override": False,  # Delay is deterministically derived from RO_Frequency; RO_Frequency is canonical hard override
        "is_derived": True,
        "source": "Deterministic Physical Formula (tau = 100 / f_MHz derived from RO Frequency)",
        # Backward compatibility aliases
        "warning_increase_pct": 3.0,
        "critical_increase_pct": 5.5,
        "min_valid": 0.05,
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
# Four-Region Physical Health Configuration (Basys 3 XC7A35T)
# =============================================================================
# Physical 2x2 Layout:
#   R1 (Northwest): CLOCKREGION_X0Y2 -> SLICE_X0Y100:SLICE_X35Y149 (pblock_R1)
#   R2 (Northeast): CLOCKREGION_X1Y2 -> SLICE_X36Y100:SLICE_X57Y149 (pblock_R2)
#   R3 (Southwest): CLOCKREGION_X0Y0 -> SLICE_X0Y0:SLICE_X35Y49    (pblock_R3)
#   R4 (Southeast): CLOCKREGION_X1Y0 -> SLICE_X36Y0:SLICE_X65Y49    (pblock_R4)
# =============================================================================
REGIONAL_CONFIG: Dict[str, Dict[str, Any]] = {
    "R1": {
        "id": "R1",
        "name": "Region 1 (R1)",
        "quadrant": "Northwest (NW)",
        "clock_region": "X0Y2",
        "pblock": "pblock_R1",
        "slice_range": "SLICE_X0Y100:SLICE_X35Y149",
        "nominal_freq": 436.3,       # Measured initial physical baseline for R1
        "nominal_delay_ns": 0.2292,  # 100 / 436.3
        "warning_drop_pct": 3.0,
        "critical_drop_pct": 5.5,
        "warning_freq": 423.2,       # 436.3 * 0.970
        "warning_delay_ns": 0.2363,  # 100 / 423.2
        "critical_freq": 412.3,      # 436.3 * 0.945
        "critical_delay_ns": 0.2425, # 100 / 412.3
        "description": "Monitors logic timing propagation in Northwest silicon quadrant"
    },
    "R2": {
        "id": "R2",
        "name": "Region 2 (R2)",
        "quadrant": "Northeast (NE)",
        "clock_region": "X1Y2",
        "pblock": "pblock_R2",
        "slice_range": "SLICE_X36Y100:SLICE_X57Y149",
        "nominal_freq": 435.8,       # Measured initial physical baseline for R2
        "nominal_delay_ns": 0.2295,  # 100 / 435.8
        "warning_drop_pct": 3.0,
        "critical_drop_pct": 5.5,
        "warning_freq": 422.7,       # 435.8 * 0.970
        "warning_delay_ns": 0.2366,  # 100 / 422.7
        "critical_freq": 411.8,      # 435.8 * 0.945
        "critical_delay_ns": 0.2428, # 100 / 411.8
        "description": "Monitors logic timing propagation in Northeast silicon quadrant"
    },
    "R3": {
        "id": "R3",
        "name": "Region 3 (R3)",
        "quadrant": "Southwest (SW)",
        "clock_region": "X0Y0",
        "pblock": "pblock_R3",
        "slice_range": "SLICE_X0Y0:SLICE_X35Y49",
        "nominal_freq": 436.1,       # Measured initial physical baseline for R3
        "nominal_delay_ns": 0.2293,  # 100 / 436.1
        "warning_drop_pct": 3.0,
        "critical_drop_pct": 5.5,
        "warning_freq": 423.0,       # 436.1 * 0.970
        "warning_delay_ns": 0.2364,  # 100 / 423.0
        "critical_freq": 412.1,      # 436.1 * 0.945
        "critical_delay_ns": 0.2427, # 100 / 412.1
        "description": "Monitors logic timing propagation in Southwest silicon quadrant"
    },
    "R4": {
        "id": "R4",
        "name": "Region 4 (R4)",
        "quadrant": "Southeast (SE)",
        "clock_region": "X1Y0",
        "pblock": "pblock_R4",
        "slice_range": "SLICE_X36Y0:SLICE_X65Y49",
        "nominal_freq": 435.9,       # Measured initial physical baseline for R4
        "nominal_delay_ns": 0.2294,  # 100 / 435.9
        "warning_drop_pct": 3.0,
        "critical_drop_pct": 5.5,
        "warning_freq": 422.8,       # 435.9 * 0.970
        "warning_delay_ns": 0.2365,  # 100 / 422.8
        "critical_freq": 411.9,      # 435.9 * 0.945
        "critical_delay_ns": 0.2428, # 100 / 411.9
        "description": "Monitors logic timing propagation in Southeast silicon quadrant"
    }
}


def get_error_risk_label(error_rate: float) -> Tuple[str, str, str]:

    """
    Independent classification of functional Error Risk derived strictly from Error_Rate.
    Decoupled from overall FPGA Health (which may be degraded by temperature, supply rails, or RO timing).

    Engineering Thresholds (PRBS-7 monitor):
      - Error_Rate >= 0.002000 (>= 2000 ppm): "High" (Critical functional bit errors)
      - Error_Rate >= 0.000500 (>= 500 ppm):  "Medium" (Elevated soft error activity)
      - Error_Rate <  0.000500 (< 500 ppm):   "Low" (Nominal / negligible bit error rate)

    Returns:
      (risk_label, risk_color, description)
    """
    try:
        err = float(error_rate)
    except (TypeError, ValueError):
        err = 0.0

    cfg = SENSOR_CONFIG.get("Error_Rate", {})
    crit_high = cfg.get("critical_high", 0.002000)
    op_max = cfg.get("operating_max", 0.000500)

    if err >= crit_high:
        return "High", HEALTH_COLORS["Critical"], f"Bit Error Rate ({err:.6f}) exceeds critical limit ({crit_high:.6f})"
    elif err >= op_max:
        return "Medium", HEALTH_COLORS["Warning"], f"Bit Error Rate ({err:.6f}) is elevated above nominal floor ({op_max:.6f})"
    else:
        return "Low", HEALTH_COLORS["Healthy"], f"Bit Error Rate ({err:.6f}) is nominal (< {op_max:.6f})"



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
        equiv_delay = calculate_ro_delay_ns(val_float, stages=RO_STAGES)
        crit_delay_str = f"{100.0 / crit_low:.4f} ns" if crit_low > 0 else "N/A"
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
                reason=(
                    f"RO_Frequency ({val_float:.1f} MHz): Critical RO timing limit violated "
                    f"(critical limit = {crit_low:.1f} MHz); equivalent derived delay = {equiv_delay:.4f} ns "
                    f"(critical margin = {crit_delay_str}, derived from RO frequency)."
                ),
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
                reason=(
                    f"RO_Frequency ({val_float:.1f} MHz): Critical RO timing limit violated - "
                    f"abnormally high (critical limit = {crit_high:.1f} MHz, expected {op_str}); "
                    f"equivalent derived delay = {equiv_delay:.4f} ns (derived from RO frequency)."
                ),
                provenance=provenance
            )
        elif val_float < op_min or val_float > warn_high:
            warn_limit = warn_low if val_float < op_min else warn_high
            return ChannelEvaluation(
                channel=channel,
                value=val_float,
                display_name=disp,
                unit=unit,
                nominal=nom,
                operating_range_str=op_str,
                severity=LimitSeverity.WARNING,
                status_label="WARNING (TIMING DELAY DRIFT)" if val_float < op_min else "WARNING (SLIGHT OVERCLOCK)",
                is_violation=True,
                is_hard_override=True,
                reason=(
                    f"RO_Frequency ({val_float:.1f} MHz): RO timing degradation / drift warning "
                    f"(warning limit = {warn_limit:.1f} MHz, nominal = {nom:.1f} MHz); "
                    f"equivalent derived delay = {equiv_delay:.4f} ns (derived from RO frequency)."
                ) if val_float < op_min else (
                    f"RO_Frequency ({val_float:.1f} MHz): RO timing warning "
                    f"outside nominal operating range {op_str}; "
                    f"equivalent derived delay = {equiv_delay:.4f} ns (derived from RO frequency)."
                ),
                provenance=provenance
            )

    elif channel == "RO_Delay_ns":
        # Note: RO_Delay_ns is deterministically derived (tau = 100 / f_MHz).
        # RO_Frequency is the canonical hard-override timing measurement.
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
                is_hard_override=False,
                reason=f"Derived stage delay ({val_float:.4f} ns) exceeds critical timing margin {crit_high:.4f} ns (derived from RO frequency).",
                provenance=provenance
            )
        elif val_float <= crit_low:
            return ChannelEvaluation(
                channel=channel,
                value=val_float,
                display_name=disp,
                unit=unit,
                nominal=nom,
                operating_range_str=op_str,
                severity=LimitSeverity.CRITICAL,
                status_label="CRITICAL (ABNORMAL FAST GATE DELAY)",
                is_violation=True,
                is_hard_override=False,
                reason=f"Derived stage delay ({val_float:.4f} ns) abnormally fast (expected {op_str}, derived from RO frequency).",
                provenance=provenance
            )
        elif val_float > op_max or val_float < warn_low:
            return ChannelEvaluation(
                channel=channel,
                value=val_float,
                display_name=disp,
                unit=unit,
                nominal=nom,
                operating_range_str=op_str,
                severity=LimitSeverity.WARNING,
                status_label="WARNING (TIMING MARGIN REDUCTION)" if val_float > op_max else "WARNING (FAST TIMING DRIFT)",
                is_violation=True,
                is_hard_override=False,
                reason=f"Derived stage delay ({val_float:.4f} ns) is elevated above nominal {nom:.4f} ns (derived from RO frequency)." if val_float > op_max else f"Derived stage delay ({val_float:.4f} ns) is outside nominal operating range {op_str} (derived from RO frequency).",
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
        channel_evaluations: Dict[str, ChannelEvaluation],
        primary_reason: str = "All engineering limits satisfied",
        primary_channel: str = "Nominal",
        measured_str: str = "Nominal",
        limit_str: str = "Within envelope",
        derived_delay_str: Optional[str] = None,
        worst_region: Optional[str] = None,
        regional_evaluations: Optional[Dict[str, Dict[str, Any]]] = None,
        timing_reasons: Optional[List[str]] = None
    ):
        self.is_input_valid = is_input_valid
        self.is_physically_valid = is_physically_valid
        self.has_hard_violations = has_hard_violations
        self.max_severity = max_severity
        self.override_reasons = override_reasons
        self.channel_evaluations = channel_evaluations
        self.primary_reason = primary_reason
        self.primary_channel = primary_channel
        self.measured_str = measured_str
        self.limit_str = limit_str
        self.derived_delay_str = derived_delay_str
        self.worst_region = worst_region
        self.regional_evaluations = regional_evaluations or {}
        self.timing_reasons = timing_reasons or []
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
            "channels": {k: v.to_dict() for k, v in self.channel_evaluations.items()},
            "primary_reason": self.primary_reason,
            "primary_channel": self.primary_channel,
            "measured_str": self.measured_str,
            "limit_str": self.limit_str,
            "derived_delay_str": self.derived_delay_str,
            "worst_region": self.worst_region,
            "regional_evaluations": self.regional_evaluations,
            "timing_reasons": self.timing_reasons
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
            "evaluations": {k: v.to_dict() for k, v in self.channel_evaluations.items()},
            "primary_reason": self.primary_reason,
            "primary_channel": self.primary_channel,
            "measured_str": self.measured_str,
            "limit_str": self.limit_str,
            "derived_delay_str": self.derived_delay_str,
            "worst_region": self.worst_region,
            "regional_evaluations": self.regional_evaluations,
            "timing_reasons": self.timing_reasons
        }


def evaluate_engineering_limits(
    telemetry: Dict[str, Any],
    provenance_map: Optional[Dict[str, str]] = None,
    regional_baselines: Optional[Dict[str, float]] = None
) -> EngineeringAssessment:
    """
    Evaluates a full telemetry record against all centralized engineering boundaries.
    
    Architectural Principles:
      1. Deterministic engineering rules remain authoritative for physical safety.
      2. Derived quantities (RO_Delay_ns derived from RO_Frequency) are evaluated for
         display and observability, but NEVER counted as a second independent failure.
      3. When four regional monitors (R1..R4) are present, each is assessed independently
         so an anomalous quadrant is not masked by averaging.
    """
    provenance_map = provenance_map or {}
    regional_baselines = regional_baselines or {}
    evals: Dict[str, ChannelEvaluation] = {}
    reasons: List[str] = []
    timing_reasons: List[str] = []
    max_sev = LimitSeverity.NORMAL
    is_input_valid = True
    is_phys_valid = True
    has_hard_viol = False

    primary_reason = "All engineering limits satisfied"
    primary_channel = "Nominal"
    measured_str = "Nominal"
    limit_str = "Within envelope"
    derived_delay_str = None
    worst_region = None
    regional_evals: Dict[str, Dict[str, Any]] = {}

    # 1. Independent Regional RO Evaluation (R1, R2, R3, R4)
    has_regional_data = any(f"RO_{r}" in telemetry for r in ["R1", "R2", "R3", "R4"])
    worst_reg_sev = LimitSeverity.NORMAL
    worst_reg_id = None
    worst_reg_reason = None
    worst_reg_meas = None
    worst_reg_lim = None
    worst_reg_delay = None

    if has_regional_data:
        for r_id in ["R1", "R2", "R3", "R4"]:
            ro_k = f"RO_{r_id}"
            if ro_k not in telemetry:
                continue
            r_meta = REGIONAL_CONFIG[r_id]
            f_meas = float(telemetry[ro_k])
            f_base = float(regional_baselines.get(ro_k, r_meta["nominal_freq"]))
            drift_mhz = f_meas - f_base
            drift_pct = (drift_mhz / f_base) * 100.0 if f_base > 0 else 0.0
            tau_ns = calculate_ro_delay_ns(f_meas, stages=RO_STAGES)
            crit_drop = r_meta.get("critical_drop_pct", 5.5)
            warn_drop = r_meta.get("warning_drop_pct", 3.0)
            crit_f = round(f_base * (1.0 - crit_drop / 100.0), 1)
            warn_f = round(f_base * (1.0 - warn_drop / 100.0), 1)

            reg_sev = LimitSeverity.NORMAL
            reg_state = "Healthy"
            reg_reason = None

            if drift_pct <= -crit_drop:
                reg_sev = LimitSeverity.CRITICAL
                reg_state = "Degraded"
                reg_reason = (
                    f"Region {r_id} ({r_meta['quadrant']}): Critical RO timing limit violated: "
                    f"measured frequency = {f_meas:.1f} MHz (critical boundary = {crit_f:.1f} MHz, {drift_pct:.2f}% drift); "
                    f"equivalent derived delay = {tau_ns:.4f} ns (derived from RO frequency)."
                )
            elif drift_pct <= -warn_drop:
                reg_sev = LimitSeverity.WARNING
                reg_state = "Warning"
                reg_reason = (
                    f"Region {r_id} ({r_meta['quadrant']}): RO timing drift warning: "
                    f"measured frequency = {f_meas:.1f} MHz (warning boundary = {warn_f:.1f} MHz, {drift_pct:.2f}% drift); "
                    f"equivalent derived delay = {tau_ns:.4f} ns (derived from RO frequency)."
                )

            regional_evals[r_id] = {
                "id": r_id,
                "name": r_meta["name"],
                "quadrant": r_meta["quadrant"],
                "frequency": f_meas,
                "baseline_frequency": f_base,
                "drift_pct": drift_pct,
                "delay_ns": tau_ns,
                "severity": reg_sev,
                "state": reg_state,
                "reason": reg_reason
            }

            if reg_sev == LimitSeverity.CRITICAL and worst_reg_sev != LimitSeverity.CRITICAL:
                worst_reg_sev = LimitSeverity.CRITICAL
                worst_reg_id = r_id
                worst_reg_reason = reg_reason
                worst_reg_meas = f"{f_meas:.1f} MHz ({r_id})"
                worst_reg_lim = f"{crit_f:.1f} MHz ({r_id} critical boundary)"
                worst_reg_delay = f"{tau_ns:.4f} ns (derived from RO frequency)"
            elif reg_sev == LimitSeverity.WARNING and worst_reg_sev == LimitSeverity.NORMAL:
                worst_reg_sev = LimitSeverity.WARNING
                worst_reg_id = r_id
                worst_reg_reason = reg_reason
                worst_reg_meas = f"{f_meas:.1f} MHz ({r_id})"
                worst_reg_lim = f"{warn_f:.1f} MHz ({r_id} warning boundary)"
                worst_reg_delay = f"{tau_ns:.4f} ns (derived from RO frequency)"

    # 2. Evaluate Non-Timing Physical Sensor Channels
    phys_channels = ["Temperature", "VCCINT", "VCCAUX", "VCCBRAM", "Error_Rate"]
    for ch in phys_channels:
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
                    primary_reason = f"Physical sensor validity limit breached ({eval_res.display_name})"
                    primary_channel = ch
                    measured_str = f"{val} {eval_res.unit}".strip()
                    limit_str = f"[{eval_res.operating_range_str}]"
            elif eval_res.severity == LimitSeverity.CRITICAL:
                if max_sev != LimitSeverity.PHYSICALLY_INVALID:
                    max_sev = LimitSeverity.CRITICAL
                has_hard_viol = True
                if eval_res.reason:
                    reasons.append(eval_res.reason)
                    if primary_channel == "Nominal" or primary_channel == "RO_Frequency":
                        primary_reason = f"Critical {eval_res.display_name} limit violated"
                        primary_channel = ch
                        measured_str = f"{val} {eval_res.unit}".strip()
                        limit_str = f"Critical limit exceeded"
            elif eval_res.severity == LimitSeverity.WARNING:
                if max_sev == LimitSeverity.NORMAL:
                    max_sev = LimitSeverity.WARNING
                has_hard_viol = True
                if eval_res.reason:
                    reasons.append(eval_res.reason)
                    if primary_channel == "Nominal":
                        primary_reason = f"{eval_res.display_name} operating warning"
                        primary_channel = ch
                        measured_str = f"{val} {eval_res.unit}".strip()
                        limit_str = f"Outside normal range"

    # 3. Evaluate Timing Channels (RO_Frequency and Derived RO_Delay_ns)
    # Always evaluate both for display/sensor table
    if "RO_Frequency" in telemetry:
        evals["RO_Frequency"] = evaluate_single_channel("RO_Frequency", telemetry["RO_Frequency"], provenance=provenance_map.get("RO_Frequency", "MEASURED"))
    if "RO_Delay_ns" in telemetry:
        evals["RO_Delay_ns"] = evaluate_single_channel("RO_Delay_ns", telemetry["RO_Delay_ns"], provenance=provenance_map.get("RO_Delay_ns", "DERIVED"))

    # 4. Integrate Timing Violation (Canonical Single Source of Truth, No Double Counting)
    if has_regional_data and worst_reg_sev in (LimitSeverity.CRITICAL, LimitSeverity.WARNING):
        # A regional monitor has triggered an independent timing alert
        worst_region = worst_reg_id
        if worst_reg_sev == LimitSeverity.CRITICAL:
            if max_sev != LimitSeverity.PHYSICALLY_INVALID:
                max_sev = LimitSeverity.CRITICAL
            has_hard_viol = True
            if worst_reg_reason:
                reasons.append(worst_reg_reason)
                timing_reasons.append(worst_reg_reason)
            primary_reason = f"Critical RO timing limit violated in {REGIONAL_CONFIG[worst_reg_id]['name']} ({REGIONAL_CONFIG[worst_reg_id]['quadrant']})"
            primary_channel = f"RO_{worst_reg_id}"
            measured_str = worst_reg_meas
            limit_str = worst_reg_lim
            derived_delay_str = worst_reg_delay
        elif worst_reg_sev == LimitSeverity.WARNING:
            if max_sev == LimitSeverity.NORMAL:
                max_sev = LimitSeverity.WARNING
            has_hard_viol = True
            if worst_reg_reason:
                reasons.append(worst_reg_reason)
                timing_reasons.append(worst_reg_reason)
            if primary_channel == "Nominal":
                primary_reason = f"RO timing drift warning in {REGIONAL_CONFIG[worst_reg_id]['name']} ({REGIONAL_CONFIG[worst_reg_id]['quadrant']})"
                primary_channel = f"RO_{worst_reg_id}"
                measured_str = worst_reg_meas
                limit_str = worst_reg_lim
                derived_delay_str = worst_reg_delay
    elif "RO_Frequency" in telemetry:
        # Standard global RO_Frequency evaluation (when regional data not present or healthy)
        ro_eval = evals["RO_Frequency"]
        val_f = float(telemetry["RO_Frequency"])
        equiv_delay = calculate_ro_delay_ns(val_f, stages=RO_STAGES)
        cfg_ro = SENSOR_CONFIG["RO_Frequency"]

        if ro_eval.severity == LimitSeverity.CRITICAL:
            if max_sev != LimitSeverity.PHYSICALLY_INVALID:
                max_sev = LimitSeverity.CRITICAL
            has_hard_viol = True
            if ro_eval.reason:
                reasons.append(ro_eval.reason)
                timing_reasons.append(ro_eval.reason)
            primary_reason = "Critical RO timing limit violated"
            primary_channel = "RO_Frequency"
            measured_str = f"{val_f:.1f} MHz"
            limit_str = f"{cfg_ro['critical_low']:.1f} MHz"
            derived_delay_str = f"{equiv_delay:.4f} ns (derived from RO frequency)"
        elif ro_eval.severity == LimitSeverity.WARNING:
            if max_sev == LimitSeverity.NORMAL:
                max_sev = LimitSeverity.WARNING
            has_hard_viol = True
            if ro_eval.reason:
                reasons.append(ro_eval.reason)
                timing_reasons.append(ro_eval.reason)
            if primary_channel == "Nominal":
                primary_reason = "RO timing drift warning"
                primary_channel = "RO_Frequency"
                measured_str = f"{val_f:.1f} MHz"
                limit_str = f"{cfg_ro['warning_low']:.1f} MHz"
                derived_delay_str = f"{equiv_delay:.4f} ns (derived from RO frequency)"
        # Note: RO_Delay_ns is NOT appended to reasons when RO_Frequency is present!
    elif "RO_Delay_ns" in telemetry:
        # Fallback only if RO_Frequency was completely missing from telemetry
        delay_eval = evals["RO_Delay_ns"]
        val_d = float(telemetry["RO_Delay_ns"])
        cfg_d = SENSOR_CONFIG["RO_Delay_ns"]
        if delay_eval.severity == LimitSeverity.CRITICAL:
            if max_sev != LimitSeverity.PHYSICALLY_INVALID:
                max_sev = LimitSeverity.CRITICAL
            has_hard_viol = True
            if delay_eval.reason:
                reasons.append(delay_eval.reason)
                timing_reasons.append(delay_eval.reason)
            primary_reason = "Critical RO propagation delay exceeded"
            primary_channel = "RO_Delay_ns"
            measured_str = f"{val_d:.4f} ns"
            limit_str = f"{cfg_d['critical_high']:.4f} ns"
            derived_delay_str = f"{val_d:.4f} ns (derived from RO frequency)"
        elif delay_eval.severity == LimitSeverity.WARNING:
            if max_sev == LimitSeverity.NORMAL:
                max_sev = LimitSeverity.WARNING
            has_hard_viol = True
            if delay_eval.reason:
                reasons.append(delay_eval.reason)
                timing_reasons.append(delay_eval.reason)
            if primary_channel == "Nominal":
                primary_reason = "RO propagation delay elevated"
                primary_channel = "RO_Delay_ns"
                measured_str = f"{val_d:.4f} ns"
                limit_str = f"{cfg_d['warning_high']:.4f} ns"
                derived_delay_str = f"{val_d:.4f} ns (derived from RO frequency)"

    return EngineeringAssessment(
        is_input_valid=is_input_valid,
        is_physically_valid=is_phys_valid,
        has_hard_violations=has_hard_viol,
        max_severity=max_sev,
        override_reasons=reasons,
        channel_evaluations=evals,
        primary_reason=primary_reason,
        primary_channel=primary_channel,
        measured_str=measured_str,
        limit_str=limit_str,
        derived_delay_str=derived_delay_str,
        worst_region=worst_region,
        regional_evaluations=regional_evals,
        timing_reasons=timing_reasons
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
      2. Critical Operating Breach -> Final: 'Degraded', Override: True (if ML != Degraded)
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
        primary_reason = engineering_assessment.get("primary_reason", "Deterministic engineering limit violated")
        primary_channel = engineering_assessment.get("primary_channel", "Nominal")
        measured_str = engineering_assessment.get("measured_str", "Nominal")
        limit_str = engineering_assessment.get("limit_str", "Nominal")
        derived_delay_str = engineering_assessment.get("derived_delay_str")
        worst_region = engineering_assessment.get("worst_region")
        regional_evals = engineering_assessment.get("regional_evaluations", {})
        eng_dict = engineering_assessment
    else:
        max_sev = engineering_assessment.max_severity
        reasons = engineering_assessment.override_reasons
        evals = engineering_assessment.channel_evaluations
        primary_reason = getattr(engineering_assessment, "primary_reason", "Deterministic engineering limit violated")
        primary_channel = getattr(engineering_assessment, "primary_channel", "Nominal")
        measured_str = getattr(engineering_assessment, "measured_str", "Nominal")
        limit_str = getattr(engineering_assessment, "limit_str", "Nominal")
        derived_delay_str = getattr(engineering_assessment, "derived_delay_str", None)
        worst_region = getattr(engineering_assessment, "worst_region", None)
        regional_evals = getattr(engineering_assessment, "regional_evaluations", {})
        eng_dict = engineering_assessment.to_dict()

    final_decision_str = f"{ml_pred_clean.upper()} (All engineering limits satisfied)."

    if max_sev == LimitSeverity.PHYSICALLY_INVALID:
        final_health = "Degraded"
        override_applied = True
        override_title = "CRITICAL — PHYSICAL VALIDITY OVERRIDE"
        override_explanation = (
            f"Telemetry values violate physical sensor limits ({'; '.join(reasons)}). "
            f"The Random Forest predicted '{ml_pred_clean}' ({ml_confidence * 100:.1f}%), "
            "but physical sensor validity takes absolute precedence."
        )
        final_decision_str = "DEGRADED because physical sensor validity limits take precedence over the ML prediction."

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
            final_decision_str = "DEGRADED because the deterministic engineering limit takes precedence over the ML prediction."
        else:
            final_decision_str = "DEGRADED (ML prediction confirmed by deterministic engineering limits)."

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
            final_decision_str = "WARNING because the deterministic operating boundary takes precedence over the ML prediction."
        elif ml_pred_clean == "Degraded":
            final_health = "Degraded"
            final_decision_str = "DEGRADED based on ML probabilistic model inference."
        else:
            final_health = "Warning"
            final_decision_str = "WARNING (ML prediction confirmed by engineering limits)."

    assessment_panel = {
        "ml_prediction": ml_pred_clean.upper(),
        "ml_confidence": float(ml_confidence),
        "ml_confidence_str": f"{ml_confidence * 100:.1f}%",
        "eng_assessment": final_health.upper(),
        "primary_reason": primary_reason,
        "primary_channel": primary_channel,
        "measured_str": measured_str,
        "limit_str": limit_str,
        "derived_delay_str": derived_delay_str,
        "final_decision": final_decision_str
    }

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
        "engineering_assessment": eng_dict,
        "assessment_panel": assessment_panel,
        "primary_reason": primary_reason,
        "primary_channel": primary_channel,
        "measured_str": measured_str,
        "limit_str": limit_str,
        "derived_delay_str": derived_delay_str,
        "final_decision": final_decision_str,
        "worst_region": worst_region,
        "regional_evaluations": regional_evals
    }
