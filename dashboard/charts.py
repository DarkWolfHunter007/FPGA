"""
Interactive Technical Chart Builders for FPGA Health Monitoring Dashboard
========================================================================
Built with Altair for high-performance, dark-themed, responsive visualizations.
Strictly separates distinct physical scales onto their own dedicated charts.
"""

from typing import List, Tuple, Optional, Dict
import pandas as pd
import numpy as np
import altair as alt


def apply_dark_theme(chart: alt.Chart) -> alt.Chart:
    """Applies a clean FPGA laboratory dark aesthetic to Altair charts."""
    return chart.configure(
        background="transparent"
    ).configure_view(
        strokeOpacity=0
    ).configure_axis(
        gridColor="rgba(255, 255, 255, 0.07)",
        domainColor="rgba(255, 255, 255, 0.2)",
        tickColor="rgba(255, 255, 255, 0.2)",
        labelColor="#94A3B8",
        titleColor="#E2E8F0",
        labelFontSize=11,
        titleFontSize=12,
        titleFontWeight="normal",
        labelFont="JetBrains Mono, Consolas, monospace",
        titleFont="Inter, sans-serif"
    ).configure_legend(
        labelColor="#CBD5E1",
        titleColor="#E2E8F0",
        labelFont="Inter, sans-serif",
        titleFont="Inter, sans-serif"
    )


def create_temperature_chart(df: pd.DataFrame, baseline_temp: float = 35.0) -> alt.Chart:
    """Graph 3: FPGA Die Temperature Trend (°C) with baseline and warning reference lines."""
    plot_df = df.reset_index()
    plot_df["Sample_Index"] = plot_df.index

    line = alt.Chart(plot_df).mark_line(
        color="#FF5252",
        strokeWidth=2.2
    ).encode(
        x=alt.X("Sample_Index:Q", title="Timestamp / Sample Sequence"),
        y=alt.Y("Temperature:Q", title="Die Temperature (°C)", scale=alt.Scale(zero=False)),
        tooltip=[
            alt.Tooltip("Sample_Index:Q", title="Sample #"),
            alt.Tooltip("Temperature:Q", title="Temperature (°C)", format=".2f")
        ]
    )

    # Baseline reference line
    base_df = pd.DataFrame({"y": [baseline_temp]})
    base_rule = alt.Chart(base_df).mark_rule(
        color="#00E676",
        strokeDash=[3, 3],
        strokeWidth=1.2,
        opacity=0.8
    ).encode(y="y:Q")

    # Warning threshold line at 50°C
    thresh_df = pd.DataFrame({"y": [50.0]})
    warn_rule = alt.Chart(thresh_df).mark_rule(
        color="#FF9100",
        strokeDash=[4, 4],
        strokeWidth=1.2,
        opacity=0.7
    ).encode(y="y:Q")

    return apply_dark_theme(line + base_rule + warn_rule)


def create_ro_frequency_chart(df: pd.DataFrame, baseline_freq: float = 436.0) -> alt.Chart:
    """Graph 1: Ring Oscillator Frequency Trend (MHz) with baseline reference line."""
    plot_df = df.reset_index()
    plot_df["Sample_Index"] = plot_df.index

    line = alt.Chart(plot_df).mark_line(
        color="#00E5FF",
        strokeWidth=2.2
    ).encode(
        x=alt.X("Sample_Index:Q", title="Timestamp / Sample Sequence"),
        y=alt.Y("RO_Frequency:Q", title="RO Frequency (MHz)", scale=alt.Scale(zero=False)),
        tooltip=[
            alt.Tooltip("Sample_Index:Q", title="Sample #"),
            alt.Tooltip("RO_Frequency:Q", title="Frequency (MHz)", format=".2f")
        ]
    )

    # Baseline reference line
    base_df = pd.DataFrame({"y": [baseline_freq]})
    base_rule = alt.Chart(base_df).mark_rule(
        color="#38BDF8",
        strokeDash=[3, 3],
        strokeWidth=1.2,
        opacity=0.8
    ).encode(y="y:Q")

    return apply_dark_theme(line + base_rule)


