"""
Bit-accurate Python model of hardware/rtl/regional_baseline_checker.v

This is NOT a simulation of the Verilog source: it re-implements the same algorithm with the
same integer widths and thresholds so the arithmetic (overflow ranges, 1 % stability test,
3.0 % / 5.5 % limits, dead-oscillator rule) can be checked without a Verilog simulator.
Run the Vivado/xsim flow on the RTL itself to verify the Verilog.
"""

import unittest

MASK16 = (1 << 16) - 1
MASK23 = (1 << 23) - 1
MASK26 = (1 << 26) - 1


class RegionalBaselineCheckerModel:
    def __init__(self, settle_samples=8, warn_k=970, crit_k=945, min_valid=500):
        self.settle_samples = settle_samples
        self.warn_k = warn_k
        self.crit_k = crit_k
        self.min_valid = min_valid
        self.reset()

    def reset(self):
        self.settle_cnt = 0
        self.prev_freq = 0
        self.have_prev = False
        self.base_ready = False
        self.base = 0

    def valid_pulse(self, freq):
        """One cycle with i_freq_valid = 1 and i_freq_mhz_x10 = freq."""
        freq &= MASK16
        if self.base_ready:
            return
        if freq < self.min_valid:
            self.have_prev = False
            return
        diff = abs(freq - self.prev_freq) & MASK16
        stable = self.have_prev and ((diff * 100) & MASK23) <= freq
        if self.settle_cnt < self.settle_samples:
            self.settle_cnt += 1
            self.prev_freq = freq
            self.have_prev = True
        else:
            self.prev_freq = freq
            self.have_prev = True
            if stable:
                self.base = freq
                self.base_ready = True

    def outputs(self, freq):
        cur_x1000 = (freq * 1000) & MASK26
        warn_limit = (self.base * self.warn_k) & MASK26
        crit_limit = (self.base * self.crit_k) & MASK26
        degraded = self.base_ready and (freq < self.min_valid or cur_x1000 < crit_limit)
        warning = self.base_ready and not degraded and cur_x1000 < warn_limit
        return warning, degraded


def calibrate(model, freq, n=12):
    for _ in range(n):
        model.valid_pulse(freq)


class TestRegionalBaselineCheckerModel(unittest.TestCase):
    def test_arithmetic_never_overflows_its_registers(self):
        # Largest legal frequency word is 16 bits; every product must fit the declared widths
        self.assertLess(MASK16 * 1000, 1 << 26)
        self.assertLess(MASK16 * 970, 1 << 26)
        self.assertLess(MASK16 * 100, 1 << 23)

    def test_slow_region_calibrates_to_its_own_baseline_and_is_healthy(self):
        r2 = RegionalBaselineCheckerModel()
        calibrate(r2, 3218)  # 321.8 MHz - R2's placement-driven frequency on the real board
        self.assertTrue(r2.base_ready)
        self.assertEqual(r2.base, 3218)
        self.assertEqual(r2.outputs(3218), (False, False))   # healthy: no false red LED
        self.assertEqual(r2.outputs(3215), (False, False))   # measurement jitter

    def test_fast_region_unchanged(self):
        r3 = RegionalBaselineCheckerModel()
        calibrate(r3, 4412)
        self.assertEqual(r3.outputs(4412), (False, False))

    def test_drift_thresholds_are_relative_to_baseline(self):
        for base in (3218, 4360, 4412, 4800):
            m = RegionalBaselineCheckerModel()
            calibrate(m, base)
            self.assertEqual(m.outputs(int(base * 0.99)), (False, False), base)   # -1 %
            self.assertEqual(m.outputs(int(base * 0.96)), (True, False), base)    # -4 %  warning
            self.assertEqual(m.outputs(int(base * 0.93)), (False, True), base)    # -7 %  degraded

    def test_limits_match_legacy_values_at_factory_nominal(self):
        m = RegionalBaselineCheckerModel()
        calibrate(m, 4360)  # 436.0 MHz
        self.assertEqual(m.outputs(4231), (False, False))  # 423.1 MHz >= 422.9 legacy warning limit
        self.assertEqual(m.outputs(4228), (True, False))   # 422.8 MHz < 422.9
        self.assertEqual(m.outputs(4121), (True, False))   # 412.1 MHz >= 412.0 legacy critical limit
        self.assertEqual(m.outputs(4118), (False, True))   # 411.8 MHz < 412.0

    def test_dead_or_halted_oscillator_never_becomes_baseline(self):
        m = RegionalBaselineCheckerModel()
        calibrate(m, 0)        # oscillator halted at boot
        calibrate(m, 120)      # 12.0 MHz: still below the 50.0 MHz floor
        self.assertFalse(m.base_ready)
        calibrate(m, 3218)     # then it starts: calibrates to the real value
        self.assertTrue(m.base_ready)
        self.assertEqual(m.base, 3218)

    def test_dead_oscillator_after_calibration_is_degraded(self):
        m = RegionalBaselineCheckerModel()
        calibrate(m, 4360)
        self.assertEqual(m.outputs(0), (False, True))
        self.assertEqual(m.outputs(499), (False, True))

    def test_unstable_start_keeps_waiting_instead_of_latching(self):
        m = RegionalBaselineCheckerModel()
        # Alternates by ~10 % every sample: never within 1 % of the previous sample
        for i in range(40):
            m.valid_pulse(3000 if i % 2 == 0 else 3300)
        self.assertFalse(m.base_ready)
        calibrate(m, 3218, n=3)  # settles
        self.assertTrue(m.base_ready)

    def test_startup_transient_is_discarded(self):
        m = RegionalBaselineCheckerModel(settle_samples=8)
        for _ in range(8):
            m.valid_pulse(4360)      # default nominal placeholder held by the counter at reset
        for _ in range(4):
            m.valid_pulse(3218)      # real measurement
        self.assertTrue(m.base_ready)
        self.assertEqual(m.base, 3218)

    def test_reset_recalibrates(self):
        m = RegionalBaselineCheckerModel()
        calibrate(m, 4360)
        self.assertTrue(m.base_ready)
        m.reset()
        self.assertFalse(m.base_ready)
        self.assertEqual(m.outputs(3218), (False, False))  # nothing is flagged before calibration
        calibrate(m, 3218)
        self.assertEqual(m.base, 3218)


if __name__ == "__main__":
    unittest.main(verbosity=2)
