`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Module Name: uart_tx
// Description: Standard 8N1 UART Serial Transmitter
// Target:      Digilent Basys 3 (XC7A35T-1CPG236C)
// System Clock: 100.0 MHz
// Baud Rate:    115200 bps
// Divisor:      100,000,000 / 115,200 = 868 clock cycles per bit
//////////////////////////////////////////////////////////////////////////////////

module uart_tx #(
    parameter CLK_FREQ_HZ = 100000000,
    parameter BAUD_RATE   = 115200
)(
    input  wire       clk,
    input  wire       rst,
    input  wire       i_valid,
    input  wire [7:0] i_data,
    output reg        o_tx,
    output wire       o_busy,
    output reg        o_done
);

    localparam CLKS_PER_BIT = CLK_FREQ_HZ / BAUD_RATE; // 868 at 100MHz / 115200

    localparam STATE_IDLE  = 3'b000;
    localparam STATE_START = 3'b001;
    localparam STATE_DATA  = 3'b010;
    localparam STATE_STOP  = 3'b011;
    localparam STATE_CLEAN = 3'b100;

    reg [2:0]  state;
    reg [15:0] clk_count;
    reg [2:0]  bit_index;
    reg [7:0]  tx_data;

    assign o_busy = (state != STATE_IDLE);

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            state      <= STATE_IDLE;
            o_tx       <= 1'b1; // Idle line is HIGH
            o_done     <= 1'b0;
            clk_count  <= 16'd0;
            bit_index  <= 3'd0;
            tx_data    <= 8'd0;
        end else begin
            o_done <= 1'b0;

            case (state)
                STATE_IDLE: begin
                    o_tx      <= 1'b1;
                    clk_count <= 16'd0;
                    bit_index <= 3'd0;
                    if (i_valid) begin
                        tx_data <= i_data;
                        state   <= STATE_START;
                    end
                end

                STATE_START: begin
                    o_tx <= 1'b0; // Start bit is LOW
                    if (clk_count < CLKS_PER_BIT - 1) begin
                        clk_count <= clk_count + 16'd1;
                    end else begin
                        clk_count <= 16'd0;
                        state     <= STATE_DATA;
                    end
                end

                STATE_DATA: begin
                    o_tx <= tx_data[bit_index];
                    if (clk_count < CLKS_PER_BIT - 1) begin
                        clk_count <= clk_count + 16'd1;
                    end else begin
                        clk_count <= 16'd0;
                        if (bit_index < 3'd7) begin
                            bit_index <= bit_index + 3'd1;
                        end else begin
                            bit_index <= 3'd0;
                            state     <= STATE_STOP;
                        end
                    end
                end

                STATE_STOP: begin
                    o_tx <= 1'b1; // Stop bit is HIGH
                    if (clk_count < CLKS_PER_BIT - 1) begin
                        clk_count <= clk_count + 16'd1;
                    end else begin
                        clk_count <= 16'd0;
                        o_done    <= 1'b1;
                        state     <= STATE_CLEAN;
                    end
                end

                STATE_CLEAN: begin
                    state <= STATE_IDLE;
                end

                default: state <= STATE_IDLE;
            endcase
        end
    end

endmodule