def create_ro_delay_chart(df: pd.DataFrame, baseline_delay: float = 0.2294) -> alt.Chart:
    """Graph 2: Ring Oscillator Delay Trend (Derived RO Stage Delay in ns) with baseline reference line."""
    plot_df = df.reset_index()
    plot_df["Sample_Index"] = plot_df.index

    line = alt.Chart(plot_df).mark_line(
        color="#D946EF",
        strokeWidth=2.2
    ).encode(
        x=alt.X("Sample_Index:Q", title="Timestamp / Sample Sequence"),
        y=alt.Y("RO_Delay_ns:Q", title="Derived RO Stage Delay (ns)", scale=alt.Scale(zero=False)),
        tooltip=[
            alt.Tooltip("Sample_Index:Q", title="Sample #"),
            alt.Tooltip("RO_Delay_ns:Q", title="Stage Delay (ns)", format=".4f")
        ]
    )

    # Baseline reference line
    base_df = pd.DataFrame({"y": [baseline_delay]})
    base_rule = alt.Chart(base_df).mark_rule(
        color="#A855F7",
        strokeDash=[3, 3],
        strokeWidth=1.2,
        opacity=0.8
    ).encode(y="y:Q")

    return apply_dark_theme(line + base_rule)


def create_error_rate_chart(df: pd.DataFrame) -> alt.Chart:
    """Graph 4: Functional Error Rate Trend."""
    plot_df = df.reset_index()
    plot_df["Sample_Index"] = plot_df.index

    area = alt.Chart(plot_df).mark_area(
        line={"color": "#FFAB00", "width": 2},
        color=alt.Gradient(
            gradient="linear",
            stops=[
                alt.GradientStop(color="rgba(255, 171, 0, 0.45)", offset=0),
                alt.GradientStop(color="rgba(255, 171, 0, 0.02)", offset=1)
            ],
            x1=1, x2=1, y1=1, y2=0
        )
    ).encode(
        x=alt.X("Sample_Index:Q", title="Timestamp / Sample Sequence"),
        y=alt.Y("Error_Rate:Q", title="Functional Error Rate", scale=alt.Scale(zero=True)),
        tooltip=[
            alt.Tooltip("Sample_Index:Q", title="Sample #"),
            alt.Tooltip("Error_Rate:Q", title="Error Rate", format=".6f")
        ]
    )
    return apply_dark_theme(area)


def create_voltage_chart(df: pd.DataFrame, rail: str = "VCCINT", nominal_voltage: float = 1.000) -> alt.Chart:
    """Graph 5: Supply Voltage Rail Trend (V)."""
    plot_df = df.reset_index()
    plot_df["Sample_Index"] = plot_df.index

    rail_colors = {
        "VCCINT": "#00E676",
        "VCCAUX": "#38BDF8",
        "VCCBRAM": "#A855F7"
    }
    color = rail_colors.get(rail, "#00E676")

    line = alt.Chart(plot_df).mark_line(
        color=color,
        strokeWidth=2.0
    ).encode(
        x=alt.X("Sample_Index:Q", title="Timestamp / Sample Sequence"),
        y=alt.Y(f"{rail}:Q", title=f"{rail} Voltage (V)", scale=alt.Scale(zero=False)),
        tooltip=[
            alt.Tooltip("Sample_Index:Q", title="Sample #"),
            alt.Tooltip(f"{rail}:Q", title=f"{rail} (V)", format=".4f")
        ]
    )

    # Nominal voltage reference line
    nom_df = pd.DataFrame({"y": [nominal_voltage]})
    nom_rule = alt.Chart(nom_df).mark_rule(
        color="rgba(255, 255, 255, 0.35)",
        strokeDash=[2, 2],
        strokeWidth=1.0
    ).encode(y="y:Q")

    return apply_dark_theme(line + nom_rule)


def create_health_prediction_trend_chart(df: pd.DataFrame) -> alt.Chart:
    """
    Graph 6: FPGA Health Prediction Trend Over Time.
    Encodes Healthy=0, Warning=1, Degraded=2 with exact ML classes.
    """
    plot_df = df.reset_index()
    plot_df["Sample_Index"] = plot_df.index

    state_map = {"Healthy": 0, "Warning": 1, "Degraded": 2}
    if "Predicted_Health" in plot_df.columns:
        plot_df["Health_Level"] = plot_df["Predicted_Health"].map(lambda x: state_map.get(str(x), 0))
        plot_df["Health_Label"] = plot_df["Predicted_Health"].astype(str)
    elif "Health" in plot_df.columns:
        plot_df["Health_Level"] = plot_df["Health"].map(lambda x: state_map.get(str(x), 0))
        plot_df["Health_Label"] = plot_df["Health"].astype(str)
    else:
        plot_df["Health_Level"] = 0
        plot_df["Health_Label"] = "Healthy"

    chart = alt.Chart(plot_df).mark_circle(
        size=45
    ).encode(
        x=alt.X("Sample_Index:Q", title="Timestamp / Sample Sequence"),
        y=alt.Y(
            "Health_Level:O",
            title="Predicted Health State",
            axis=alt.Axis(
                values=[0, 1, 2],
                labelExpr="datum.value == 0 ? 'Healthy' : datum.value == 1 ? 'Warning' : 'Degraded'"
            )
        ),
        color=alt.Color(
            "Health_Label:N",
            scale=alt.Scale(
                domain=["Healthy", "Warning", "Degraded"],
                range=["#00E676", "#FFD600", "#FF9100"]
            ),
            legend=alt.Legend(title="Health State")
        ),
        tooltip=[
            alt.Tooltip("Sample_Index:Q", title="Sample #"),
            alt.Tooltip("Health_Label:N", title="Health State")
        ]
    )
    return apply_dark_theme(chart)


