from typing import TypedDict

from langgraph.graph import StateGraph, END


# ============================================================
# State
# ============================================================

class FPGAState(TypedDict):

    health: str
    confidence: float

    temperature: float
    ro_frequency: float
    ro_delay: float

    error_rate: float

    recommendation: str


# ============================================================
# Analyze health
# ============================================================

def analyze_health(state):

    health = state["health"]

    confidence = state["confidence"]

    temperature = state["temperature"]

    ro_frequency = state["ro_frequency"]

    error_rate = state["error_rate"]


    # --------------------------------------------------------
    # Recommendation logic
    # --------------------------------------------------------

    if health == "Degraded":

        recommendation = (
            "FPGA health is degraded. "
            "Increase monitoring frequency and "
            "investigate increasing error rate "
            "and RO frequency degradation."
        )

    elif health == "Warning":

        recommendation = (
            "FPGA health is showing warning signs. "
            "Continue monitoring temperature, "
            "RO frequency and functional error rate."
        )

    else:

        recommendation = (
            "FPGA health is currently healthy. "
            "Continue normal monitoring."
        )


    # --------------------------------------------------------
    # Additional conditions
    # --------------------------------------------------------

    if temperature > 50:

        recommendation += (
            " Temperature is elevated."
        )


    if error_rate > 0.002:

        recommendation += (
            " Functional error rate is increasing."
        )


    if confidence < 0.70:

        recommendation += (
            " Prediction confidence is relatively low; "
            "collect additional measurements."
        )


    state["recommendation"] = recommendation

    return state


# ============================================================
# Build LangGraph
# ============================================================

graph = StateGraph(FPGAState)


graph.add_node(
    "analyze_health",
    analyze_health
)


graph.set_entry_point(
    "analyze_health"
)


graph.add_edge(
    "analyze_health",
    END
)


app = graph.compile()


# ============================================================
# Test
# ============================================================

if __name__ == "__main__":

    state = {

        "health": "Warning",

        "confidence": 0.87,

        "temperature": 48.5,

        "ro_frequency": 241.2,

        "ro_delay": 2.07,

        "error_rate": 0.0015,

        "recommendation": ""

    }


    result = app.invoke(state)


    print("\nFPGA HEALTH")
    print(
        result["health"]
    )

    print("\nCONFIDENCE")
    print(
        result["confidence"]
    )

    print("\nRECOMMENDATION")
    print(
        result["recommendation"]
    )