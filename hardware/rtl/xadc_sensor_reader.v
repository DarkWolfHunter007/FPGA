`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Module Name: xadc_sensor_reader
// Description: Internal XADC DRP Sequencer for Artix-7 Sensors
// Channels:    Temperature (0x00), VCCINT (0x01), VCCAUX (0x02), VCCBRAM (0x06)
// Fixed-Point Formats:
//   - Temperature: 0.1 °C units (e.g., 352 = 35.2 °C)
//   - VCCINT / VCCAUX / VCCBRAM: Millivolts (e.g., 1000 = 1.000 V, 1800 = 1.800 V)
//////////////////////////////////////////////////////////////////////////////////

module xadc_sensor_reader #(
    parameter CLK_FREQ_HZ = 100000000 // 100 MHz System Clock
)(
    input  wire        clk,
    input  wire        rst,
    output reg  [15:0] o_temp_c_x10,  // Temp in 0.1 °C (e.g. 352 = 35.2 °C)
    output reg  [15:0] o_vccint_mv,   // VCCINT in mV (e.g. 1000 = 1.000 V)
    output reg  [15:0] o_vccaux_mv,   // VCCAUX in mV (e.g. 1800 = 1.800 V)
    output reg  [15:0] o_vccbram_mv,  // VCCBRAM in mV (e.g. 1000 = 1.000 V)
    output reg         o_sensors_valid
);

    // =========================================================================
    // DRP Signals
    // =========================================================================
    reg  [6:0]  daddr;
    reg         den;
    wire        drdy;
    wire [15:0] do_out;

    // State machine for DRP channel reads
    localparam S_IDLE        = 4'd0;
    localparam S_READ_TEMP   = 4'd1;
    localparam S_WAIT_TEMP   = 4'd2;
    localparam S_READ_VINT   = 4'd3;
    localparam S_WAIT_VINT   = 4'd4;
    localparam S_READ_VAUX   = 4'd5;
    localparam S_WAIT_VAUX   = 4'd6;
    localparam S_READ_VBRAM  = 4'd7;
    localparam S_WAIT_VBRAM  = 4'd8;
    localparam S_CALC_DONE   = 4'd9;

    reg [3:0]  state;
    reg [23:0] poll_timer;
    localparam POLL_INTERVAL = CLK_FREQ_HZ / 20; // Poll 20 times/sec (every 50ms)

    reg [11:0] raw_temp;
    reg [11:0] raw_vccint;
    reg [11:0] raw_vccaux;
    reg [11:0] raw_vccbram;

    // =========================================================================
    // XADC 7-Series Primitive Instantiation
    // =========================================================================
    XADC #(
        .INIT_40(16'h0000), // Config 0: Continuous sequence mode
        .INIT_41(16'h21AF), // Config 1: Sequencer mode, continuous
        .INIT_42(16'h0400), // Config 2: DCLK divider = 4
        .INIT_48(16'h4701), // Channel Enable: Temp, VCCINT, VCCAUX, VCCBRAM
        .INIT_49(16'h0000),
        .INIT_4A(16'h0000),
        .INIT_4B(16'h0000),
        .INIT_4C(16'h0000),
        .INIT_4D(16'h0000),
        .INIT_4E(16'h0000),
        .INIT_4F(16'h0000),
        .INIT_50(16'hB5ED), // Upper alarm thresholds
        .INIT_51(16'h57E4),
        .INIT_52(16'hA147),
        .INIT_53(16'hCA33),
        .SIM_DEVICE("7SERIES"),
        .SIM_MONITOR_FILE("design.txt")
    ) xadc_inst (
        .DCLK(clk),
        .RESET(rst),
        .DEN(den),
        .DWE(1'b0),          // Read only
        .DADDR(daddr),
        .DI(16'h0000),
        .DO(do_out),
        .DRDY(drdy),
        .VP(1'b0),
        .VN(1'b0),
        .VAUXP(16'h0000),
        .VAUXN(16'h0000),
        .CONVST(1'b0),
        .CONVSTCLK(1'b0),
        .ALM(),
        .OT(),
        .BUSY(),
        .CHANNEL(),
        .EOC(),
        .EOS(),
        .JTAGBUSY(),
        .JTAGLOCKED(),
        .JTAGMODIFIED(),
        .MUXADDR()
    );

    // =========================================================================
    // DRP Polling Sequencer
    // =========================================================================
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            state           <= S_IDLE;
            poll_timer      <= 24'd0;
            den             <= 1'b0;
            daddr           <= 7'h00;
            raw_temp        <= 12'd1032; // Default approx 35.0 C
            raw_vccint      <= 12'd1365; // Default approx 1.000 V
            raw_vccaux      <= 12'd2458; // Default approx 1.800 V
            raw_vccbram     <= 12'd1365; // Default approx 1.000 V
            o_temp_c_x10    <= 16'd350;  // 35.0 °C
            o_vccint_mv     <= 16'd1000; // 1.000 V
            o_vccaux_mv     <= 16'd1800; // 1.800 V
            o_vccbram_mv    <= 16'd1000; // 1.000 V
            o_sensors_valid <= 1'b0;
        end else begin
            den             <= 1'b0;
            o_sensors_valid <= 1'b0;

            case (state)
                S_IDLE: begin
                    if (poll_timer < POLL_INTERVAL - 1) begin
                        poll_timer <= poll_timer + 24'd1;
                    end else begin
                        poll_timer <= 24'd0;
                        state      <= S_READ_TEMP;
                    end
                end

                // --- 1. Temperature (0x00) ---
                S_READ_TEMP: begin
                    daddr <= 7'h00;
                    den   <= 1'b1;
                    state <= S_WAIT_TEMP;
                end

                S_WAIT_TEMP: begin
                    if (drdy) begin
                        raw_temp <= do_out[15:4];
                        state    <= S_READ_VINT;
                    end
                end

                // --- 2. VCCINT (0x01) ---
                S_READ_VINT: begin
                    daddr <= 7'h01;
                    den   <= 1'b1;
                    state <= S_WAIT_VINT;
                end

                S_WAIT_VINT: begin
                    if (drdy) begin
                        raw_vccint <= do_out[15:4];
                        state      <= S_READ_VAUX;
                    end
                end

                // --- 3. VCCAUX (0x02) ---
                S_READ_VAUX: begin
                    daddr <= 7'h02;
                    den   <= 1'b1;
                    state <= S_WAIT_VAUX;
                end

                S_WAIT_VAUX: begin
                    if (drdy) begin
                        raw_vccaux <= do_out[15:4];
                        state      <= S_READ_VBRAM;
                    end
                end

                // --- 4. VCCBRAM (0x06) ---
                S_READ_VBRAM: begin
                    daddr <= 7'h06;
                    den   <= 1'b1;
                    state <= S_WAIT_VBRAM;
                end

                S_WAIT_VBRAM: begin
                    if (drdy) begin
                        raw_vccbram <= do_out[15:4];
                        state       <= S_CALC_DONE;
                    end
                end

                // --- 5. Conversion & Latching ---
                S_CALC_DONE: begin
                    // Temperature: (raw * 503975) / 409600 - 2732 (in 0.1 °C)
                    // Simplified: (raw * 504) / 410 - 273
                    // Exact 32-bit math:
                    o_temp_c_x10 <= (({20'd0, raw_temp} * 32'd503975) / 32'd409600) - 32'd2732;

                    // Voltage in mV: (raw * 3000) / 4096
                    o_vccint_mv  <= ({20'd0, raw_vccint}  * 32'd3000) / 32'd4096;
                    o_vccaux_mv  <= ({20'd0, raw_vccaux}  * 32'd3000) / 32'd4096;
                    o_vccbram_mv <= ({20'd0, raw_vccbram} * 32'd3000) / 32'd4096;

                    o_sensors_valid <= 1'b1;
                    state           <= S_IDLE;
                end

                default: state <= S_IDLE;
            endcase
        end
    end

endmodule
