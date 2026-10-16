"""
Regression tests for the "false Degraded" problem on the physical Basys 3 board.

Ring-oscillator frequency is dominated by placement/routing. On the real board R2 reads
~322 MHz while R1/R3/R4 read ~440 MHz on a perfectly healthy die. These tests pin the
fix: each region is judged by drift from its OWN start-up baseline, the baseline is
captured per region from a clean + stable window, and genuine aging is still caught.
"""

import sys
import unittest
from pathlib import Path
from unittest import mock

import joblib
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import dashboard.config as dashboard_config
from dashboard.config import (
    LimitSeverity,
    calibrate_history_dataframe,
    determine_final_health,
    evaluate_engineering_limits,
    evaluate_regional_health,
)
from dashboard.data_source import LiveUARTDataSource
from dashboard.health_map import generate_four_region_data, render_four_region_map_html

MODEL_PATH = PROJECT_ROOT / "ml" / "models" / "fpga_health_model.pkl"

# What the physical board actually reports when healthy (see report.md, COM10 stream)
REAL_BOARD = {"RO_R1": 439.4, "RO_R2": 321.8, "RO_R3": 441.1, "RO_R4": 439.8}


def make_packet(i, regions=None, temperature=37.3):
    """One simulated UART packet with a tiny deterministic jitter (+/- 0.1 MHz)."""
    regions = dict(regions or REAL_BOARD)
    jitter = 0.1 * ((i % 3) - 1)
    pkt = {k: round(v + jitter, 2) for k, v in regions.items()}
    mean = sum(pkt.values()) / 4.0
    pkt.update({
        "Timestamp": 1000.0 + i,
        "Temperature": temperature,
        "VCCINT": 1.002,
        "VCCAUX": 1.798,
        "VCCBRAM": 1.001,
        "RO_Frequency": round(mean, 2),
        "RO_Delay_ns": round(100.0 / mean, 4),
        "Error_Rate": 0.0,
    })
    return pkt


def feed(ds, packets):
    """Push packets through LiveUARTDataSource.poll_hardware like the real receiver would."""
    queue = list(packets)
    ds.receiver.read_packet = lambda: queue.pop(0) if queue else None
    ds.poll_hardware()


class TestUartCalibrationOnRealBoardProfile(unittest.TestCase):
    def setUp(self):
        self.ds = LiveUARTDataSource(port="COM3", buffer_size=200)

    def test_r2_placement_offset_is_calibrated_not_replaced_by_436(self):
        feed(self.ds, [make_packet(i) for i in range(30)])

        self.assertFalse(self.ds._baseline_is_fallback)
        base = self.ds.baseline_sample
        self.assertAlmostEqual(base["RO_R2"], 321.8, delta=0.5)
        self.assertAlmostEqual(base["RO_R1"], 439.4, delta=0.5)

        history_df, latest, meta = self.ds.get_data(window_size=150)
        self.assertAlmostEqual(meta["regional_baselines"]["RO_R2"], 321.8, delta=0.5)

        assessment = evaluate_engineering_limits(
            latest.to_dict(), regional_baselines=meta["regional_baselines"]
        )
        self.assertEqual(assessment.max_severity, LimitSeverity.NORMAL)
        self.assertEqual(assessment.degraded_pblocks, [])
        self.assertEqual(assessment.warning_pblocks, [])

        regions = generate_four_region_data(latest.to_dict(), meta["regional_baselines"])
        self.assertTrue(all(r["state"] == "Healthy" for r in regions), [r["state"] for r in regions])
        html = render_four_region_map_html(regions, composite_risk=0.1)
        self.assertIn("placement offset", html)  # the offset stays visible, not silent

    def test_ml_sees_healthy_after_baseline_normalisation(self):
        if not MODEL_PATH.exists():
            self.skipTest("ML model bundle not available.")
        bundle = joblib.load(MODEL_PATH)
        model, features = bundle["model"], bundle["features"]

        feed(self.ds, [make_packet(i) for i in range(40)])
        history_df, latest, meta = self.ds.get_data(window_size=150)

        calibrated = calibrate_history_dataframe(
            history_df, regional_baselines=meta["regional_baselines"]
        )
        # Overall RO series sits on the factory-nominal scale for a healthy board
        self.assertAlmostEqual(calibrated["RO_Frequency"].iloc[-1], 436.0, delta=1.0)
        self.assertAlmostEqual(calibrated["RO_Raw_Frequency"].iloc[-1], 410.5, delta=1.0)

        pred = str(model.predict(calibrated[features])[-1])
        self.assertEqual(pred, "Healthy")

        assessment = evaluate_engineering_limits(
            latest.to_dict(), regional_baselines=meta["regional_baselines"]
        )
        final = determine_final_health(pred, 0.9, assessment)
        self.assertEqual(final["final_health"], "Healthy")
        self.assertFalse(final["override_applied"])

    def test_real_aging_after_calibration_is_still_caught(self):
        feed(self.ds, [make_packet(i) for i in range(30)])
        aged = dict(REAL_BOARD, RO_R2=300.0)  # -6.8% vs R2's own baseline
        feed(self.ds, [make_packet(i, aged) for i in range(30, 40)])

        _, latest, meta = self.ds.get_data(window_size=150)
        regions = generate_four_region_data(latest.to_dict(), meta["regional_baselines"])
        by_id = {r["id"]: r for r in regions}
        self.assertEqual(by_id["R2"]["state"], "Degraded")
        self.assertLess(by_id["R2"]["drift_pct"], -5.5)
        for rid in ("R1", "R3", "R4"):
            self.assertEqual(by_id[rid]["state"], "Healthy")

    def test_unhealthy_start_does_not_lock_in_factory_nominal_and_retries(self):
        # Boot while the die is far too hot: baseline must not be taken from this window
        feed(self.ds, [make_packet(i, temperature=60.0) for i in range(6)])
        self.assertTrue(self.ds._baseline_is_fallback)
        self.assertEqual(self.ds.baseline_sample["RO_R2"], 436.0)

        # Once the board settles, calibration is retried and succeeds
        feed(self.ds, [make_packet(i, temperature=37.3) for i in range(6, 16)])
        self.assertFalse(self.ds._baseline_is_fallback)
        self.assertAlmostEqual(self.ds.baseline_sample["RO_R2"], 321.8, delta=0.5)
        self.assertAlmostEqual(self.ds.baseline_sample["Temperature"], 37.3, delta=0.2)

    def test_unstable_start_window_is_not_used_as_baseline(self):
        wobble = []
        for i in range(5):
            r2 = 300.0 if i % 2 == 0 else 335.0  # >10% spread inside the window
            wobble.append(make_packet(i, dict(REAL_BOARD, RO_R2=r2)))
        feed(self.ds, wobble)
        self.assertTrue(self.ds._baseline_is_fallback)
        self.assertEqual(self.ds.baseline_sample["RO_R2"], 436.0)

    def test_reset_clears_calibration_state(self):
        feed(self.ds, [make_packet(i) for i in range(10)])
        self.ds.reset()
        self.assertIsNone(self.ds.baseline_sample)
        self.assertFalse(self.ds._baseline_is_fallback)
        self.assertEqual(self.ds.buffer, [])


