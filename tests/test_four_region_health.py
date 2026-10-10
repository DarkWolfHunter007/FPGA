"""
Tests for Four-Region Physical Health Architecture & Regional Map Rendering
"""

import unittest
from dashboard.health_map import (
    generate_four_region_data,
    render_four_region_map_html,
    calculate_aggregate_risk_score,
    REGIONAL_DEFAULTS
)
import math
from dashboard.config import (
    REGIONAL_CONFIG,
    HEALTH_COLORS,
    STATUS_BG_COLORS,
    LimitSeverity,
    evaluate_regional_health,
    validate_regional_baseline,
    evaluate_engineering_limits,
    determine_final_health
)
from dashboard.data_source import (
    MockCSVDataSource,
    LiveSimulationDataSource,
    LiveUARTDataSource,
    EstimatedDataSource
)


class TestFourRegionHealth(unittest.TestCase):

    def test_regional_defaults_and_config_consistency(self):
        """Verify that all four physical regions R1..R4 are present with valid metadata."""
        for r_key in ["R1", "R2", "R3", "R4"]:
            self.assertIn(r_key, REGIONAL_CONFIG)
            self.assertIn(r_key, REGIONAL_DEFAULTS)
            cfg = REGIONAL_CONFIG[r_key]
            self.assertIn("nominal_freq", cfg)
            self.assertIn("nominal_delay_ns", cfg)
            self.assertGreater(cfg["nominal_freq"], 400.0)
            self.assertLess(cfg["nominal_delay_ns"], 0.3)
            self.assertTrue(cfg["pblock"].startswith("pblock_"))
            self.assertTrue(cfg["clock_region"].startswith("X"))

    def test_generate_four_region_data_nominal(self):
        """Nominal telemetry produces Healthy state across all four quadrants."""
        telemetry = {
            "RO_Frequency": 436.0,
            "RO_R1": 436.3,
            "RO_R2": 435.8,
            "RO_R3": 436.1,
            "RO_R4": 435.9,
            "Temperature": 35.8,
            "VCCINT": 1.000,
            "Error_Rate": 0.0
        }
        regions = generate_four_region_data(telemetry)
        self.assertEqual(len(regions), 4)

        for r in regions:
            self.assertEqual(r["state"], "Healthy")
            self.assertAlmostEqual(r["drift_pct"], 0.0, delta=0.5)
            self.assertGreater(r["delay_ns"], 0.20)
            self.assertLess(r["delay_ns"], 0.25)

    def test_generate_four_region_data_degraded_quadrant(self):
        """Simulate R4 experiencing localized thermal/aging degradation."""
        telemetry = {
            "RO_Frequency": 436.0,
            "RO_R1": 436.3,
            "RO_R2": 435.8,
            "RO_R3": 436.1,
            "RO_R4": 410.0,  # Dropped from 435.9 by ~6%
            "Temperature": 42.0,
            "VCCINT": 0.995,
            "Error_Rate": 0.00001
        }
        regions = generate_four_region_data(telemetry)
        r4 = next(r for r in regions if r["id"] == "R4")
        self.assertEqual(r4["state"], "Degraded")
        self.assertLess(r4["drift_pct"], -5.5)

        r1 = next(r for r in regions if r["id"] == "R1")
        self.assertEqual(r1["state"], "Healthy")

    def test_r2_critical_with_low_baseline_inconsistency_regression(self):
        """
        REGRESSION TEST (Resolved):
        Demonstrates that an R2 measured frequency around 322.1 MHz evaluated against
        a low baseline of 322.20 MHz (drift = -0.03%) is correctly classified as Degraded
        because 322.1 MHz violates the authoritative critical boundary (411.8 MHz).
        Hard engineering limits take precedence over small baseline drift.
        """
        telemetry = {
            "RO_Frequency": 322.3,
            "RO_R1": 436.3,
            "RO_R2": 322.1,  # Critical violation (configured critical boundary is 411.8 MHz)
            "RO_R3": 436.1,
            "RO_R4": 435.9,
            "Temperature": 35.0,
            "VCCINT": 1.000,
            "Error_Rate": 0.00001
        }
        regional_baselines = {
            "RO_R1": 436.3,
            "RO_R2": 322.20,  # Erroneously accepted degraded baseline
            "RO_R3": 436.1,
            "RO_R4": 435.9
        }
        regions = generate_four_region_data(telemetry, regional_baselines=regional_baselines)
        r2 = next(r for r in regions if r["id"] == "R2")

        # R2 must NOT be Healthy when 322.1 MHz violates the critical limit (411.8 MHz)
        self.assertNotEqual(r2["state"], "Healthy")
        self.assertEqual(r2["state"], "Degraded")
        self.assertIn("Below critical boundary", r2["indicator"])
        self.assertEqual(r2["critical_freq"], 411.8)

    def test_render_four_region_map_html(self):
        """Verify HTML generation produces 2x2 grid with quadrant details."""
        telemetry = {
            "RO_Frequency": 436.0,
            "RO_R1": 436.3,
            "RO_R2": 435.8,
            "RO_R3": 436.1,
            "RO_R4": 435.9
        }
        regions = generate_four_region_data(telemetry)
        html = render_four_region_map_html(regions, composite_risk=0.12)

        self.assertIn("R1", html)
        self.assertIn("R2", html)
        self.assertIn("R3", html)
        self.assertIn("R4", html)
        self.assertIn("Northwest (NW)", html)
        self.assertIn("Northeast (NE)", html)
        self.assertIn("Southwest (SW)", html)
        self.assertIn("Southeast (SE)", html)
        self.assertIn("pblock_R1", html)
        self.assertIn("pblock_R4", html)

    def test_data_sources_provide_regional_telemetry(self):
        """Verify that simulation and estimated data sources output regional fields."""
        sim = LiveSimulationDataSource()
        hist, latest, meta = sim.get_data()
        self.assertIn("RO_R1", latest)
        self.assertIn("RO_R4", latest)
        self.assertIn("regional_baselines", meta)

        est = EstimatedDataSource({"RO_Frequency": 436.0})
        hist_e, latest_e, meta_e = est.get_data()
        self.assertIn("RO_R1", latest_e)
        self.assertIn("RO_R4", latest_e)
        self.assertIn("regional_baselines", meta_e)

    def test_r2_healthy_case(self):
        """A valid reading inside the healthy operating envelope remains Healthy."""
        telemetry = {
            "RO_Frequency": 435.8,
            "RO_R1": 436.3,
            "RO_R2": 435.8,  # Nominal frequency
            "RO_R3": 436.1,
            "RO_R4": 435.9,
            "Temperature": 35.0,
            "VCCINT": 1.000,
            "Error_Rate": 0.00001
        }
        regions = generate_four_region_data(telemetry)
        r2 = next(r for r in regions if r["id"] == "R2")
        self.assertEqual(r2["state"], "Healthy")
        self.assertEqual(r2["severity"], LimitSeverity.NORMAL)
        self.assertEqual(r2["indicator"], "Nominal Timing Propagation")
        self.assertAlmostEqual(r2["drift_pct"], 0.0, places=1)

    def test_r2_warning_case(self):
        """A reading violating warning boundary (422.7 MHz) but above critical (411.8 MHz) produces Warning."""
        telemetry = {
            "RO_Frequency": 420.0,
            "RO_R1": 436.3,
            "RO_R2": 420.0,  # Below warning boundary 422.7 MHz, above critical 411.8 MHz
            "RO_R3": 436.1,
            "RO_R4": 435.9,
            "Temperature": 35.0,
            "VCCINT": 1.000,
            "Error_Rate": 0.00001
        }
        regions = generate_four_region_data(telemetry)
        r2 = next(r for r in regions if r["id"] == "R2")
        self.assertEqual(r2["state"], "Warning")
        self.assertEqual(r2["severity"], LimitSeverity.WARNING)
        self.assertIn("Below warning boundary", r2["indicator"])
        self.assertEqual(r2["warning_freq"], 422.7)

    def test_critical_precedence_over_small_drift(self):
        """A critical boundary violation unconditionally takes precedence over small baseline drift."""
        # Even if a baseline of 322.2 MHz is artificially supplied:
        res = evaluate_regional_health("R2", measurement=322.1, baseline_freq=322.20)
        self.assertEqual(res["state"], "Degraded")
        self.assertEqual(res["severity"], LimitSeverity.CRITICAL)
        self.assertIn("Below critical boundary", res["indicator"])
        # Drift must still be reported accurately as a separate diagnostic metric
        self.assertAlmostEqual(res["current_freq"], 322.1, places=1)
        self.assertIn("critical_boundary", res)

    def test_invalid_and_missing_data_not_healthy(self):
        """Missing, nonnumeric, non-finite, or implausible measurements must NEVER produce Healthy."""
        invalid_cases = [
            None,
            "INVALID_CORRUPTED",
            float("nan"),
            float("inf"),
            -50.0,    # Physically impossible
            950.0     # Physically impossible
        ]
        for bad_val in invalid_cases:
            res = evaluate_regional_health("R2", measurement=bad_val)
            self.assertNotEqual(
                res["state"],
                "Healthy",
                f"Invalid measurement {bad_val} was falsely marked Healthy!"
            )
            self.assertEqual(res["state"], "Degraded")
            self.assertEqual(res["severity"], LimitSeverity.PHYSICALLY_INVALID)
            self.assertFalse(res["is_valid"])

    def test_baseline_validation_rejects_unhealthy_baseline(self):
        """An invalid or unhealthy baseline cannot silently establish a healthy status."""
        # Baseline near 322.2 MHz is severely degraded and must be rejected
        is_valid, chosen_base, src, reason = validate_regional_baseline("R2", 322.20)
        self.assertFalse(is_valid)
        self.assertEqual(chosen_base, 435.8)  # Fell back to factory nominal
        self.assertEqual(src, "FACTORY_NOMINAL_FALLBACK")
        self.assertIn("Unhealthy baseline", reason)

        # Non-numeric baseline must be rejected
        is_v_str, chosen_str, src_str, _ = validate_regional_baseline("R2", "bad_base")
        self.assertFalse(is_v_str)
        self.assertEqual(chosen_str, 435.8)

        # Legitimate healthy calibrated baseline must be accepted
        is_v_cal, chosen_cal, src_cal, _ = validate_regional_baseline("R2", 434.5)
        self.assertTrue(is_v_cal)
        self.assertEqual(chosen_cal, 434.5)
        self.assertEqual(src_cal, "CALIBRATED_BOARD")

    def test_overall_engineering_assessment_reflects_degraded_r2(self):
        """A Degraded R2 region is correctly reflected in the overall engineering assessment."""
        telemetry = {
            "RO_Frequency": 436.0,
            "RO_R1": 436.3,
            "RO_R2": 322.1,  # Critical boundary violation
            "RO_R3": 436.1,
            "RO_R4": 435.9,
            "Temperature": 35.0,
            "VCCINT": 1.000,
            "VCCAUX": 1.800,
            "VCCBRAM": 1.000,
            "Error_Rate": 0.00001
        }
        assessment = evaluate_engineering_limits(telemetry)
        self.assertEqual(assessment.max_severity, LimitSeverity.CRITICAL)
        self.assertEqual(assessment.worst_region, "R2")
        self.assertTrue(assessment.has_hard_violations)
        self.assertIn("Region 2 (R2)", assessment.primary_reason)

        final_res = determine_final_health("Warning", 0.48, assessment)
        self.assertEqual(final_res["final_health"], "Degraded")
        self.assertTrue(final_res["override_applied"])

    def test_regional_display_consistency(self):
        """Regional status label, status color, background, and indicator agree."""
        res_h = evaluate_regional_health("R1", 436.3)
        self.assertEqual(res_h["state"], "Healthy")
        self.assertEqual(res_h["color"], HEALTH_COLORS["Healthy"])
        self.assertEqual(res_h["bg"], STATUS_BG_COLORS["Healthy"])

        res_w = evaluate_regional_health("R2", 420.0)
        self.assertEqual(res_w["state"], "Warning")
        self.assertEqual(res_w["color"], HEALTH_COLORS["Warning"])
        self.assertEqual(res_w["bg"], STATUS_BG_COLORS["Warning"])

        res_d = evaluate_regional_health("R2", 322.1)
        self.assertEqual(res_d["state"], "Degraded")
        self.assertEqual(res_d["color"], HEALTH_COLORS["Degraded"])
        self.assertEqual(res_d["bg"], STATUS_BG_COLORS["Degraded"])

    def test_telemetry_provenance_explicit(self):
        """Synthetic or derived regional values are not represented as verified physical measurements."""
        telemetry = {"RO_Frequency": 436.0}  # No regional fields
        regions = generate_four_region_data(telemetry)
        for r in regions:
            self.assertEqual(r["provenance"], "DERIVED_GLOBAL")
            self.assertNotEqual(r["provenance"], "MEASURED")


if __name__ == "__main__":
    unittest.main()

