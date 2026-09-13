`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Module Name: ring_oscillator
// Description: 5-Stage Ring Oscillator (RO) Sensor for Silicon Aging & Delay Monitoring
// Target:      Digilent Basys 3 (XC7A35T-1CPG236C Artix-7)
// Stages:      N = 5 inverting logic elements
// Formula:     tau = 1 / (2 * N * f_Hz) = 1000 / (2 * 5 * f_MHz) [ns/stage]
// Notes:       Uses DONT_TOUCH / KEEP / S synthesis attributes to prevent Vivado
//              logic optimization and preserve the physical combinatorial feedback loop.
//////////////////////////////////////////////////////////////////////////////////

module ring_oscillator (
    input  wire i_en,      // Enable oscillation (Active High)
    output wire o_ro_clk   // Asynchronous ring oscillator clock output
);

    // Internal node wires with synthesis protection attributes
    (* DONT_TOUCH = "TRUE", KEEP = "TRUE", S = "TRUE" *) wire stage0_out;
    (* DONT_TOUCH = "TRUE", KEEP = "TRUE", S = "TRUE" *) wire stage1_out;
    (* DONT_TOUCH = "TRUE", KEEP = "TRUE", S = "TRUE" *) wire stage2_out;
    (* DONT_TOUCH = "TRUE", KEEP = "TRUE", S = "TRUE" *) wire stage3_out;
    (* DONT_TOUCH = "TRUE", KEEP = "TRUE", S = "TRUE" *) wire stage4_out;

    // Stage 0: Gated Inverting Element (NAND / Gated Inverter)
    // When i_en is high, stage0_out = ~stage4_out
    // When i_en is low, stage0_out = 1'b1 (halts oscillation)
    assign stage0_out = ~(stage4_out & i_en);

    // Stages 1 to 4: Inverting delay chain
    assign stage1_out = ~stage0_out;
    assign stage2_out = ~stage1_out;
    assign stage3_out = ~stage2_out;
    assign stage4_out = ~stage3_out;

    // Output tapped from stage4
    assign o_ro_clk = stage4_out;

endmodule
