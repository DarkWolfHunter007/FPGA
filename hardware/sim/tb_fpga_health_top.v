`timescale 1ns / 1ps

module tb_fpga_health_top;

    reg clk;
    reg btnC;
    reg [3:0] sw;
    wire [15:0] led;
    wire RsTx;

    // Instantiate Unit Under Test (UUT)
    fpga_health_top uut (
        .clk(clk),
        .btnC(btnC),
        .sw(sw),
        .led(led),
        .RsTx(RsTx)
    );

    // 100.0 MHz Clock Generation (period = 10ns)
    initial begin
        clk = 0;
        forever #5 clk = ~clk;
    end

    initial begin
        $display("Starting FPGA Health Monitor Testbench...");
        // Initialize inputs
        btnC = 1'b1;     // Assert reset
        sw   = 4'b0001;  // sw[0]=1 (HELLO handshake mode for quick telemetry output)

        #200;
        btnC = 1'b0;     // Release reset
        $display("Reset released. Running design...");

        // Wait to observe heartbeat and UART signals
        #5000;

        // Switch to regular JSON streaming mode
        sw = 4'b0000;
        #5000;

        $display("Simulation checkpoint reached.");
        $display("  Heartbeat LED (led[0]): %b", led[0]);
        $display("  Healthy indicator (led[13]): %b", led[13]);
        $display("  UART Tx line: %b", RsTx);
        $display("Testbench completed successfully.");
        $finish;
    end

endmodule
