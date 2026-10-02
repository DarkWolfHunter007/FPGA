"""
FPGA Physical Four-Region Health Architecture & Regional Map Generator
======================================================================
Replaces the conceptual 5x5 virtual matrix with a physical 2x2 regional
representation reflecting the four physically constrained hardware quadrants:
  - R1: Northwest (NW) — Clock Region X0Y2, Pblock pblock_R1
  - R2: Northeast (NE) — Clock Region X1Y2, Pblock pblock_R2
  - R3: Southwest (SW) — Clock Region X0Y0, Pblock pblock_R3
  - R4: Southeast (SE) — Clock Region X1Y0, Pblock pblock_R4

Physically Honest Fault Model:
  Ring Oscillator telemetry measures live gate propagation delay, thermal drift,
  and transistor aging. It does NOT claim to detect arbitrary single-LUT stuck-at
  faults. Configuration memory errors are managed via CRC/SEM, while functional
  data-path errors are tracked via the independent PRBS-7 error rate monitor.
"""

import textwrap
from typing import List, Dict, Any, Optional
from config import calculate_ro_delay_ns, RO_STAGES
from dashboard.config import HEALTH_COLORS, STATUS_BG_COLORS

# Default nominal benchmarks per region from physical Basys 3 telemetry
REGIONAL_DEFAULTS = {
    "R1": {
        "id": "R1",
        "name": "Region 1 (R1)",
        "quadrant": "Northwest (NW)",
        "clock_region": "X0Y2",
        "pblock": "pblock_R1",
        "slice_range": "SLICE_X0Y100:SLICE_X35Y149",
        "nominal_freq": 436.3,
        "nominal_delay_ns": 0.2292
    },
    "R2": {
        "id": "R2",
        "name": "Region 2 (R2)",
        "quadrant": "Northeast (NE)",
        "clock_region": "X1Y2",
        "pblock": "pblock_R2",
        "slice_range": "SLICE_X36Y100:SLICE_X57Y149",
        "nominal_freq": 435.8,
        "nominal_delay_ns": 0.2295
    },
    "R3": {
        "id": "R3",
        "name": "Region 3 (R3)",
        "quadrant": "Southwest (SW)",
        "clock_region": "X0Y0",
        "pblock": "pblock_R3",
        "slice_range": "SLICE_X0Y0:SLICE_X35Y49",
        "nominal_freq": 436.1,
        "nominal_delay_ns": 0.2293
    },
    "R4": {
        "id": "R4",
        "name": "Region 4 (R4)",
        "quadrant": "Southeast (SE)",
        "clock_region": "X1Y0",
        "pblock": "pblock_R4",
        "slice_range": "SLICE_X36Y0:SLICE_X65Y49",
        "nominal_freq": 435.9,
        "nominal_delay_ns": 0.2294
    }
}


def calculate_aggregate_risk_score(
    health_pred: str,
    confidence: float,
    temp: float,
    ro_freq_shift_pct: float,
    error_rate: float
) -> float:
    """
    Computes a continuous aggregate risk score in range [0.0, 1.0].
    0.0 = completely pristine / healthy baseline
    1.0 = maximum degradation / critical risk
    """
    base_scores = {"Healthy": 0.15, "Warning": 0.50, "Degraded": 0.85, "Critical": 0.95}
    score = base_scores.get(health_pred, 0.15)

    temp_factor = min(1.0, max(0.0, (temp - 35.0) / 20.0))
    ro_factor = min(1.0, max(0.0, abs(min(0.0, ro_freq_shift_pct)) / 6.5))
    err_factor = min(1.0, max(0.0, error_rate / 0.003))

    composite_risk = (
        0.45 * score +
        0.20 * temp_factor +
        0.20 * ro_factor +
        0.15 * err_factor
    )
    return round(min(1.0, max(0.0, composite_risk)), 3)


