import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import RO_STAGES, calculate_ro_delay_ns, validate_ro_delay

# ============================================================
# Configuration
# ============================================================

NUM_SAMPLES = 10000
OUTPUT_FILE = PROJECT_ROOT / "data" / "raw" / "mock_fpga_data.csv"

np.random.seed(42)


# ============================================================
# Generate one FPGA measurement
# ============================================================

def generate_measurement(timestamp, degradation):
    """
    degradation:
        0.0 = healthy
        0.5 = stressed
        1.0 = degraded
    """

    # --------------------------------------------------------
    # Temperature (°C)
    # --------------------------------------------------------
    temperature = (
        35.0
        + 18.0 * degradation
        + np.random.normal(0, 0.8)
    )

    # --------------------------------------------------------
    # Supply voltages (V)
    # --------------------------------------------------------
    vccint = (
        1.000
        - 0.010 * degradation
        + np.random.normal(0, 0.001)
    )

    vccaux = (
        1.800
        - 0.010 * degradation
        + np.random.normal(0, 0.001)
    )

    vccbram = (
        1.000
        - 0.008 * degradation
        + np.random.normal(0, 0.001)
    )

    # --------------------------------------------------------
    # Ring oscillator frequency (MHz)
    # Healthy FPGA ≈ higher frequency (~436 MHz)
    # Degraded FPGA ≈ lower frequency (~411 MHz)
    # --------------------------------------------------------
    ro_frequency = (
        436.0
        - 25.0 * degradation
        + np.random.normal(0, 0.8)
    )

    # --------------------------------------------------------
    # Physical Derived RO Stage Propagation Delay (ns)
    # Formula: tau = 1 / (2 * N * f_Hz)
    # tau_ns = 1000 / (2 * N * f_MHz)
    # For N=5 stages and f=411-436 MHz -> tau_ns ~ 0.229 - 0.243 ns/stage
    # --------------------------------------------------------
    ro_delay_ns = calculate_ro_delay_ns(ro_frequency, stages=RO_STAGES)

    # --------------------------------------------------------
    # Functional error rate
    # --------------------------------------------------------
    base_error_probability = (
        0.00001
        + 0.003 * degradation
    )

    error_rate = max(
        0.0,
        base_error_probability
        + np.random.normal(0, 0.0002)
    )

    # --------------------------------------------------------
    # Determine simulated health label
    # --------------------------------------------------------
    if degradation < 0.35:
        health = "Healthy"
    elif degradation < 0.70:
        health = "Warning"
    else:
        health = "Degraded"

    return {
        "Timestamp": timestamp,
        "Temperature": round(temperature, 4),
        "VCCINT": round(vccint, 4),
        "VCCAUX": round(vccaux, 4),
        "VCCBRAM": round(vccbram, 4),
        "RO_Frequency": round(ro_frequency, 4),
        "RO_Delay_ns": round(ro_delay_ns, 4),
        "Error_Rate": round(error_rate, 6),
        "Health": health
    }


# ============================================================
# Generate dataset
# ============================================================

def generate_dataset():
    data = []

    for i in range(NUM_SAMPLES):
        timestamp = i
        degradation = i / NUM_SAMPLES
        measurement = generate_measurement(timestamp, degradation)
        data.append(measurement)

    df = pd.DataFrame(data)

    # Perform physical sanity validation on generated dataset
    sample_freq = df["RO_Frequency"].iloc[0]
    sample_delay = df["RO_Delay_ns"].iloc[0]
    is_valid, msg = validate_ro_delay(sample_freq, RO_STAGES, sample_delay)
    if not is_valid:
        raise ValueError(f"CRITICAL SANITY CHECK FAILED: {msg}")

    # Create directory if necessary
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False)

    print("==================================================")
    print("MOCK FPGA DATASET GENERATION & UNIT AUDIT")
    print("==================================================")
    print(f"Dataset generated successfully with {len(df)} samples.")
    print(f"Saved to: {OUTPUT_FILE}")
    print(f"RO Inverter Stages (N): {RO_STAGES}")
    print(f"Sample Initial Frequency: {sample_freq:.2f} MHz -> Delay: {sample_delay:.4f} ns/stage")
    print(f"Sample Degraded Frequency: {df['RO_Frequency'].iloc[-1]:.2f} MHz -> Delay: {df['RO_Delay_ns'].iloc[-1]:.4f} ns/stage")
    print(f"Validation Status: {msg}")
    print("\nHealth distribution:")
    print(df["Health"].value_counts())
    print("==================================================")


if __name__ == "__main__":
    generate_dataset()