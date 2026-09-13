`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Module Name: error_rate_monitor
// Description: Hardware PRBS-7 Functional Error Rate Monitor Engine
// Target:      Digilent Basys 3 (Artix-7)
// Function:    Generates PRBS-7 bit sequence, streams through pipeline, checks
//              for bit mismatches over 1,000,000 bit testing epochs.
// Error Injection: Switch-controlled (i_error_inject) synthetic bit-flip injection
//                  to demonstrate live health state transitions (Healthy -> Warning -> Degraded).
//////////////////////////////////////////////////////////////////////////////////

module error_rate_monitor #(
    parameter WINDOW_BITS = 1000000 // 1,000,000 bit testing window
)(
    input  wire        clk,
    input  wire        rst,
    input  wire        i_error_inject,    // Switch-controlled artificial error injection
    output reg  [19:0] o_error_count_ppm, // Errors per 1,000,000 bits (0 to 1,000,000)
    output reg         o_error_rate_valid // Pulse when epoch completes
);

    // PRBS-7 Linear Feedback Shift Registers: x^7 + x^6 + 1
    reg [6:0] tx_lfsr;
    reg [6:0] rx_lfsr;

    reg [19:0] bit_counter;
    reg [19:0] error_accumulator;

    // Synthetic error injection counter
    reg [15:0] inject_counter;
    localparam INJECT_INTERVAL = 16'd500; // 1 error every 500 bits (~0.002000 error rate)

    wire tx_next_bit;
    assign tx_next_bit = tx_lfsr[6] ^ tx_lfsr[5];

    wire rx_expected_bit;
    assign rx_expected_bit = rx_lfsr[6] ^ rx_lfsr[5];

    wire transmitted_bit;
    wire inject_flip;
    assign inject_flip     = i_error_inject && (inject_counter == 16'd0);
    assign transmitted_bit = tx_next_bit ^ inject_flip;

    // Monitor pipeline
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            tx_lfsr            <= 7'h7F;
            rx_lfsr            <= 7'h7F;
            bit_counter        <= 20'd0;
            error_accumulator  <= 20'd0;
            inject_counter     <= 16'd0;
            o_error_count_ppm  <= 20'd10; // Default nominal 10 ppm (0.000010)
            o_error_rate_valid <= 1'b0;
        end else begin
            o_error_rate_valid <= 1'b0;

            // LFSR Progression
            tx_lfsr <= {tx_lfsr[5:0], tx_next_bit};
            rx_lfsr <= {rx_lfsr[5:0], rx_expected_bit};

            // Error Injection Stride
            if (inject_counter < INJECT_INTERVAL - 1) begin
                inject_counter <= inject_counter + 16'd1;
            end else begin
                inject_counter <= 16'd0;
            end

            // Compare received vs expected
            if (transmitted_bit != rx_expected_bit) begin
                error_accumulator <= error_accumulator + 20'd1;
            end

            // Epoch Accumulator & Latch
            if (bit_counter < WINDOW_BITS - 1) begin
                bit_counter <= bit_counter + 20'd1;
            end else begin
                bit_counter        <= 20'd0;
                o_error_count_ppm  <= error_accumulator;
                error_accumulator  <= 20'd0;
                o_error_rate_valid <= 1'b1;
            end
        end
    end

endmodule
