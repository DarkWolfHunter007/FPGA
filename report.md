# FPGA Health Classification and Regional Map Consistency: Investigation & Verification Report

**File:** `report.md`  
**Target Repository:** `FPGA`  
**Target Hardware:** Digilent Basys 3 (Xilinx Artix-7 XC7A35T-1CPG236C)  
**Date of Investigation:** 2026-10-10  

---

## 1. Investigation Details

- **Repository Name:** `FPGA`
- **Active Branch:** `main`
- **Remote Repositories:**
  - `origin`: `https://github.com/DarkWolfHunter007/FPGA.git`
  - `fork`: `https://github.com/Rithika-Reeba/FPGA.git`
- **Git Commit Hash Inspected / Base:** `6f2666453664d6eb2be150e7039572458022a101`
- **Git Commit Hash After Fixes:** `d597f0e9c9ff694ebb4b317423dab8b329c4ecbb`
- **Dashboard URL:** `http://localhost:8501`
- **Browser Inspection Status:**
  - *Initial Defect State:* Inspected via user-provided visual capture and diagnostic telemetry logs.
  - *Post-Fix State:* Programmatic verification of generated Streamlit HTML markup, data structures, and complete regression test suite execution in a headless environment.
- **Investigation Timestamp:** 2026-10-10 11:30:00 to 12:15:00 UTC+05:30.

---

## 2. Browser Output

### Initial Defect State (Prior to Fix)
As observed in the supplied telemetry screenshots:
- **Overall FPGA Health:** `Degraded`
- **ML Prediction:** `Warning` (Confidence: 48.0%)
- **Engineering Assessment:** `Degraded` (Deterministic safety override active: RO frequency below critical operating boundary)
- **Aggregate RO Frequency:** ~407.5 MHz
- **Regional Frequencies:**
  - Region 1 (R1 - Northwest): 436.0 MHz (Baseline: 436.3 MHz, Drift: -0.07%, Status: `Healthy`)
  - Region 2 (R2 - Northeast): **322.1 MHz** (Baseline: **322.20 MHz**, Drift: **-0.03%**, Status: **`Healthy`** ❌ *Defect*)
  - Region 3 (R3 - Southwest): 436.0 MHz (Baseline: 436.1 MHz, Drift: -0.02%, Status: `Healthy`)
  - Region 4 (R4 - Southeast): 436.0 MHz (Baseline: 435.9 MHz, Drift: +0.02%, Status: `Healthy`)
- **Regional Baselines & Boundaries:**
  - R2 Baseline: 322.20 MHz
  - R2 Critical Boundary: 411.8 MHz
- **Contradiction:** The overall engineering assessment flagged R2 as critical because 322.1 MHz violated the hard critical boundary (411.8 MHz), yet the 2×2 regional map evaluated R2 solely against its low baseline of 322.20 MHz (producing -0.03% drift) and labeled it **Healthy ("Nominal Timing Propagation")**.
- **Browser Console Errors:** None (the inconsistency was purely logical and state-driven).

### Corrected State (Post-Fix)
- **Overall FPGA Health:** `Degraded`
- **ML Prediction:** `Warning` (Confidence: 48.0%)
- **Engineering Assessment:** `Degraded` (Safety override active: `RO frequency below critical threshold (322.10 MHz < 411.80 MHz)`)
- **Regional Frequencies & Evaluated States:**
  - Region 1 (R1): 436.0 MHz (Baseline: 436.3 MHz, Crit: 412.3 MHz, Drift: -0.07%, Status: `Healthy`, Provenance: `[MEASURED]`)
  - Region 2 (R2): **322.1 MHz** (Baseline: **435.8 MHz** [Factory Fallback], Crit: **411.8 MHz**, Drift: **-26.09%**, Status: **`Degraded`** ✅, Reason: `Below critical boundary (322.1 <= 411.8 MHz) (Hard Engineering Override)`, Provenance: `[MEASURED]`)
  - Region 3 (R3): 436.0 MHz (Baseline: 436.1 MHz, Crit: 412.1 MHz, Drift: -0.02%, Status: `Healthy`, Provenance: `[MEASURED]`)
  - Region 4 (R4): 436.0 MHz (Baseline: 435.9 MHz, Crit: 411.9 MHz, Drift: +0.02%, Status: `Healthy`, Provenance: `[MEASURED]`)
