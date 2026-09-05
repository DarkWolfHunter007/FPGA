import sys
import time
import random
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import RO_STAGES, calculate_ro_delay_ns


def generate_live_measurement():
    temperature = round(random.uniform(35.0, 50.0), 2)
    vccint = round(random.uniform(0.990, 1.010), 4)
    vccaux = round(random.uniform(1.790, 1.810), 4)
    vccbram = round(random.uniform(0.990, 1.010), 4)
    ro_frequency = round(random.uniform(238.0, 250.0), 2)
    
    # Corrected physical delay calculation: tau_ns = 1000 / (2 * N * f_MHz)
    ro_delay_ns = calculate_ro_delay_ns(ro_frequency, stages=RO_STAGES)
    error_rate = round(random.uniform(0.0, 0.002), 6)

    return {
        "Temperature": temperature,
        "VCCINT": vccint,
        "VCCAUX": vccaux,
        "VCCBRAM": vccbram,
        "RO_Frequency": ro_frequency,
        "RO_Delay_ns": ro_delay_ns,
        "Error_Rate": error_rate
    }


if __name__ == "__main__":
    print(f"Streaming live mock measurements (N={RO_STAGES} stages)... Press Ctrl+C to stop.\n")
    for _ in range(5):
        measurement = generate_live_measurement()
        print(measurement)
        time.sleep(0.5)