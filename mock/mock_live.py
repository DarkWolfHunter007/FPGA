import time
import random


def generate_live_measurement():

    temperature = random.uniform(
        35,
        50
    )

    vccint = random.uniform(
        0.99,
        1.01
    )

    vccaux = random.uniform(
        1.79,
        1.81
    )

    vccbram = random.uniform(
        0.99,
        1.01
    )

    ro_frequency = random.uniform(
        238,
        250
    )

    ro_delay = (
        1 / (2 * ro_frequency)
    ) * 1e9

    error_rate = random.uniform(
        0,
        0.002
    )

    return {

        "Temperature": temperature,

        "VCCINT": vccint,

        "VCCAUX": vccaux,

        "VCCBRAM": vccbram,

        "RO_Frequency": ro_frequency,

        "RO_Delay_ns": ro_delay,

        "Error_Rate": error_rate
    }


if __name__ == "__main__":

    while True:

        measurement = (
            generate_live_measurement()
        )

        print(measurement)

        time.sleep(1)