class TestRegionalLimitsFollowBaseline(unittest.TestCase):
    def test_limits_scale_with_baseline_and_match_legacy_at_nominal(self):
        nominal = evaluate_regional_health("R1", 436.0, baseline_freq=436.0)
        self.assertEqual(nominal["warning_freq"], 422.9)
        self.assertEqual(nominal["critical_freq"], 412.0)

        slow = evaluate_regional_health("R2", 321.8, baseline_freq=321.8)
        self.assertAlmostEqual(slow["warning_freq"], 422.9 * 321.8 / 436.0, delta=0.1)
        self.assertAlmostEqual(slow["critical_freq"], 412.0 * 321.8 / 436.0, delta=0.1)
        self.assertEqual(slow["state"], "Healthy")

    def test_over_frequency_is_relative_to_baseline_too(self):
        # A fast, compactly-placed oscillator (baseline 480 MHz) is not "over-frequency"...
        self.assertEqual(evaluate_regional_health("R3", 482.0, baseline_freq=480.0)["state"], "Healthy")
        # ...but +6% from its own baseline is.
        self.assertEqual(evaluate_regional_health("R3", 510.0, baseline_freq=480.0)["state"], "Degraded")

    def test_halted_or_dead_oscillator_is_still_invalid(self):
        for dead in (0.0, 3.0):
            res = evaluate_regional_health("R2", dead, baseline_freq=321.8)
            self.assertEqual(res["state"], "Degraded")
            self.assertEqual(res["severity"], LimitSeverity.PHYSICALLY_INVALID)

    def test_quorum_threshold_is_configurable(self):
        base = dict(REAL_BOARD)
        telemetry = dict(base, RO_R2=300.0, Temperature=37.3, VCCINT=1.002,
                         VCCAUX=1.798, VCCBRAM=1.001, Error_Rate=0.0)
        telemetry["RO_Frequency"] = sum(telemetry[k] for k in base) / 4.0
        baselines = dict(base)

        # Default quorum (2): an isolated aged region does not change the overall status
        self.assertEqual(dashboard_config.REGIONAL_QUORUM_MIN, 2)
        isolated = evaluate_engineering_limits(telemetry, regional_baselines=baselines)
        self.assertEqual(isolated.degraded_pblocks, ["R2"])
        self.assertEqual(isolated.max_severity, LimitSeverity.NORMAL)

        # Quorum 1: any single critical region makes the overall status Degraded
        with mock.patch.object(dashboard_config, "REGIONAL_QUORUM_MIN", 1):
            strict = evaluate_engineering_limits(telemetry, regional_baselines=baselines)
        self.assertEqual(strict.max_severity, LimitSeverity.CRITICAL)
        self.assertTrue(strict.quorum_triggered)
        self.assertTrue(any("Single-pblock" in r for r in strict.override_reasons))


if __name__ == "__main__":
    unittest.main(verbosity=2)