def create_normalized_indicators_chart(df: pd.DataFrame) -> alt.Chart:
    """
    Graph 7: Normalized FPGA Health Indicators.
    Normalizes:
    - Temperature (0 to 1)
    - RO Frequency Degradation (inverted: 0 at max freq, 1 at min freq)
    - RO Delay Increase (0 at min delay, 1 at max delay)
    - Functional Error Rate (0 to 1)
    """
    plot_df = pd.DataFrame()
    plot_df["Sample_Index"] = df.reset_index().index

    def min_max_norm(series: pd.Series, invert: bool = False) -> pd.Series:
        s_min, s_max = series.min(), series.max()
        if s_max == s_min:
            return pd.Series(0.0, index=series.index)
        norm = (series - s_min) / (s_max - s_min)
        return (1.0 - norm) if invert else norm

    norm_temp = min_max_norm(df["Temperature"])
    norm_ro_deg = min_max_norm(df["RO_Frequency"], invert=True)
    norm_delay = min_max_norm(df["RO_Delay_ns"])
    norm_error = min_max_norm(df["Error_Rate"])

    melted = pd.DataFrame({
        "Sample_Index": plot_df["Sample_Index"],
        "Normalized Temperature": norm_temp.values,
        "RO Frequency Degradation": norm_ro_deg.values,
        "RO Delay Increase": norm_delay.values,
        "Functional Error Rate": norm_error.values
    }).melt(
        id_vars=["Sample_Index"],
        var_name="Indicator",
        value_name="Normalized_Value"
    )

    chart = alt.Chart(melted).mark_line(
        strokeWidth=2.0
    ).encode(
        x=alt.X("Sample_Index:Q", title="Timestamp / Sample Sequence"),
        y=alt.Y(
            "Normalized_Value:Q",
            title="Normalized Indicator Index (0.0 to 1.0)",
            scale=alt.Scale(domain=[0.0, 1.0])
        ),
        color=alt.Color(
            "Indicator:N",
            scale=alt.Scale(
                domain=[
                    "Normalized Temperature",
                    "RO Frequency Degradation",
                    "RO Delay Increase",
                    "Functional Error Rate"
                ],
                range=["#FF5252", "#00E5FF", "#D946EF", "#FFAB00"]
            ),
            legend=alt.Legend(title="Sensor Indicator", orient="top")
        ),
        tooltip=[
            alt.Tooltip("Sample_Index:Q", title="Sample #"),
            alt.Tooltip("Indicator:N", title="Indicator"),
            alt.Tooltip("Normalized_Value:Q", title="Score", format=".3f")
        ]
    )
    return apply_dark_theme(chart)


def create_feature_importance_chart(features: List[str], importances: np.ndarray, top_n: int = 8) -> alt.Chart:
    """Top Feature Importance horizontal bar chart."""
    pairs = sorted(zip(features, importances), key=lambda x: x[1], reverse=True)[:top_n]
    feat_df = pd.DataFrame(pairs, columns=["Feature", "Importance"])
    feat_df["Feature"] = feat_df["Feature"].str.replace("_", " ")

    chart = alt.Chart(feat_df).mark_bar(
        color="#00E5FF",
        cornerRadiusTopRight=4,
        cornerRadiusBottomRight=4
    ).encode(
        y=alt.Y("Feature:N", sort="-x", title="Telemetry Feature"),
        x=alt.X("Importance:Q", title="Relative Feature Importance Weight"),
        tooltip=[
            alt.Tooltip("Feature:N", title="Feature"),
            alt.Tooltip("Importance:Q", title="Weight", format=".4f")
        ]
    )
    return apply_dark_theme(chart)
