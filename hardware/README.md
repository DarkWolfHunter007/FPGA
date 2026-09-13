# Digilent Basys 3 FPGA Health Monitoring Hardware Implementation

Complete hardware RTL design, constraints, synthesis, and programming guide for the **AI-Assisted FPGA Health Monitoring System** on the **Digilent Basys 3** (Xilinx Artix-7 `XC7A35T-1CPG236C`).

---

## 1. Hardware Architecture Overview

```
+-------------------------------------------------------------------------------------------------+
|                                    DIGILENT BASYS 3 ARTIX-7                                     |
|                                                                                                 |
|   +--------------------------+    +--------------------------+    +-------------------------+   |
|   |   5-Stage Inverting      |    |   XADC Dual 12-bit       |    |   PRBS-7 Functional     |   |
|   |   Ring Oscillator (RO)   |    |   Sensor Sequencer       |    |   Error Rate Monitor    |   |
|   |   Aging Delay Sensor     |    |   Temp, VCCINT/AUX/BRAM  |    |   Pattern Checker       |   |
|   +------------+-------------+    +------------+-------------+    +------------+------------+   |
|                |                               |                               |                |
|                v                               v                               v                |
|   +--------------------------+    +--------------------------+    +-------------------------+   |
|   |  Frequency Counter       |    |  DRP 50ms Poller         |    |  Error Accumulator      |   |
|   |  10ms Gate Window (CDC)  |    |  Fixed-Point Scaler      |    |  10^6 Bit Epoch Counter |   |
|   +------------+-------------+    +------------+-------------+    +------------+------------+   |
|                |                               |                               |                |
|                +-------------------------------+-------------------------------+                |
|                                                |                                                |
|                                                v                                                |
|                              +-----------------------------------+                              |
|                              |   Telemetry Packet Formatter      |                              |
|                              |   ASCII JSON & Handshake Engine   |                              |
|                              +-----------------+-----------------+                              |
|                                                |                                                |
|                                                v                                                |
|                              +-----------------------------------+                              |
|                              |   UART Transmitter (115200 8N1)   |                              |
|                              |   Divisor = 868 @ 100.0 MHz ClkW5 |                              |
|                              +-----------------+-----------------+                              |
|                                                | Pin A18 (RsTx)                                 |
+------------------------------------------------|------------------------------------------------+
                                                 v
                                   FTDI FT2232HQ USB-UART Bridge
                                                 v
                                        Host PC (Windows COM)
```

---

## 2. Pin Mappings, Switches & Diagnostic LEDs

### Switch Definitions (`sw[3:0]`)
| Switch | Pin | Function | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `sw[0]` | `V17` | **Telemetry Format Mode** | `0` (Down) | `0`: JSON Telemetry Stream<br>`1`: `HELLO FPGA` Handshake burst test |
| `sw[1]` | `V16` | **Ring Oscillator Run/Halt** | `0` (Down) | `0`: Ring Oscillator oscillating continuously<br>`1`: RO halted for debugging |
| `sw[2]` | `W16` | **Synthetic Fault Injection** | `0` (Down) | `0`: Nominal PRBS-7 operation (Error rate ~0.000010)<br>`1`: Injects bit errors (~0.002000) to demonstrate live Warning/Degraded state transitions |
| `sw[3]` | `W17` | **Auxiliary Test Flag** | `0` (Down) | Test flag indicator |

### LED Definitions (`led[15:0]`)
| LED | Pin | Indicator Name | Description |
| :--- | :--- | :--- | :--- |
| `led[0]` | `U16` | **Heartbeat** | Blinks at 1 Hz when 100 MHz clock is active |
| `led[1]` | `E19` | **UART TX Active** | Pulses whenever a byte packet is transmitting over UART |
| `led[2]` | `U19` | **XADC Conversion** | Pulses when XADC completes a 4-channel DRP cycle |
| `led[3]` | `V19` | **RO Oscillating** | Lit when Ring Oscillator is running |
| `led[4]` | `W18` | **Error Injected** | Lit when `sw[2]` is active |
| `led[5]` | `U15` | **Mode Select** | Lit when `sw[0]` is in Hello Handshake mode |
| `led[13]`| `N3`  | **Health: HEALTHY** | Lit when Temperature, RO Freq, and Error Rate are nominal |
| `led[14]`| `P1`  | **Health: WARNING** | Lit when intermediate aging or elevated error rate is detected |
| `led[15]`| `L1`  | **Health: DEGRADED**| Lit when severe stress or high error rate is detected |

### Master Clock and Serial Pins
- **System Clock**: 100.0 MHz on Pin `W5` (`sys_clk_pin`, Period 10.0 ns)
- **Master Reset**: Pin `U18` (`btnC`, Active High)
- **UART Serial TX**: Pin `A18` (`RsTx` connected to USB-UART bridge)

---

## 3. Vivado Build & Programming Instructions

### Method A: Automated Batch Build (Command Line)

1. Open **Vivado Command Prompt** (or any shell where Vivado is on your `PATH`).
2. Navigate to the project root:
   ```powershell
   cd D:\Work\Personal\FPGA
   ```
3. Run synthesis, implementation, and bitstream generation:
   ```powershell
   vivado -mode batch -source hardware/vivado/build_bitstream.tcl
   ```
   The compiled bitstream will be generated at `hardware/build/fpga_health_top.bit`.

4. Plug in the Basys 3 board via USB and program it:
   ```powershell
   vivado -mode batch -source hardware/vivado/program_fpga.tcl
   ```

### Method B: Vivado GUI Project

1. Open Vivado and create a new project targeting `xc7a35tcpg236-1`.
2. Add all Verilog files from `hardware/rtl/`:
   - `uart_tx.v`
   - `ring_oscillator.v`
   - `frequency_counter.v`
   - `xadc_sensor_reader.v`
   - `error_rate_monitor.v`
   - `packet_formatter.v`
   - `fpga_health_top.v`
3. Add constraints from `hardware/constraints/basys3.xdc`.
4. Click **Generate Bitstream**.
5. Open **Hardware Manager** -> **Auto Connect** -> **Program Device**.

---

## 4. Telemetry Verification

### Step 1: Verify Serial Stream in Terminal
Open a serial terminal (PuTTY, Tera Term, or Python serial monitor) on your Basys 3 COM port at **115200 baud, 8 data bits, no parity, 1 stop bit (8N1)**.

You will observe live 1 Hz JSON telemetry frames:
```json
{"Temperature":35.2,"VCCINT":1.002,"VCCAUX":1.801,"VCCBRAM":1.000,"RO_Frequency":249.8,"Error_Rate":0.000010}
```

If you flip `sw[0]` UP, the board outputs the handshake string:
```text
HELLO FPGA - Basys 3 Artix-7 Health Monitor Online
```

### Step 2: Connect to Dashboard
1. Start the Streamlit application:
   ```powershell
   streamlit run dashboard/app.py
   ```
2. In the sidebar, select **Physical UART Stream (Artix-7)**.
3. Select your COM port from the dropdown and click **🔌 Connect**.
4. The dashboard will automatically detect the telemetry stream, validate the physical bounds, compute $\tau = 100/f$, engineer 16 features, evaluate health with Random Forest ML, and run the LangGraph diagnostic reasoning agent in real time.
