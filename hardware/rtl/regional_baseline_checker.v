`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Module Name: regional_baseline_checker
// Description: Per-region start-up baseline capture + drift classification for the
//              on-board health LEDs.
//
// Why: a ring oscillator's absolute frequency is set mostly by placement/routing, not
//      by aging. A healthy region can legitimately run at ~322 MHz while its neighbours
//      run at ~440 MHz. Comparing every region to one fixed limit (e.g. 412 MHz) lights
//      the red LED on a healthy die. Instead each region latches ITS OWN baseline after
//      power-up and is judged by drift from that baseline.
//
// Calibration: the first SETTLE_SAMPLES valid measurements are ignored (start-up
//      transients). After that, the first measurement that agrees with the previous one
//      within 1 % is latched as the baseline and o_base_ready is raised. Readings below
//      MIN_VALID_X10 (50.0 MHz) are treated as a dead / halted oscillator and never
//      become a baseline.
//
// Classification (after o_base_ready):
//      degraded : freq <  baseline * CRIT_THRESH_X1000 / 1000   (default 94.5 %, -5.5 %)
//                 or freq < MIN_VALID_X10 (dead oscillator)
//      warning  : freq <  baseline * WARN_THRESH_X1000 / 1000   (default 97.0 %, -3.0 %)
//
// Units: frequency in 0.1 MHz (4360 = 436.0 MHz). Same thresholds as the dashboard.
// A reset (btnC) clears the baseline and recalibrates.
//////////////////////////////////////////////////////////////////////////////////

module regional_baseline_checker #(
    parameter SETTLE_SAMPLES    = 8,    // valid measurements ignored after reset
    parameter WARN_THRESH_X1000 = 970,  // warning below 97.0 % of baseline
    parameter CRIT_THRESH_X1000 = 945,  // degraded below 94.5 % of baseline
    parameter MIN_VALID_X10     = 500   // below 50.0 MHz = dead / halted oscillator
)(
    input  wire        clk,
    input  wire        rst,
    input  wire [15:0] i_freq_mhz_x10, // latest regional frequency (0.1 MHz units)
    input  wire        i_freq_valid,   // one-cycle pulse when a fresh measurement is latched
    output reg         o_base_ready,   // baseline captured
    output reg  [15:0] o_base_mhz_x10, // captured baseline (0.1 MHz units)
    output wire        o_warning,      // drift beyond warning limit
    output wire        o_degraded      // drift beyond critical limit, or dead oscillator
);

    localparam [9:0] WARN_K = WARN_THRESH_X1000;
    localparam [9:0] CRIT_K = CRIT_THRESH_X1000;

    reg [7:0]  settle_cnt;
    reg [15:0] prev_freq;
    reg        have_prev;

    wire sample_ok = (i_freq_mhz_x10 >= MIN_VALID_X10);

    // Stable when |cur - prev| <= 1 % of cur
    wire [15:0] diff      = (i_freq_mhz_x10 > prev_freq) ? (i_freq_mhz_x10 - prev_freq)
                                                         : (prev_freq - i_freq_mhz_x10);
    wire [22:0] diff_x100 = diff * 7'd100;
    wire        stable    = have_prev && (diff_x100 <= {7'd0, i_freq_mhz_x10});

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            settle_cnt     <= 8'd0;
            prev_freq      <= 16'd0;
            have_prev      <= 1'b0;
            o_base_ready   <= 1'b0;
            o_base_mhz_x10 <= 16'd0;
        end else if (i_freq_valid && !o_base_ready) begin
            if (!sample_ok) begin
                // Dead / halted oscillator: restart the stability check, never baseline it
                have_prev <= 1'b0;
            end else if (settle_cnt < SETTLE_SAMPLES) begin
                settle_cnt <= settle_cnt + 8'd1;
                prev_freq  <= i_freq_mhz_x10;
                have_prev  <= 1'b1;
            end else begin
                prev_freq <= i_freq_mhz_x10;
                have_prev <= 1'b1;
                if (stable) begin
                    o_base_mhz_x10 <= i_freq_mhz_x10;
                    o_base_ready   <= 1'b1;
                end
            end
        end
    end

    // freq < base * K / 1000   <=>   freq * 1000 < base * K   (all values < 2^26)
    wire [25:0] cur_x1000  = i_freq_mhz_x10 * 10'd1000;
    wire [25:0] warn_limit = o_base_mhz_x10 * WARN_K;
    wire [25:0] crit_limit = o_base_mhz_x10 * CRIT_K;

    assign o_degraded = o_base_ready && ((i_freq_mhz_x10 < MIN_VALID_X10) || (cur_x1000 < crit_limit));
    assign o_warning  = o_base_ready && !o_degraded && (cur_x1000 < warn_limit);

endmodule