def generate_four_region_data(
    telemetry: Dict[str, Any],
    regional_baselines: Optional[Dict[str, float]] = None
) -> List[Dict[str, Any]]:
    """
    Generates structured physical telemetry and health assessment for the four
    constrained FPGA regions (R1 Northwest, R2 Northeast, R3 Southwest, R4 Southeast).
    Uses independent regional baselines to avoid forcing identical nominals.
    """
    baselines = regional_baselines or {}
    global_ro_freq = float(telemetry.get("RO_Frequency", 436.0))

    regions = []
    region_keys = ["R1", "R2", "R3", "R4"]

    for r_key in region_keys:
        meta = REGIONAL_DEFAULTS[r_key]
        
        # 1. Measured live frequency (with fallback to global RO)
        meas_freq = float(telemetry.get(f"RO_{r_key}", global_ro_freq))

        # 2. Independent baseline frequency
        base_freq = float(baselines.get(f"RO_{r_key}", meta["nominal_freq"]))

        # 3. Frequency drift from regional baseline
        drift_mhz = meas_freq - base_freq
        drift_pct = (drift_mhz / base_freq) * 100.0 if base_freq > 0 else 0.0

        # 4. Physical stage delay derivation: tau = 100 / f_MHz
        delay_ns = calculate_ro_delay_ns(meas_freq, stages=RO_STAGES)
        base_delay_ns = calculate_ro_delay_ns(base_freq, stages=RO_STAGES)
        delay_drift_pct = ((delay_ns - base_delay_ns) / base_delay_ns) * 100.0 if base_delay_ns > 0 else 0.0

        # 5. Regional Health State Evaluation (Independent Timing Thresholds)
        # Warning: Frequency drop > 3.0% (tau increase > 3.1%)
        # Degraded: Frequency drop > 5.5% (tau increase > 5.8%)
        if drift_pct <= -5.5:
            state = "Degraded"
            color = HEALTH_COLORS["Degraded"]
            bg = STATUS_BG_COLORS["Degraded"]
            border = "rgba(255, 145, 0, 0.55)"
            indicator = "Severe Aging Delay Degradation"
        elif drift_pct <= -3.0:
            state = "Warning"
            color = HEALTH_COLORS["Warning"]
            bg = STATUS_BG_COLORS["Warning"]
            border = "rgba(255, 214, 0, 0.5)"
            indicator = "Moderate Timing Drift / Thermal Load"
        else:
            state = "Healthy"
            color = HEALTH_COLORS["Healthy"]
            bg = STATUS_BG_COLORS["Healthy"]
            border = "rgba(0, 230, 118, 0.4)"
            indicator = "Nominal Timing Propagation"

        regions.append({
            "id": r_key,
            "name": meta["name"],
            "quadrant": meta["quadrant"],
            "clock_region": meta["clock_region"],
            "pblock": meta["pblock"],
            "slice_range": meta["slice_range"],
            "current_freq": round(meas_freq, 2),
            "baseline_freq": round(base_freq, 2),
            "drift_mhz": round(drift_mhz, 2),
            "drift_pct": round(drift_pct, 2),
            "delay_ns": round(delay_ns, 4),
            "baseline_delay_ns": round(base_delay_ns, 4),
            "delay_drift_pct": round(delay_drift_pct, 2),
            "state": state,
            "color": color,
            "bg": bg,
            "border": border,
            "indicator": indicator
        })

    return regions


