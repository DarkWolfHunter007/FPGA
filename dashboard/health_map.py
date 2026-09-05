"""
FPGA Health Risk Map Generator (Dynamic Logic Array Grid)
=========================================================
Generates a 5x5 (25-cell) deterministic health-risk matrix visualization
derived from overall degradation score, model confidence, and thermal/RO indicators.

Explicit Research Note:
This map visualizes aggregate health-risk metrics derived from system-level
monitoring and does NOT represent separate physical sensor partitions on silicon.
"""

import textwrap
from typing import List, Dict, Any
from dashboard.config import HEALTH_COLORS, STATUS_BG_COLORS


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


def generate_risk_cells(risk_score: float) -> List[Dict[str, Any]]:
    """
    Deterministically generates 25 grid cells (5x5) based on composite risk score.
    Higher risk smoothly propagates from center/logic cluster across the virtual matrix.
    """
    spatial_weights = [
        0.70, 0.75, 0.80, 0.75, 0.70,
        0.75, 0.88, 0.95, 0.88, 0.75,
        0.80, 0.95, 1.00, 0.95, 0.80,
        0.75, 0.88, 0.95, 0.88, 0.75,
        0.70, 0.75, 0.80, 0.75, 0.70
    ]

    cells = []
    for idx, weight in enumerate(spatial_weights):
        cell_risk = risk_score * weight

        if cell_risk < 0.32:
            state = "Healthy"
            color = HEALTH_COLORS["Healthy"]
            bg = STATUS_BG_COLORS["Healthy"]
            border = "rgba(0, 230, 118, 0.35)"
        elif cell_risk < 0.62:
            state = "Warning"
            color = HEALTH_COLORS["Warning"]
            bg = STATUS_BG_COLORS["Warning"]
            border = "rgba(255, 214, 0, 0.4)"
        elif cell_risk < 0.84:
            state = "Degraded"
            color = HEALTH_COLORS["Degraded"]
            bg = STATUS_BG_COLORS["Degraded"]
            border = "rgba(255, 145, 0, 0.45)"
        else:
            state = "Critical"
            color = HEALTH_COLORS["Critical"]
            bg = STATUS_BG_COLORS["Critical"]
            border = "rgba(255, 23, 68, 0.55)"

        row = idx // 5 + 1
        col = idx % 5 + 1
        cells.append({
            "id": f"L{row}{col}",
            "label": f"CLB-{row}{col}",
            "state": state,
            "risk_val": round(cell_risk, 2),
            "color": color,
            "bg": bg,
            "border": border
        })

    return cells


def render_health_risk_map_html(cells: List[Dict[str, Any]], composite_risk: float) -> str:
    """Generates full-width card container with compact centered 5x5 cubes."""
    grid_items = []
    for cell in cells:
        grid_items.append(f'<div class="risk-cell" style="background-color: {cell["bg"]}; border-color: {cell["border"]}; color: {cell["color"]};"><span class="risk-cell-label">{cell["label"]}</span><span>{cell["state"][:4].upper()}</span></div>')

    grid_html = "".join(grid_items)

    return textwrap.dedent(f"""
<div class="risk-map-container">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
        <span style="font-size: 0.95rem; font-weight: 600; color: #E2E8F0;">Virtual Logic Health Matrix (5 × 5 Cluster)</span>
        <span style="font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; color: #00E5FF; font-weight: 700;">
            Composite Risk Index: {composite_risk * 100:.1f} %
        </span>
    </div>
    
    <div class="risk-grid-wrapper">
        <div class="risk-grid">
            {grid_html}
        </div>
    </div>
    
    <!-- Legend -->
    <div style="display: flex; justify-content: center; gap: 16px; margin-top: 10px; flex-wrap: wrap; font-size: 0.78rem; font-family: 'JetBrains Mono', monospace;">
        <span style="color: {HEALTH_COLORS['Healthy']}; display: flex; align-items: center; gap: 4px;">
            <span style="display: inline-block; width: 10px; height: 10px; background: {HEALTH_COLORS['Healthy']}; border-radius: 2px;"></span> Healthy (&lt;32%)
        </span>
        <span style="color: {HEALTH_COLORS['Warning']}; display: flex; align-items: center; gap: 4px;">
            <span style="display: inline-block; width: 10px; height: 10px; background: {HEALTH_COLORS['Warning']}; border-radius: 2px;"></span> Warning (32–62%)
        </span>
        <span style="color: {HEALTH_COLORS['Degraded']}; display: flex; align-items: center; gap: 4px;">
            <span style="display: inline-block; width: 10px; height: 10px; background: {HEALTH_COLORS['Degraded']}; border-radius: 2px;"></span> Degraded (62–84%)
        </span>
        <span style="color: {HEALTH_COLORS['Critical']}; display: flex; align-items: center; gap: 4px;">
            <span style="display: inline-block; width: 10px; height: 10px; background: {HEALTH_COLORS['Critical']}; border-radius: 2px;"></span> Critical (&gt;84%)
        </span>
    </div>
    
    <div class="science-callout" style="margin-top: 12px; margin-bottom: 0;">
        <strong>Scientific Methodology Disclaimer:</strong> Visualization of health-risk indicators derived from the overall FPGA monitoring data. It does not represent independent physical sensor regions.
    </div>
</div>
""").strip()