- **Browser/UI Rendering:**
  - R2 card renders with degraded orange/red styling, a visible badge `[CRIT: 411.8 MHz]`, an explicit diagnostic reason line, and provenance indicator `[MEASURED]`.
  - Overall status and regional map status are in 100% agreement.

---

## 3. Aggregate RO Frequency Verification

### Exact RTL Expression
From `hardware/rtl/fpga_health_top.v` (lines 111–115):

```verilog
// Aggregate average frequency for backward-compatible telemetry
wire [17:0] ro_sum = {2'b00, ro_r1_freq_mhz_x10} + {2'b00, ro_r2_freq_mhz_x10} +
                     {2'b00, ro_r3_freq_mhz_x10} + {2'b00, ro_r4_freq_mhz_x10};
wire [15:0] ro_freq_mhz_x10 = ro_sum[17:2]; // Average (sum / 4)
```

Additionally, `hardware/rtl/fpga_health_top.v` (lines 117–120) computes the conservative worst-case frequency for on-board LED diagnostic indicators:
```verilog
wire [15:0] min_r12 = (ro_r1_freq_mhz_x10 < ro_r2_freq_mhz_x10) ? ro_r1_freq_mhz_x10 : ro_r2_freq_mhz_x10;
wire [15:0] min_r34 = (ro_r3_freq_mhz_x10 < ro_r4_freq_mhz_x10) ? ro_r3_freq_mhz_x10 : ro_r4_freq_mhz_x10;
wire [15:0] ro_worst_freq_mhz_x10 = (min_r12 < min_r34) ? min_r12 : min_r34;
```

### Arithmetic Average & Scaling Verification
- **Is it the arithmetic average?** Yes. It computes $\lfloor (R1 + R2 + R3 + R4)/4 \rfloor$.
- **Frequency Units & Scaling:** Frequencies in RTL are scaled by $\times 10$ ($0.1\text{ MHz}$ resolution). For example, $436.3\text{ MHz}$ is represented as integer `4363`.
- **Bit Widths & Truncation:**
  - Individual regional inputs: `wire [15:0]`.
  - Accumulator: `wire [17:0] ro_sum` (includes 2 guard bits preventing arithmetic overflow).
  - Division by 4: Shift-right by 2 bits (`ro_sum[17:2]`), truncating the fractional remainder (maximum truncation loss $< 0.3\text{ MHz}$).

### Telemetry Serialization
From `hardware/rtl/packet_formatter.v` (lines 121–141):
- Serialized JSON field: `"RO_Frequency":XXX.X`
- Individual regional fields: `"RO_R1":XXX.X`, `"RO_R2":XXX.X`, `"RO_R3":XXX.X`, `"RO_R4":XXX.X`

### Dashboard Parser & UI Binding
- **Parser:** `communication/uart_receiver.py` and `dashboard/data_source.py` decode `"RO_Frequency"`, dividing or floating to MHz.
- **UI Component:** Rendered in Section 2 (Primary Telemetry Grid: "RO Frequency" card), Section 3 (Timing Degradation Indicator), and Altair Trend Charts (Tab 1).
- **Identified Pipeline Inconsistency:** Older versions of `LiveUARTDataSource.poll_hardware()` silently copied global `RO_Frequency` into missing regional fields (`RO_R1..RO_R4`) and marked them as `MEASURED`. This was corrected to mark provenance as `DERIVED_GLOBAL`.

---

## 4. Live Telemetry Provenance

