`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Module Name: packet_formatter
// Description: Telemetry ASCII JSON Serializer & UART Packet Dispatcher
// Target:      Digilent Basys 3 (XC7A35T-1CPG236C Artix-7)
// Output:      Streams structured JSON telemetry packets or handshake messages over UART
// Packet Formats:
//   Mode 0 (Default):
//     {"Temperature":35.2,"VCCINT":1.002,"VCCAUX":1.801,"VCCBRAM":1.000,"RO_Frequency":249.8,"Error_Rate":0.000010}\r\n
//   Mode 1 (Handshake/Test):
//     HELLO FPGA - Basys 3 Artix-7 Health Monitor Online\r\n
//////////////////////////////////////////////////////////////////////////////////

module packet_formatter #(
    parameter CLK_FREQ_HZ      = 100000000,
    parameter TRANSMIT_HZ      = 1          // 1 packet per second
)(
    input  wire        clk,
    input  wire        rst,
    input  wire        i_mode_select,       // 0: JSON Telemetry, 1: HELLO FPGA Handshake
    input  wire [15:0] i_temp_c_x10,        // Temp in 0.1 °C (e.g. 352 = 35.2)
    input  wire [15:0] i_vccint_mv,         // VCCINT in mV (e.g. 1000 = 1.000)
    input  wire [15:0] i_vccaux_mv,         // VCCAUX in mV (e.g. 1800 = 1.800)
    input  wire [15:0] i_vccbram_mv,        // VCCBRAM in mV (e.g. 1000 = 1.000)
    input  wire [15:0] i_ro_freq_mhz_x10,   // RO freq in 0.1 MHz (e.g. 2498 = 249.8)
    input  wire [19:0] i_error_count_ppm,   // Error PPM (e.g. 10 = 0.000010)
    input  wire        i_uart_busy,         // UART TX busy flag
    output reg         o_uart_valid,        // Byte valid strobe to UART TX
    output reg  [7:0]  o_uart_data,         // Byte to transmit
    output reg         o_tx_active          // High while packet transmission is in progress
);

    localparam INTERVAL_TICKS = CLK_FREQ_HZ / TRANSMIT_HZ;

    // Buffer for packet characters (max 128 bytes)
    reg [7:0] buffer [0:127];
    reg [7:0] pkt_len;
    reg [7:0] send_ptr;

    // Timer to trigger periodic transmission
    reg [27:0] timer;

    // State machine
    localparam S_IDLE       = 3'd0;
    localparam S_LOAD_PKT   = 3'd1;
    localparam S_SEND_BYTE  = 3'd2;
    localparam S_WAIT_BUSY  = 3'd3;
    localparam S_WAIT_READY = 3'd4;

    reg [2:0] state;

    // Digits computation
    function [7:0] to_ascii;
        input [3:0] digit;
        begin
            to_ascii = 8'h30 + {4'd0, digit};
        end
    endfunction

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            timer        <= 28'd0;
            state        <= S_IDLE;
            pkt_len      <= 8'd0;
            send_ptr     <= 8'd0;
            o_uart_valid <= 1'b0;
            o_uart_data  <= 8'd0;
            o_tx_active  <= 1'b0;
        end else begin
            o_uart_valid <= 1'b0;

            case (state)
                S_IDLE: begin
                    o_tx_active <= 1'b0;
                    if (timer < INTERVAL_TICKS - 1) begin
                        timer <= timer + 28'd1;
                    end else begin
                        timer <= 28'd0;
                        state <= S_LOAD_PKT;
                    end
                end

                S_LOAD_PKT: begin
                    o_tx_active <= 1'b1;
                    send_ptr    <= 8'd0;

                    if (i_mode_select) begin
                        // Mode 1: HELLO FPGA Handshake Text
                        buffer[0]  <= "H"; buffer[1]  <= "E"; buffer[2]  <= "L"; buffer[3]  <= "L";
                        buffer[4]  <= "O"; buffer[5]  <= " "; buffer[6]  <= "F"; buffer[7]  <= "P";
                        buffer[8]  <= "G"; buffer[9]  <= "A"; buffer[10] <= " "; buffer[11] <= "-";
                        buffer[12] <= " "; buffer[13] <= "B"; buffer[14] <= "a"; buffer[15] <= "s";
                        buffer[16] <= "y"; buffer[17] <= "s"; buffer[18] <= " "; buffer[19] <= "3";
                        buffer[20] <= " "; buffer[21] <= "A"; buffer[22] <= "r"; buffer[23] <= "t";
                        buffer[24] <= "i"; buffer[25] <= "x"; buffer[26] <= "-"; buffer[27] <= "7";
                        buffer[28] <= " "; buffer[29] <= "H"; buffer[30] <= "e"; buffer[31] <= "a";
                        buffer[32] <= "l"; buffer[33] <= "t"; buffer[34] <= "h"; buffer[35] <= " ";
                        buffer[36] <= "M"; buffer[37] <= "o"; buffer[38] <= "n"; buffer[39] <= "i";
                        buffer[40] <= "t"; buffer[41] <= "o"; buffer[42] <= "r"; buffer[43] <= " ";
                        buffer[44] <= "O"; buffer[45] <= "n"; buffer[46] <= "l"; buffer[47] <= "i";
                        buffer[48] <= "n"; buffer[49] <= "e"; buffer[50] <= "\r"; buffer[51] <= "\n";
                        pkt_len    <= 8'd52;
                    end else begin
                        // Mode 0: Full JSON Telemetry Packet
                        // {"Temperature":
                        buffer[0]  <= "{"; buffer[1]  <= "\""; buffer[2]  <= "T"; buffer[3]  <= "e";
                        buffer[4]  <= "m"; buffer[5]  <= "p"; buffer[6]  <= "e"; buffer[7]  <= "r";
                        buffer[8]  <= "a"; buffer[9]  <= "t"; buffer[10] <= "u"; buffer[11] <= "r";
                        buffer[12] <= "e"; buffer[13] <= "\""; buffer[14] <= ":";

                        // XX.X
                        buffer[15] <= to_ascii((i_temp_c_x10 / 16'd100) % 16'd10);
                        buffer[16] <= to_ascii((i_temp_c_x10 / 16'd10) % 16'd10);
                        buffer[17] <= ".";
                        buffer[18] <= to_ascii(i_temp_c_x10 % 16'd10);

                        // ,"VCCINT":
                        buffer[19] <= ","; buffer[20] <= "\""; buffer[21] <= "V"; buffer[22] <= "C";
                        buffer[23] <= "C"; buffer[24] <= "I"; buffer[25] <= "N"; buffer[26] <= "T";
                        buffer[27] <= "\""; buffer[28] <= ":";

                        // X.XXX
                        buffer[29] <= to_ascii((i_vccint_mv / 16'd1000) % 16'd10);
                        buffer[30] <= ".";
                        buffer[31] <= to_ascii((i_vccint_mv / 16'd100) % 16'd10);
                        buffer[32] <= to_ascii((i_vccint_mv / 16'd10) % 16'd10);
                        buffer[33] <= to_ascii(i_vccint_mv % 16'd10);

                        // ,"VCCAUX":
                        buffer[34] <= ","; buffer[35] <= "\""; buffer[36] <= "V"; buffer[37] <= "C";
                        buffer[38] <= "C"; buffer[39] <= "A"; buffer[40] <= "U"; buffer[41] <= "X";
                        buffer[42] <= "\""; buffer[43] <= ":";

                        // X.XXX
                        buffer[44] <= to_ascii((i_vccaux_mv / 16'd1000) % 16'd10);
                        buffer[45] <= ".";
                        buffer[46] <= to_ascii((i_vccaux_mv / 16'd100) % 16'd10);
                        buffer[47] <= to_ascii((i_vccaux_mv / 16'd10) % 16'd10);
                        buffer[48] <= to_ascii(i_vccaux_mv % 16'd10);

                        // ,"VCCBRAM":
                        buffer[49] <= ","; buffer[50] <= "\""; buffer[51] <= "V"; buffer[52] <= "C";
                        buffer[53] <= "C"; buffer[54] <= "B"; buffer[55] <= "R"; buffer[56] <= "A";
                        buffer[57] <= "M"; buffer[58] <= "\""; buffer[59] <= ":";

                        // X.XXX
                        buffer[60] <= to_ascii((i_vccbram_mv / 16'd1000) % 16'd10);
                        buffer[61] <= ".";
                        buffer[62] <= to_ascii((i_vccbram_mv / 16'd100) % 16'd10);
                        buffer[63] <= to_ascii((i_vccbram_mv / 16'd10) % 16'd10);
                        buffer[64] <= to_ascii(i_vccbram_mv % 16'd10);

                        // ,"RO_Frequency":
                        buffer[65] <= ","; buffer[66] <= "\""; buffer[67] <= "R"; buffer[68] <= "O";
                        buffer[69] <= "_"; buffer[70] <= "F"; buffer[71] <= "r"; buffer[72] <= "e";
                        buffer[73] <= "q"; buffer[74] <= "u"; buffer[75] <= "e"; buffer[76] <= "n";
                        buffer[77] <= "c"; buffer[78] <= "y"; buffer[79] <= "\""; buffer[80] <= ":";

                        // XXX.X
                        buffer[81] <= to_ascii((i_ro_freq_mhz_x10 / 16'd1000) % 16'd10);
                        buffer[82] <= to_ascii((i_ro_freq_mhz_x10 / 16'd100) % 16'd10);
                        buffer[83] <= to_ascii((i_ro_freq_mhz_x10 / 16'd10) % 16'd10);
                        buffer[84] <= ".";
                        buffer[85] <= to_ascii(i_ro_freq_mhz_x10 % 16'd10);

                        // ,"Error_Rate":0.
                        buffer[86] <= ","; buffer[87] <= "\""; buffer[88] <= "E"; buffer[89] <= "r";
                        buffer[90] <= "r"; buffer[91] <= "o"; buffer[92] <= "r"; buffer[93] <= "_";
                        buffer[94] <= "R"; buffer[95] <= "a"; buffer[96] <= "t"; buffer[97] <= "e";
                        buffer[98] <= "\""; buffer[99] <= ":"; buffer[100] <= "0"; buffer[101] <= ".";

                        // XXXXXX (6 digits)
                        buffer[102] <= to_ascii((i_error_count_ppm / 20'd100000) % 20'd10);
                        buffer[103] <= to_ascii((i_error_count_ppm / 20'd10000) % 20'd10);
                        buffer[104] <= to_ascii((i_error_count_ppm / 20'd1000) % 20'd10);
                        buffer[105] <= to_ascii((i_error_count_ppm / 20'd100) % 20'd10);
                        buffer[106] <= to_ascii((i_error_count_ppm / 20'd10) % 20'd10);
                        buffer[107] <= to_ascii(i_error_count_ppm % 20'd10);

                        // }\r\n
                        buffer[108] <= "}"; buffer[109] <= "\r"; buffer[110] <= "\n";
                        pkt_len     <= 8'd111;
                    end

                    state <= S_SEND_BYTE;
                end

                S_SEND_BYTE: begin
                    if (send_ptr < pkt_len) begin
                        o_uart_data  <= buffer[send_ptr];
                        o_uart_valid <= 1'b1;
                        state        <= S_WAIT_BUSY;
                    end else begin
                        state <= S_IDLE;
                    end
                end

                S_WAIT_BUSY: begin
                    if (i_uart_busy) begin
                        state <= S_WAIT_READY;
                    end
                end

                S_WAIT_READY: begin
                    if (!i_uart_busy) begin
                        send_ptr <= send_ptr + 8'd1;
                        state    <= S_SEND_BYTE;
                    end
                end

                default: state <= S_IDLE;
            endcase
        end
    end

endmodule
