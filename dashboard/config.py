"""
Configuration Constants and Sensor Thresholds for FPGA Health Monitoring
========================================================================
Centralizes all physical operating limits, nominal ratings, and threshold rules.
No magic numbers in UI code.
"""

from typing import Dict, Any
from config import RO_STAGES, calculate_ro_delay_ns, validate_ro_delay, DEVICE_NAME, ARCHITECTURE

# Backward compatibility alias
RO_STAGE_COUNT = RO_STAGES

# ============================================================
# Sensor Operating Nominals & Validation Bounds
# ============================================================
SENSOR_CONFIG: Dict[str, Dict[str, Any]] = {
    "Temperature": {
        "unit": "°C",
        "nominal": 35.0,
        "warning": 45.0,
        "critical": 52.0,
        "min_valid": 0.0,
        "max_valid": 125.0,
        "display_name": "Die Temperature"
    },
    "VCCINT": {
        "unit": "V",
        "nominal": 1.000,
        "tolerance_pct": 2.5,
        "min_nominal": 0.975,
        "max_nominal": 1.025,
        "min_valid": 0.5,
        "max_valid": 1.5,
        "display_name": "VCCINT (Core Supply)"
    },
    "VCCAUX": {
        "unit": "V",
        "nominal": 1.800,
        "tolerance_pct": 2.5,
        "min_nominal": 1.755,
        "max_nominal": 1.845,
        "min_valid": 1.0,
        "max_valid": 2.5,
        "display_name": "VCCAUX (Auxiliary Supply)"
    },
    "VCCBRAM": {
        "unit": "V",
        "nominal": 1.000,
        "tolerance_pct": 2.5,
        "min_nominal": 0.975,
        "max_nominal": 1.025,
        "min_valid": 0.5,
        "max_valid": 1.5,
        "display_name": "VCCBRAM (BRAM Supply)"
    },
    "RO_Frequency": {
        "unit": "MHz",
        "nominal": 250.0,
        "warning_drop_pct": 3.0,
        "critical_drop_pct": 5.5,
        "min_valid": 50.0,
        "max_valid": 400.0,
        "display_name": "Ring Oscillator Frequency"
    },
    "RO_Delay_ns": {
        "unit": "ns",
        "nominal": 0.4000,  # Correct nominal delay for 5-stage RO at 250 MHz
        "warning_increase_pct": 3.0,
        "critical_increase_pct": 6.0,
        "min_valid": 0.10,
        "max_valid": 2.50,
        "display_name": "Derived RO Stage Delay"
    },
    "Error_Rate": {
        "unit": "",
        "nominal": 0.00001,
        "warning": 0.0010,
        "critical": 0.0025,
        "min_valid": 0.0,
        "max_valid": 1.0,
        "display_name": "Functional Error Rate"
    }
}

# ============================================================
# Health State Color Palette
# ============================================================
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
