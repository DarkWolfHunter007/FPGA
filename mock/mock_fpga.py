import os
import numpy as np
import pandas as pd

# ============================================================
# Configuration
# ============================================================

NUM_SAMPLES = 10000
OUTPUT_FILE = "../data/raw/mock_fpga_data.csv"

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
    # Temperature
    # --------------------------------------------------------

    temperature = (
        35
        + 18 * degradation
        + np.random.normal(0, 0.8)
    )

    # --------------------------------------------------------
    # Supply voltages
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
    # Ring oscillator
    #
    # Healthy FPGA ≈ higher frequency
    # Degraded FPGA ≈ lower frequency
    # --------------------------------------------------------

    ro_frequency = (
        250
        - 15 * degradation
        + np.random.normal(0, 0.8)
    )

    # --------------------------------------------------------
    # Approximate RO delay
    #
    # This is a simplified simulated relationship.
    # Actual hardware delay must be measured on the FPGA.
    # --------------------------------------------------------

    ro_delay = (
        1 / (2 * ro_frequency)
    )

    # Convert to ns for easier interpretation

    ro_delay_ns = ro_delay * 1e9

    # --------------------------------------------------------
    # Functional error rate
    # --------------------------------------------------------

    base_error_probability = (
        0.00001
        + 0.003 * degradation
    )

    error_rate = max(
        0,
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
        "Temperature": temperature,
        "VCCINT": vccint,
        "VCCAUX": vccaux,
        "VCCBRAM": vccbram,
        "RO_Frequency": ro_frequency,
        "RO_Delay_ns": ro_delay_ns,
        "Error_Rate": error_rate,
        "Health": health
    }


# ============================================================
# Generate dataset
# ============================================================

def generate_dataset():

    data = []

    for i in range(NUM_SAMPLES):

        timestamp = i

        # Slowly changing degradation

        degradation = i / NUM_SAMPLES

        measurement = generate_measurement(
            timestamp,
            degradation
        )

        data.append(measurement)

    df = pd.DataFrame(data)

    # Create directory if necessary

    os.makedirs(
        os.path.dirname(OUTPUT_FILE),
        exist_ok=True
    )

    df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print("Dataset generated successfully.")
    print(f"Samples: {len(df)}")
    print(f"Saved to: {OUTPUT_FILE}")

    print("\nHealth distribution:")
    print(df["Health"].value_counts())


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    generate_dataset()