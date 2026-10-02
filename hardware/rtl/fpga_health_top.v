`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Module Name: fpga_health_top
// Description: Top-Level FPGA Health Monitoring & Telemetry Engine
// Target:      Digilent Basys 3 (XC7A35T-1CPG236C Artix-7)
// Architecture: Four-Region Physical Health Monitoring Architecture
//   - Region 1 (u_region1): Northwest Quadrant (Pblock pblock_R1, Clock Region X0Y2)
//   - Region 2 (u_region2): Northeast Quadrant (Pblock pblock_R2, Clock Region X1Y2)
//   - Region 3 (u_region3): Southwest Quadrant (Pblock pblock_R3, Clock Region X0Y0)
//   - Region 4 (u_region4): Southeast Quadrant (Pblock pblock_R4, Clock Region X1Y0)
// Interfaces:
//   - clk: 100.0 MHz on pin W5
//   - btnC: Master Reset on pin U18
//   - RsTx: UART Serial Stream (115200 8N1) on pin A18
//   - sw[3:0]: Hardware configuration switches
//   - led[15:0]: Diagnostic and health state LEDs
//////////////////////////////////////////////////////////////////////////////////

module fpga_health_top (
    input  wire        clk,        // 100.0 MHz System Clock (Pin W5)
    input  wire        btnC,       // Active-High Reset Button (Pin U18)
    input  wire [3:0]  sw,         // Mode and Control Switches
    output wire [15:0] led,        // Status and Health Indicators
    output wire        RsTx        // UART TX to USB-UART Bridge (Pin A18)
);

    wire rst;
    assign rst = btnC;

    // Switch mappings
    wire sw_mode_select;  // sw[0]: 0=JSON Stream, 1=HELLO Handshake
    wire sw_ro_enable;    // sw[1]: 1=RO Enabled, 0=RO Halted
    wire sw_error_inject; // sw[2]: 1=Inject PRBS errors (Fault demo)
    wire sw_test_flag;    // sw[3]: General test flag

    assign sw_mode_select  = sw[0];
    assign sw_ro_enable    = ~sw[1]; // sw[1]=0: RO enabled (default), sw[1]=1: RO halted
    assign sw_error_inject = sw[2];
    assign sw_test_flag    = sw[3];

    // =========================================================================
    // 1. 1 Hz Heartbeat Counter
    // =========================================================================
    reg [26:0] heartbeat_cnt;
    reg        heartbeat_led;

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            heartbeat_cnt <= 27'd0;
            heartbeat_led <= 1'b0;
        end else begin
            if (heartbeat_cnt < 27'd50000000 - 1) begin
                heartbeat_cnt <= heartbeat_cnt + 27'd1;
            end else begin
                heartbeat_cnt <= 27'd0;
                heartbeat_led <= ~heartbeat_led;
            end
        end
    end

    // =========================================================================
    // 2. Four Independent Physical Regional Health Monitors (R1..R4)
    // =========================================================================
    wire [15:0] ro_r1_freq_mhz_x10;
    wire [15:0] ro_r2_freq_mhz_x10;
    wire [15:0] ro_r3_freq_mhz_x10;
    wire [15:0] ro_r4_freq_mhz_x10;
    wire        ro_r1_valid, ro_r2_valid, ro_r3_valid, ro_r4_valid;
    wire        ro_r1_clk,   ro_r2_clk,   ro_r3_clk,   ro_r4_clk;

    // Region 1: Northwest (Pblock pblock_R1, Clock Region X0Y2)
    regional_health_monitor u_region1 (
        .clk(clk),
        .rst(rst),
        .i_en(sw_ro_enable),
        .o_freq_mhz_x10(ro_r1_freq_mhz_x10),
        .o_freq_valid(ro_r1_valid),
        .o_ro_clk(ro_r1_clk)
    );

    // Region 2: Northeast (Pblock pblock_R2, Clock Region X1Y2)
    regional_health_monitor u_region2 (
        .clk(clk),
        .rst(rst),
        .i_en(sw_ro_enable),
        .o_freq_mhz_x10(ro_r2_freq_mhz_x10),
        .o_freq_valid(ro_r2_valid),
        .o_ro_clk(ro_r2_clk)
    );

    // Region 3: Southwest (Pblock pblock_R3, Clock Region X0Y0)
    regional_health_monitor u_region3 (
        .clk(clk),
        .rst(rst),
        .i_en(sw_ro_enable),
        .o_freq_mhz_x10(ro_r3_freq_mhz_x10),
        .o_freq_valid(ro_r3_valid),
        .o_ro_clk(ro_r3_clk)
    );

    // Region 4: Southeast (Pblock pblock_R4, Clock Region X1Y0)
    regional_health_monitor u_region4 (
        .clk(clk),
        .rst(rst),
        .i_en(sw_ro_enable),
        .o_freq_mhz_x10(ro_r4_freq_mhz_x10),
        .o_freq_valid(ro_r4_valid),
        .o_ro_clk(ro_r4_clk)
    );

    // Aggregate average frequency for backward-compatible telemetry
    wire [17:0] ro_sum = {2'b00, ro_r1_freq_mhz_x10} + {2'b00, ro_r2_freq_mhz_x10} +
                         {2'b00, ro_r3_freq_mhz_x10} + {2'b00, ro_r4_freq_mhz_x10};
    wire [15:0] ro_freq_mhz_x10 = ro_sum[17:2]; // Average (sum / 4)

    // Worst-case (minimum) frequency for conservative on-board hardware LED health indication
    wire [15:0] min_r12 = (ro_r1_freq_mhz_x10 < ro_r2_freq_mhz_x10) ? ro_r1_freq_mhz_x10 : ro_r2_freq_mhz_x10;
    wire [15:0] min_r34 = (ro_r3_freq_mhz_x10 < ro_r4_freq_mhz_x10) ? ro_r3_freq_mhz_x10 : ro_r4_freq_mhz_x10;
    wire [15:0] ro_worst_freq_mhz_x10 = (min_r12 < min_r34) ? min_r12 : min_r34;

    // =========================================================================
    // 3. XADC On-Chip Temperature & Voltage Sensor Reader
    // =========================================================================
    wire [15:0] temp_c_x10;
    wire [15:0] vccint_mv;
    wire [15:0] vccaux_mv;
    wire [15:0] vccbram_mv;
    wire        sensors_valid;

    xadc_sensor_reader #(
        .CLK_FREQ_HZ(100000000)
    ) u_xadc_reader (
        .clk(clk),
        .rst(rst),
        .o_temp_c_x10(temp_c_x10),
        .o_vccint_mv(vccint_mv),
        .o_vccaux_mv(vccaux_mv),
        .o_vccbram_mv(vccbram_mv),
        .o_sensors_valid(sensors_valid)
    );

    // =========================================================================
    // 4. PRBS-7 Functional Error Rate Monitor
    // =========================================================================
    wire [19:0] error_count_ppm;
    wire        error_rate_valid;

    error_rate_monitor #(
        .WINDOW_BITS(1000000)
    ) u_err_monitor (
        .clk(clk),
        .rst(rst),
        .i_error_inject(sw_error_inject),
        .o_error_count_ppm(error_count_ppm),
        .o_error_rate_valid(error_rate_valid)
    );

    // =========================================================================
    // 5. UART Transmitter & Four-Region Packet Formatter
    // =========================================================================
    wire       uart_tx_valid;
    wire [7:0] uart_tx_data;
    wire       uart_busy;
    wire       tx_active;

    packet_formatter #(
        .CLK_FREQ_HZ(100000000),
        .TRANSMIT_HZ(1) // 1 Hz telemetry streaming
    ) u_formatter (
        .clk(clk),
        .rst(rst),
        .i_mode_select(sw_mode_select),
        .i_temp_c_x10(temp_c_x10),
        .i_vccint_mv(vccint_mv),
        .i_vccaux_mv(vccaux_mv),
        .i_vccbram_mv(vccbram_mv),
        .i_ro_r1_freq_mhz_x10(ro_r1_freq_mhz_x10),
        .i_ro_r2_freq_mhz_x10(ro_r2_freq_mhz_x10),
        .i_ro_r3_freq_mhz_x10(ro_r3_freq_mhz_x10),
        .i_ro_r4_freq_mhz_x10(ro_r4_freq_mhz_x10),
        .i_ro_freq_mhz_x10(ro_freq_mhz_x10),
        .i_error_count_ppm(error_count_ppm),
        .i_uart_busy(uart_busy),
        .o_uart_valid(uart_tx_valid),
        .o_uart_data(uart_tx_data),
        .o_tx_active(tx_active)
    );

    uart_tx #(
        .CLK_FREQ_HZ(100000000),
        .BAUD_RATE(115200)
    ) u_uart_tx (
        .clk(clk),
        .rst(rst),
        .i_valid(uart_tx_valid),
        .i_data(uart_tx_data),
        .o_tx(RsTx),
        .o_busy(uart_busy),
        .o_done()
    );

    // =========================================================================
    // 6. On-Board Diagnostic LEDs
    // =========================================================================
    // Local hardware classification rules (Physical 436.0 MHz baseline):
    // Degraded: Temp >= 52°C OR RO Freq (worst region) < 412 MHz OR Error Rate >= 1000 ppm
    // Warning:  Temp >= 45°C OR RO Freq (worst region) < 423 MHz OR Error Rate >= 100 ppm
    // Healthy:  Nominal
    wire is_degraded;
    wire is_warning;
    wire is_healthy;

    assign is_degraded = (temp_c_x10 >= 16'd520) || (ro_worst_freq_mhz_x10 < 16'd4120) || (error_count_ppm >= 20'd1000);
    assign is_warning  = !is_degraded && ((temp_c_x10 >= 16'd450) || (ro_worst_freq_mhz_x10 < 16'd4230) || (error_count_ppm >= 20'd100));
    assign is_healthy  = !is_degraded && !is_warning;

    assign led[0]  = heartbeat_led;       // 1 Hz Heartbeat
    assign led[1]  = tx_active;           // UART TX Active
    assign led[2]  = sensors_valid;       // XADC conversion strobe
    assign led[3]  = ~sw[1];              // RO Running indicator (All 4 regions active)
    assign led[4]  = sw_error_inject;     // Error Injection Flag
    assign led[5]  = sw_mode_select;      // 1: Hello test, 0: JSON Telemetry
    assign led[6]  = sw_test_flag;
    assign led[7]  = uart_busy;

    assign led[12:8] = 5'b00000;

    assign led[13] = is_healthy;          // Green indicator (Healthy)
    assign led[14] = is_warning;          // Yellow indicator (Warning)
    assign led[15] = is_degraded;         // Red indicator (Degraded)

endmodule