| Channel | Physical Quadrant / FPGA Region | Source Provenance Classification | Notes |
| :--- | :--- | :---: | :--- |
| **`RO_R1`** | Northwest (CLOCKREGION_X0Y2 / pblock_R1) | **Direct Hardware Measurement (`MEASURED`)** | Provided in live packet or explicitly tagged `DERIVED_GLOBAL` if missing. |
| **`RO_R2`** | Northeast (CLOCKREGION_X1Y2 / pblock_R2) | **Direct Hardware Measurement (`MEASURED`)** | Critical measurement (322.1 MHz). |
| **`RO_R3`** | Southwest (CLOCKREGION_X0Y0 / pblock_R3) | **Direct Hardware Measurement (`MEASURED`)** | Provided in live packet or tagged `DERIVED_GLOBAL`. |
| **`RO_R4`** | Southeast (CLOCKREGION_X1Y0 / pblock_R4) | **Direct Hardware Measurement (`MEASURED`)** | Provided in live packet or tagged `DERIVED_GLOBAL`. |
| **`RO_Frequency`** | On-Chip Logic Fabric Aggregate | **RTL Hardware Synthesis Average (`MEASURED`)** | Hardware 4-region arithmetic average. |
| **`Temperature`** | Artix-7 Die Thermal Diode | **Direct Hardware Measurement (`MEASURED`)** | Sampled via XADC internal channel 0. |
| **`VCCINT`** | Core Logic Rail (1.0V) | **Direct Hardware Measurement (`MEASURED`)** | Sampled via XADC internal channel 1. |
| **`VCCAUX`** | Auxiliary Rail (1.8V) | **Direct Hardware Measurement (`MEASURED`)** | Sampled via XADC internal channel 2. |
| **`VCCBRAM`** | Block RAM Rail (1.0V) | **Direct Hardware Measurement (`MEASURED`)** | Sampled via XADC internal channel 6. |

### Raw Received Telemetry Sample
Example packet received over 115200 baud UART:
```json
{"Temperature":35.2,"VCCINT":1.002,"VCCAUX":1.801,"VCCBRAM":1.000,"RO_R1":436.3,"RO_R2":322.1,"RO_R3":436.1,"RO_R4":435.9,"RO_Frequency":407.6,"Error_Rate":0.000010}
```

---

## 5. Root Cause of Persistent Degraded Status

Tracing the sample through the system:

1. **UART Ingestion:**
   `LiveUARTDataSource.poll_hardware()` (`dashboard/data_source.py`) received the packet containing `RO_R2: 322.1`.
2. **Baseline Calibration Vulnerability:**
   In `dashboard/data_source.py` (lines 343–352), the data source computed the initial baseline by averaging the first 5 frames without checking if those frames were healthy. When initial frames contained an already-degraded reading (~322.20 MHz), that degraded frequency was locked in as `self.baseline_sample["RO_R2"] = 322.20`.
3. **ML Classification:**
   `ml/predict.py` fed the 16-feature vector into the 200-tree Random Forest classifier. With frequency slowed but temperature and error rate normal, the model returned `Warning` with 48.0% confidence.
4. **Overall Safety Layer Evaluation:**
   `dashboard/app.py` called `evaluate_engineering_limits()` without passing regional baselines. The function evaluated R2 against the authoritative factory nominal (435.8 MHz) and critical boundary (411.8 MHz). Because $322.1 \le 411.8\text{ MHz}$, a hard engineering safety override was triggered, setting the overall system health to **Degraded**.
5. **Regional Map Calculation Divergence:**
   `dashboard/health_map.py` (`generate_four_region_data()`) received the unvalidated live baseline of 322.20 MHz. It computed:
   $$\text{Drift} = \frac{322.1 - 322.20}{322.20} \times 100\% = -0.03\%$$
   The function classified status using drift only (`drift <= -5.5%` $\to$ Degraded, `drift <= -3.0%` $\to$ Warning, else $\to$ Healthy), completely ignoring hard critical boundaries. Because $-0.03\%$ is within nominal drift, it classified R2 as **Healthy**.
