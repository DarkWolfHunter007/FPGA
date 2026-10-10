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
from dashboard.config import REGIONAL_CONFIG
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

    @unittest.expectedFailure
    def test_r2_critical_with_low_baseline_inconsistency_regression(self):
        """
        REGRESSION TEST:
        Demonstrates the confirmed bug where an R2 measured frequency around 322.1 MHz
        is evaluated against a low baseline of 322.20 MHz (drift = -0.03%).
        Because its drift is near zero, the current regional map incorrectly declares R2
        as Healthy, even though 322.1 MHz violates the critical boundary of 411.8 MHz.
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
        self.assertNotEqual(
            r2["state"],
            "Healthy",
            "Bug reproduced: R2 is falsely marked Healthy because drift from 322.2 MHz is near zero, "
            "ignoring the hard critical boundary (411.8 MHz)."
        )
        self.assertEqual(r2["state"], "Degraded")

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


if __name__ == "__main__":
    unittest.main()
