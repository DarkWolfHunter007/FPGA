`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Module Name: regional_health_monitor
// Description: Independent Physical Regional Health Monitor for Basys 3 Artix-7
// Architecture: Integrates a 5-Stage Ring Oscillator (RO) and a 10 ms Gated
//               Reciprocal Frequency Counter within a physically isolated region.
// Formula:     tau = 1 / (2 * N * f_Hz) = 100 / f_MHz [ns/stage for N=5]
// Pblock:      Constrained to one of four physical device quadrants (R1..R4)
//////////////////////////////////////////////////////////////////////////////////

module regional_health_monitor #(
    parameter REF_CLK_HZ = 100000000, // 100.0 MHz reference clock
    parameter GATE_TICKS = 1000000    // 10.0 ms measurement gate window
)(
    input  wire        clk,            // 100 MHz System Reference Clock
    input  wire        rst,            // System Reset (Active-High)
    input  wire        i_en,           // Regional Monitor Enable (1=Oscillate, 0=Halt)
    output wire [15:0] o_freq_mhz_x10, // Measured Frequency in 0.1 MHz units (4360 = 436.0 MHz)
    output wire        o_freq_valid,   // Pulse when fresh measurement is latched
    output wire        o_ro_clk        // Asynchronous RO clock output (for observability)
);

    // Internal RO clock signal
    wire ro_clk_internal;

    // 1. Dedicated 5-Stage Ring Oscillator
    // DONT_TOUCH and KEEP attributes inside ring_oscillator preserve the loop
    ring_oscillator u_ring_osc (
        .i_en(i_en),
        .o_ro_clk(ro_clk_internal)
    );

    // 2. Dedicated Reciprocal Frequency Counter with 2-Stage CDC
    frequency_counter #(
        .REF_CLK_HZ(REF_CLK_HZ),
        .GATE_TICKS(GATE_TICKS)
    ) u_freq_counter (
        .clk(clk),
        .rst(rst),
        .i_ro_clk(ro_clk_internal),
        .o_freq_mhz_x10(o_freq_mhz_x10),
        .o_freq_valid(o_freq_valid)
    );

    assign o_ro_clk = ro_clk_internal;

endmodule