6. **UI Rendering:**
   The dashboard rendered the Overall KPI card as **Degraded** while rendering R2 on the 2×2 regional grid as green **Healthy**, producing the confirmed inconsistency.

---

## 6. Code Changes

### 1. `dashboard/config.py`
- **Problem:** No canonical regional health evaluation function; lack of baseline validation logic.
- **Change:**
  - Added `validate_regional_baseline(region_id, baseline_input)`: Rejects non-numeric, unphysical, or degraded baselines ($< 422.7\text{ MHz}$ for R2), falling back to factory nominal ($435.8\text{ MHz}$).
  - Added `evaluate_regional_health(region_id, measurement, baseline_freq, provenance)`: Enforces strict severity precedence:
    1. Input validity / physical limits.
    2. Validated baseline selection.
    3. Hard critical boundary ($f \le 411.8\text{ MHz}$ for R2) takes absolute precedence over drift.
    4. Hard warning boundary ($f \le 422.7\text{ MHz}$).
    5. Percentage drift analysis.
  - Refactored `evaluate_engineering_limits()` to delegate regional evaluations to `evaluate_regional_health()`.
- **Tests Added:** `test_regional_baseline_validation_and_unhealthy_baseline_protection`, `test_r2_critical_with_low_baseline_inconsistency_regression`, `test_regional_health_critical_precedence_over_small_drift`.
- **Side Effects:** None; existing threshold schemas and backward-compatibility aliases are preserved.

### 2. `dashboard/health_map.py`
- **Problem:** `generate_four_region_data()` evaluated health solely on percentage drift, bypassing hard limits. HTML renderer omitted critical boundaries and diagnostic reasons.
- **Change:**
  - Refactored `generate_four_region_data()` to delegate regional health decisions directly to `evaluate_regional_health()`.
  - Updated `render_four_region_map_html()` to display critical boundaries (`Crit: 411.8 MHz`), diagnostic override reasons, and data provenance badges (`[MEASURED]`, `[DERIVED_GLOBAL]`).
- **Tests Added:** `test_render_four_region_map_html_displays_critical_and_reason`, `test_generate_four_region_data_handles_unhealthy_baseline`.

### 3. `dashboard/data_source.py`
- **Problem:** `LiveUARTDataSource.poll_hardware()` established unvalidated baselines from the first 5 frames. Legacy fallback falsely labeled global frequency as measured regional telemetry.
- **Change:**
  - Validated candidate baselines using `validate_regional_baseline()`; degraded averages fall back to factory nominal.
  - Flagged fallback packets explicitly as `DERIVED_GLOBAL`.
- **Tests Added:** Integrated into data source and baseline test suites.

### 4. `dashboard/app.py`
- **Problem:** `evaluate_engineering_limits()` was called without passing `regional_baselines`.
- **Change:** Passed `regional_baselines=meta.get("regional_baselines")` into `evaluate_engineering_limits()`.

### 5. `summary.md`
- **Problem:** Missing architectural documentation on regional safety precedence and baseline semantics.
- **Change:** Added Section 10 documenting the 5-tier evaluation hierarchy, factory nominal vs board-calibrated baseline semantics, ML vs safety overrides, and provenance.

---

## 7. Test and Verification Results

### Automated Unit & Regression Tests
Command executed:
```powershell
.\venv\Scripts\python -m unittest discover tests
```
Output:
```text
.....................................................................
----------------------------------------------------------------------
Ran 69 tests in 3.591s

OK
```
**Result:** 69 of 69 tests passed, 0 failed, 0 errors.

### Specific Critical Regression Tests Executed:
1. `tests.test_four_region_health.TestFourRegionHealth.test_r2_critical_with_low_baseline_inconsistency_regression` (**PASSED**)
   - Confirms that R2 with measured frequency 322.1 MHz, baseline 322.20 MHz, and critical boundary 411.8 MHz evaluates to **`Degraded`** (Severity: `CRITICAL`).
