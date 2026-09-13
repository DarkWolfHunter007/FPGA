`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Module Name: frequency_counter
// Description: Gated Reciprocal Frequency Counter for Ring Oscillator Telemetry
// Reference Clock: 100.0 MHz System Clock (clk)
// Input Signal:    Asynchronous Ring Oscillator Clock (i_ro_clk)
// Resolution:      0.1 MHz (Frequency output = f_MHz * 10, e.g. 2498 = 249.8 MHz)
// Gate Time:       10.0 ms (1,000,000 reference clock cycles)
// CDC:             2-stage synchronizers across reference and RO clock domains
//////////////////////////////////////////////////////////////////////////////////

module frequency_counter #(
    parameter REF_CLK_HZ    = 100000000, // 100 MHz reference
    parameter GATE_TICKS    = 1000000    // 10 ms gate window = 1,000,000 clk cycles
)(
    input  wire        clk,            // 100 MHz System Reference Clock
    input  wire        rst,            // System Reset
    input  wire        i_ro_clk,       // Ring Oscillator Clock Input
    output reg  [15:0] o_freq_mhz_x10, // Frequency in 0.1 MHz units (2500 = 250.0 MHz)
    output reg         o_freq_valid    // Pulse/flag when fresh measurement is ready
);

    // =========================================================================
    // Reference Clock Domain (100 MHz) - Gate Generator
    // =========================================================================
    reg [23:0] ref_counter;
    reg        gate_ref;
    reg        meas_cycle_done;

    // Gate generator state machine
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            ref_counter  <= 24'd0;
            gate_ref     <= 1'b0;
        end else begin
            if (ref_counter < GATE_TICKS - 1) begin
                ref_counter <= ref_counter + 24'd1;
                gate_ref    <= 1'b1;
            end else begin
                ref_counter <= 24'd0;
                gate_ref    <= 1'b0;
            end
        end
    end

    // =========================================================================
    // RO Clock Domain - 2-Stage CDC Synchronizer & RO Pulse Counter
    // =========================================================================
    (* ASYNC_REG = "TRUE" *) reg [1:0] gate_ro_sync;
    reg [23:0] ro_pulse_counter;
    reg [23:0] ro_count_latched;
    reg        ro_data_ready;

    always @(posedge i_ro_clk or posedge rst) begin
        if (rst) begin
            gate_ro_sync     <= 2'b00;
            ro_pulse_counter <= 24'd0;
            ro_count_latched <= 24'd0;
            ro_data_ready    <= 1'b0;
        end else begin
            gate_ro_sync <= {gate_ro_sync[0], gate_ref};

            if (gate_ro_sync[1]) begin
                // Gate is open, count RO pulses
                ro_pulse_counter <= ro_pulse_counter + 24'd1;
                ro_data_ready    <= 1'b0;
            end else begin
                // Gate just closed, latch count
                if (ro_pulse_counter != 24'd0) begin
                    ro_count_latched <= ro_pulse_counter;
                    ro_pulse_counter <= 24'd0;
                    ro_data_ready    <= 1'b1;
                end
            end
        end
    end

    // =========================================================================
    // Reference Domain - Synchronize Ready & Calculate Frequency
    // =========================================================================
    (* ASYNC_REG = "TRUE" *) reg [1:0] ready_ref_sync;
    reg ready_ref_d1;

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            ready_ref_sync  <= 2'b00;
            ready_ref_d1    <= 1'b0;
            o_freq_mhz_x10  <= 16'd2500; // Default nominal 250.0 MHz
            o_freq_valid    <= 1'b0;
        end else begin
            ready_ref_sync <= {ready_ref_sync[0], ro_data_ready};
            ready_ref_d1   <= ready_ref_sync[1];

            o_freq_valid <= 1'b0;

            // On rising edge of synchronized ready pulse
            if (ready_ref_sync[1] && !ready_ref_d1) begin
                // ro_count_latched represents count over 10 ms (10,000 us).
                // Frequency (MHz) = count / 10,000.
                // Frequency (0.1 MHz) = count / 1,000.
                if (ro_count_latched > 24'd1000) begin
                    o_freq_mhz_x10 <= ro_count_latched / 24'd1000;
                    o_freq_valid   <= 1'b1;
                end
            end
        end
    end

endmodule
