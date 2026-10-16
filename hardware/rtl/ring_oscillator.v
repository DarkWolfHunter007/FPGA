`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Module Name: ring_oscillator
// Description: 5-Stage Ring Oscillator (RO) Sensor for Silicon Aging & Delay Monitoring
// Target:      Digilent Basys 3 (XC7A35T-1CPG236C Artix-7)
// Stages:      N = 5 inverting logic elements
// Formula:     tau = 1 / (2 * N * f_Hz) = 1000 / (2 * 5 * f_MHz) [ns/stage]
// Notes:       Uses DONT_TOUCH / KEEP / S synthesis attributes to prevent Vivado
//              logic optimization and preserve the physical combinatorial feedback loop.
//
// Placement:   In hardware builds (no SIMULATION define) the five stages are explicit
//              LUT primitives tied together with relative placement (HU_SET + RLOC):
//              stage0..stage3 share slice X0Y0 and stage4 sits in the slice directly
//              above (X0Y1). Without this, Vivado is free to scatter the five LUTs
//              anywhere inside the region's pblock - in region R2 it spread the loop
//              over 9 slice rows, added ~0.8 ns of wire delay and dropped the oscillator
//              from ~440 MHz to ~322 MHz on a perfectly healthy die. A ring oscillator's
//              absolute frequency is a placement property, so every instance must be
//              placed identically for the four regions to be comparable.
//              Vivado picks the absolute site for each instance inside its pblock;
//              HU_SET keeps the set unique per instance.
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
`ifdef SIMULATION
    assign #0.23 stage0_out = ~(stage4_out & i_en);
    assign #0.23 stage1_out = ~stage0_out;
    assign #0.23 stage2_out = ~stage1_out;
    assign #0.23 stage3_out = ~stage2_out;
    assign #0.23 stage4_out = ~stage3_out;
`else
    // Stage 0: NAND(stage4_out, i_en)  -> LUT2, O = ~(I0 & I1), INIT[3:0] = 4'b0111
    (* DONT_TOUCH = "TRUE", HU_SET = "ro_stage_set", RLOC = "X0Y0" *)
    LUT2 #(.INIT(4'h7)) stage0 (.I0(stage4_out), .I1(i_en), .O(stage0_out));

    // Stages 1..4: inverters -> LUT1, O = ~I0, INIT[1:0] = 2'b01
    (* DONT_TOUCH = "TRUE", HU_SET = "ro_stage_set", RLOC = "X0Y0" *)
    LUT1 #(.INIT(2'h1)) stage1 (.I0(stage0_out), .O(stage1_out));

    (* DONT_TOUCH = "TRUE", HU_SET = "ro_stage_set", RLOC = "X0Y0" *)
    LUT1 #(.INIT(2'h1)) stage2 (.I0(stage1_out), .O(stage2_out));

    (* DONT_TOUCH = "TRUE", HU_SET = "ro_stage_set", RLOC = "X0Y0" *)
    LUT1 #(.INIT(2'h1)) stage3 (.I0(stage2_out), .O(stage3_out));

    // A slice holds four LUT6 sites, so the fifth stage goes in the slice directly above.
    (* DONT_TOUCH = "TRUE", HU_SET = "ro_stage_set", RLOC = "X0Y1" *)
    LUT1 #(.INIT(2'h1)) stage4 (.I0(stage3_out), .O(stage4_out));
`endif

    // Output tapped from stage4
    assign o_ro_clk = stage4_out;

endmodule
