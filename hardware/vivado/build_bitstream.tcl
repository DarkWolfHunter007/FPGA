# ==============================================================================
# Vivado Non-Project Build Script: FPGA Health Monitoring Bitstream
# Target: Digilent Basys 3 (Xilinx Artix-7 xc7a35tcpg236-1)
# ==============================================================================

set script_dir [file dirname [file normalize [info script]]]
set proj_root  [file normalize "$script_dir/.."]
set output_dir [file normalize "$proj_root/build"]

file mkdir $output_dir

puts "======================================================================"
puts " Starting Vivado Synthesis & Implementation for Basys 3 Health Monitor"
puts " Output directory: $output_dir"
puts "======================================================================"

# 1. Read RTL Verilog Source Files
read_verilog [glob $proj_root/rtl/*.v]

# 2. Read Constraints
read_xdc $proj_root/constraints/basys3.xdc

# 3. Synthesis
puts "--> Running Synthesis..."
synth_design -top fpga_health_top -part xc7a35tcpg236-1 -flatten_hierarchy rebuilt
write_checkpoint -force $output_dir/post_synth.dcp
report_utilization -file $output_dir/post_synth_utilization.rpt

# 4. Logic Optimization
puts "--> Running Logic Optimization (opt_design)..."
opt_design
write_checkpoint -force $output_dir/post_opt.dcp

# 5. Placement
puts "--> Running Placement (place_design)..."
place_design
write_checkpoint -force $output_dir/post_place.dcp

# 6. Routing
puts "--> Running Routing (route_design)..."
route_design
write_checkpoint -force $output_dir/post_route.dcp

# 7. Generate Reports
puts "--> Generating Implementation Reports..."
report_timing_summary -file $output_dir/timing_summary.rpt
report_utilization -file $output_dir/utilization.rpt
report_drc -file $output_dir/drc.rpt

# 8. Write Bitstream
set bitstream_path "$output_dir/fpga_health_top.bit"
puts "--> Writing Bitstream to $bitstream_path..."
write_bitstream -force $bitstream_path

puts "======================================================================"
puts " SUCCESS: Bitstream successfully generated at:"
puts " $bitstream_path"
puts "======================================================================"
