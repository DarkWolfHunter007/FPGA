# False "Degraded" on the Basys 3: cause and fix

## Symptom
With the board connected the dashboard (and the board's red LED) reported **Degraded** although the
silicon was healthy. In the live COM10 capture region R2 read **321.8 MHz** while R1, R3 and R4 read
about 440 MHz.

## Root cause
A ring oscillator's absolute frequency is a **placement/routing** property, not an aging measurement.
The floorplan only boxed each oscillator into a large pblock, so Vivado was free to scatter the five
LUTs. In R2 it spread them over 9 slice rows (about 0.8 ns of extra wire), which is the whole
440 -> 322 MHz difference (see `report.md`, section 5).

The monitor then compared every region against one fixed limit derived from 436 MHz
(warning 422.9, critical 412.0). That produced a false alarm in four places:

| Where | Problem |
| --- | --- |
| `evaluate_regional_health` | Absolute 412.0 / 422.9 MHz checked before the per-region drift check |
| `validate_regional_baseline` | Rejected any baseline below 422.9 MHz and substituted 436, so R2 could never calibrate to itself |
| `LiveUARTDataSource` baseline capture | Judged the start-up window against the absolute limits, failed on R2, then locked 436 in for every region |
| overall status / ML input | The aggregate was compared against 412 absolute. The R2 weight of 0.05 and the quorum rule only hid this |
| `fpga_health_top.v` LEDs | `worst region < 412 MHz` lit the red LED on every boot |

## What changed
**Judge each region by drift from its own baseline.**
- `dashboard/config.py`: region limits are the legacy limits scaled by `baseline / 436`. With a 436 MHz
  baseline they are exactly the old 422.9 / 412.0. A calibrated baseline is accepted anywhere within
  +/-40 % of nominal; one that differs by more than 5.5 % is accepted but reported as a **placement offset**
  in the card, so it is never silent. Dead / halted / garbage readings still fall back to 436 and are flagged.
- The overall RO series and the ML input are **baseline-normalised**: each region divided by its own
  baseline, mapped to the 436 MHz scale the model was trained on (`baseline_normalized_frequency`).
  A healthy board reads about 436 MHz, real aging in any region pulls it down.
- Default weights are equal again (R2 = 0.05 only hid R2's readings).
- `dashboard/data_source.py`: the UART baseline is captured per region from a window that is plausible,
  stable (spread <= 2 %) and clean sample by sample. If the board boots hot or unstable it keeps using 436
  and **retries** on every packet instead of locking the fallback in.
- `health_map.py` / `charts.py` use each region's own state and limits instead of hardcoded 412 / 422.9.

**Board LEDs and placement (hardware).**
- `regional_baseline_checker.v` (new): each region latches its own baseline after reset; LEDs use
  -3.0 % (warning) and -5.5 % (degraded) from that baseline. `led[12]` is lit while calibrating.
- `ring_oscillator.v`: in hardware builds the five stages are explicit `LUT1`/`LUT2` primitives with
  relative placement (`HU_SET` + `RLOC`), so all four oscillators are built the same way and the 9-row
  spread cannot recur.

## Kept as is
- The multi-pblock quorum policy (overall status changes only when 2 or more regions degrade). It is now
  one constant, `REGIONAL_QUORUM_MIN` in `dashboard/config.py`. Set it to `1` if a single region that has
  genuinely aged should make the whole chip Degraded. Region cards always show their true state.
- Temperature, supply-rail and error-rate limits are unchanged.

## Verify on the board (needs Vivado and the board)
1. Rebuild: `vivado -mode batch -source hardware/vivado/build_bitstream.tcl`. The `.bit` committed in the
   repo is the OLD design.
2. In the Implemented Design, for each region run
   `get_sites -of_objects [get_cells -hier -filter {NAME =~ *u_region2*u_ring_osc*stage*}]` (change the
   region number): stage0-3 should share one slice and stage4 should be in the slice directly above.
   If `place_design` reports an RLOC error, send me the message.
3. Program the board, press `btnC`. `led[12]` should go off within about 0.1 s and `led[13]` (green) should light.
4. Start the dashboard on the UART source. Within the first 5 packets all four regions should show
   **HEALTHY**, with a *placement offset* note on any region far from 436 MHz.
5. Fault check: flip `sw[2]` (error injection) -> Warning / Degraded still appears (error rate and
   temperature limits are unchanged).

## Limits of this change
- The Verilog has not been synthesised or simulated here (no Vivado in the sandbox). The checker algorithm
  is covered by a bit-accurate Python model (`tests/test_rtl_checker_model.py`), not by the Verilog itself.
  The existing `tb_fpga_health_top.v` runs only 20 us, so it never reaches calibration.
- A baseline is taken at power-up, so slow aging **between** power cycles is not visible to the LEDs, and the
  dashboard recalibrates each session. Persisting a commissioning baseline to disk would fix that.
- Ring-oscillator frequency also falls as the die warms. Baselines are not temperature-compensated, so a
  large temperature rise after calibration eats into the 3 % / 5.5 % margin. Measure how much your board
  drifts between a cold start and a warm run before trusting the margins.
- Halting an oscillator (`sw[1]` up) is not detected: `frequency_counter.v` keeps its last value when the
  oscillator stops, so health does not change (this predates the change). If an oscillator is halted
  *before* calibration finishes, `led[12]` stays lit.