def render_four_region_map_html(
    regions: List[Dict[str, Any]],
    composite_risk: float = 0.0
) -> str:
    """
    Renders an interactive high-tech 2x2 physical FPGA quadrant layout:
       ┌──────────────┬──────────────┐
       │ R1 Northwest │ R2 Northeast │
       ├──────────────┼──────────────┤
       │ R3 Southwest │ R4 Southeast │
       └──────────────┴──────────────┘
    """
    card_htmls = []
    for r in regions:
        drift_sign = "+" if r["drift_mhz"] >= 0 else ""
        delay_drift_sign = "+" if r["delay_drift_pct"] >= 0 else ""

        card_htmls.append(f"""
        <div style="
            background: {r['bg']};
            border: 1px solid {r['border']};
            border-radius: 8px;
            padding: 14px 16px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
            transition: transform 0.15s ease-in-out;
        ">
            <!-- Region Header -->
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 6px;">
                <div>
                    <strong style="font-size: 1.05rem; color: #FFFFFF; font-family: 'JetBrains Mono', monospace;">{r['id']}</strong>
                    <span style="color: #94A3B8; font-size: 0.85rem; margin-left: 6px;">{r['quadrant']}</span>
                </div>
                <span style="
                    background: {r['bg']};
                    color: {r['color']};
                    border: 1px solid {r['color']};
                    border-radius: 4px;
                    padding: 2px 8px;
                    font-size: 0.75rem;
                    font-weight: 700;
                    letter-spacing: 0.5px;
                ">
                    {r['state'].upper()}
                </span>
            </div>

            <!-- Key Metrics Grid -->
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 10px;">
                <div>
                    <div style="font-size: 0.72rem; color: #94A3B8; text-transform: uppercase;">Live Frequency</div>
                    <div style="font-size: 1.15rem; font-weight: 700; color: #F8FAFC; font-family: 'JetBrains Mono', monospace;">
                        {r['current_freq']:.2f} <span style="font-size: 0.75rem; color: #64748B;">MHz</span>
                    </div>
                    <div style="font-size: 0.72rem; color: #64748B;">Base: {r['baseline_freq']:.2f} MHz</div>
                </div>
                <div>
                    <div style="font-size: 0.72rem; color: #94A3B8; text-transform: uppercase;">Stage Delay (&tau;)</div>
                    <div style="font-size: 1.15rem; font-weight: 700; color: #38BDF8; font-family: 'JetBrains Mono', monospace;">
                        {r['delay_ns']:.4f} <span style="font-size: 0.75rem; color: #64748B;">ns</span>
                    </div>
                    <div style="font-size: 0.72rem; color: #64748B;">Shift: {delay_drift_sign}{r['delay_drift_pct']:.2f}%</div>
                </div>
            </div>

            <!-- Timing Drift & Physical Mapping -->
            <div style="font-size: 0.78rem; line-height: 1.4; color: #CBD5E1; margin-bottom: 6px;">
                <strong>Timing Drift:</strong> <span style="font-family: 'JetBrains Mono', monospace; color: {r['color']}; font-weight: 600;">{drift_sign}{r['drift_mhz']:.2f} MHz ({drift_sign}{r['drift_pct']:.2f}%)</span>
                <br/><strong>Physical Pblock:</strong> <code style="color: #F1F5F9; font-size: 0.72rem;">{r['pblock']} ({r['clock_region']})</code>
                <br/><strong>Silicon Coordinates:</strong> <code style="color: #64748B; font-size: 0.70rem;">{r['slice_range']}</code>
            </div>

            <!-- Indicator Badge -->
            <div style="font-size: 0.72rem; color: #94A3B8; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 6px;">
                Status: <span style="color: {r['color']}; font-weight: 600;">{r['indicator']}</span>
            </div>
        </div>
        """)

    grid_content = "\n".join(card_htmls)

    return textwrap.dedent(f"""
    <div style="background: rgba(15, 23, 42, 0.85); border: 1px solid #334155; border-radius: 10px; padding: 18px; margin: 12px 0;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
            <div>
                <strong style="font-size: 1.05rem; color: #F8FAFC;">Physical Four-Region FPGA Health Architecture</strong>
                <div style="font-size: 0.78rem; color: #94A3B8;">2&times;2 Spatially Constrained Ring-Oscillator Array (XC7A35T Artix-7)</div>
            </div>
            <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.82rem; color: #00E5FF; background: rgba(0, 229, 255, 0.1); border: 1px solid rgba(0, 229, 255, 0.25); border-radius: 4px; padding: 4px 10px;">
                Overall Risk Index: {composite_risk * 100:.1f} %
            </div>
        </div>

        <!-- 2x2 Physical Layout Grid -->
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
            {grid_content}
        </div>

        <!-- Physical Health Methodology Callout -->
        <div style="margin-top: 14px; padding: 10px 12px; background: rgba(30, 41, 59, 0.6); border-left: 3px solid #38BDF8; border-radius: 4px; font-size: 0.75rem; color: #94A3B8; line-height: 1.45;">
            <strong>Physically Honest Fault Model:</strong> Each regional monitor tracks gate delay (tau = 100 / f_MHz) within its constrained Pblock.
            RO frequency shift reflects regional NBTI/HCI aging, supply droop, or thermal variation. It does not indicate individual LUT stuck-at faults (addressed via PRBS-7 functional test).
        </div>
    </div>
    """).strip()


# Backward Compatibility Aliases for legacy imports
def generate_risk_cells(risk_score: float) -> List[Dict[str, Any]]:
    """Legacy alias: maps to four-region data format."""
    dummy_telemetry = {"RO_Frequency": 436.0}
    return generate_four_region_data(dummy_telemetry)


def render_health_risk_map_html(cells_or_regions: List[Dict[str, Any]], composite_risk: float = 0.0) -> str:
    """Legacy alias: renders four-region map html."""
    if cells_or_regions and "quadrant" in cells_or_regions[0]:
        return render_four_region_map_html(cells_or_regions, composite_risk)
    else:
        # Fallback to generating 4-region representation
        regions = generate_four_region_data({"RO_Frequency": 436.0})
        return render_four_region_map_html(regions, composite_risk)
