"""
Centralized Hardware & Physics Configuration for FPGA Health Monitoring
========================================================================
Defines key physical constants, on-chip sensor specifications, and
standard ring oscillator physical delay conversion functions.
"""

from typing import Tuple

# ============================================================
# Target Hardware Specifications (Digilent Basys 3 / Xilinx Artix-7 XC7A35T)
# ============================================================
DEVICE_NAME = "Xilinx Artix-7 (XC7A35T-1CPG236C)"
ARCHITECTURE = "28nm HKMG (High-K Metal Gate)"

# Number of inverter stages in the on-chip Ring Oscillator
RO_STAGES = 5

# Calibrated physical baseline for Digilent Basys 3 (5-stage RO @ ~229 ps/stage)
RO_NOMINAL_MHZ = 436.0
RO_NOMINAL_DELAY_NS = 0.2294  # 1000.0 / (2 * 5 * 436.0) = 0.2294 ns (229.4 ps)


# ============================================================
# Physical Ring Oscillator Delay Calculations
# ============================================================
def calculate_ro_delay_ns(frequency_mhz: float, stages: int = RO_STAGES) -> float:
    """
    Calculates the derived propagation delay per stage (in nanoseconds)
    for an N-stage Ring Oscillator oscillating at frequency f (in MHz).

    Physical Derivation:
    T = 2 * N * tau
    f_Hz = 1 / (2 * N * tau_seconds)
    tau_seconds = 1 / (2 * N * f_Hz)
    
    Given frequency in MHz:
    f_Hz = frequency_mhz * 1e6
    tau_seconds = 1 / (2 * stages * frequency_mhz * 1e6)
    tau_ns = tau_seconds * 1e9 = 1000.0 / (2 * stages * frequency_mhz)
    """
    if frequency_mhz <= 0 or stages <= 0:
        return 0.0
    
    f_hz = float(frequency_mhz) * 1e6
    tau_seconds = 1.0 / (2.0 * float(stages) * f_hz)
    tau_ns = tau_seconds * 1e9
    return round(tau_ns, 4)


def validate_ro_delay(frequency_mhz: float, stages: int = RO_STAGES, delay_ns: float = None) -> Tuple[bool, str]:
    """
    Sanity check to verify that calculated RO delay is physically reasonable.
    For a 28nm FPGA with 5 stages @ 200-300 MHz, delay should be ~0.3 - 0.6 ns/stage.
    """
    if delay_ns is None:
        delay_ns = calculate_ro_delay_ns(frequency_mhz, stages)

    # Expected physical delay bounds on 28nm Artix-7 (0.10 ns to 2.50 ns per stage)
    MIN_PHYSICAL_DELAY_NS = 0.10
    MAX_PHYSICAL_DELAY_NS = 2.50

    if not (MIN_PHYSICAL_DELAY_NS <= delay_ns <= MAX_PHYSICAL_DELAY_NS):
        return False, (
            f"RO delay sanity check failed: calculated delay {delay_ns} ns is outside "
            f"expected physical range [{MIN_PHYSICAL_DELAY_NS}, {MAX_PHYSICAL_DELAY_NS}] ns for {frequency_mhz} MHz with {stages} stages."
        )

    expected = calculate_ro_delay_ns(frequency_mhz, stages)
    if abs(delay_ns - expected) > 0.01:
        return False, f"RO delay calculation mismatch: provided {delay_ns} ns != calculated {expected} ns."

    return True, "RO delay is physically valid."