2. `tests.test_engineering_limits.TestEngineeringLimits.test_regional_baseline_validation_and_unhealthy_baseline_protection` (**PASSED**)
   - Confirms that candidate baseline 322.20 MHz is rejected as unhealthy ($< 422.7\text{ MHz}$) and falls back to factory nominal 435.8 MHz.
3. `tests.test_four_region_health.TestFourRegionHealth.test_regional_health_critical_precedence_over_small_drift` (**PASSED**)
   - Confirms that hard critical boundaries take absolute precedence over near-zero drift.
4. `tests.test_four_region_health.TestFourRegionHealth.test_regional_health_invalid_data_never_healthy` (**PASSED**)
   - Confirms that `None`, `NaN`, `Inf`, and out-of-bounds readings produce `Degraded` / `PHYSICALLY_INVALID`.
5. `tests.test_four_region_health.TestFourRegionHealth.test_render_four_region_map_html_displays_critical_and_reason` (**PASSED**)
   - Confirms HTML output renders critical boundaries, diagnostic reasons, and provenance badges.

### Verification Category Breakdown
- **Automated Unit / Regression Tests:** **PASSED** (69 tests).
- **Browser / UI Markup Generation:** **PASSED** (HTML string assertions verified).
- **Live UART Data Pipeline:** **PASSED** (Mocked stream packet parsing and bounds validation verified).
- **Physical FPGA Bench Test:** **PENDING** (Requires physical connection of Basys 3 hardware).

---

## 8. Git Commit History

All commits were created in exact chronological order:

| # | Commit Hash | Commit Message | Purpose |
| :-: | :-: | :--- | :--- |
| **1** | `b67abff` | `test: reproduce regional health inconsistency` | Added reproduction regression test capturing the R2 defect. |
| **2** | `de71399` | `fix: unify regional critical-limit evaluation` | Implemented canonical `evaluate_regional_health()` in `dashboard/config.py`. |
| **3** | `d776fa4` | `fix: validate regional baseline selection` | Added `validate_regional_baseline()` and protected `LiveUARTDataSource`. |
| **4** | `1646f38` | `fix: align regional map status rendering` | Updated `dashboard/health_map.py` HTML renderer with critical boundary and reason. |
| **5** | `d597f0e` | `docs: explain health precedence and baseline semantics` | Added Section 10 to `summary.md` explaining precedence and baseline semantics. |

---

## 9. Remaining Issues and Recommended Next Steps

### Unresolved Problems
None in the software pipeline. The logic inconsistency, baseline poisoning vulnerability, and rendering discrepancies are completely resolved.

### Required Physical Board Checks (Digilent Basys 3 XC7A35T)
1. **Bitstream Verification:** Program `top_system.bit` via Vivado Hardware Manager or OpenOCD over JTAG (Pin W5 clock, Pin U18 reset).
2. **UART Handshake & Data Stream:** Connect micro-USB (FTDI bridge on Pin A18), open serial port at 115200 baud 8N1, and verify receipt of Mode 0 JSON packets.
3. **Physical Baseline Acquisition:** Confirm that upon initialization, healthy on-chip ring oscillators stream 430–445 MHz and register as `CALIBRATED_BOARD`.
4. **Thermal / Aging Emulation:** Enable switch `sw[2]` (error injection) or apply thermal load to verify that the overall engineering assessment and regional map transition synchronously to `Warning` and `Degraded`.

---

## 10. Final Verdict

### **FIX VERIFIED**

**Evidence:**
1. The bug was reproduced via automated test `test_r2_critical_with_low_baseline_inconsistency_regression`.
2. A single canonical function `evaluate_regional_health()` unifies the overall engineering safety layer and the four-region map.
3. Unhealthy candidate baselines (e.g., 322.20 MHz) are rejected by `validate_regional_baseline()`, falling back to factory nominals.
4. Hard critical engineering limits strictly supersede small relative drift.
5. All 69 automated tests pass with 0 regressions.
6. Code changes have been committed in the required sequence and synchronized to remote repositories.
