# ==============================================================================
# Vivado Non-Project Build Script: Four-Region FPGA Health Monitoring Bitstream
# Target: Digilent Basys 3 (Xilinx Artix-7 xc7a35tcpg236-1)
# ==============================================================================

set script_dir [file dirname [file normalize [info script]]]
set proj_root  [file normalize "$script_dir/.."]
# Switch working directory and build output to local non-OneDrive disk
set local_work "C:/vivado_build"
set output_dir "$local_work/build"
file mkdir $local_work
file mkdir $output_dir
cd $local_work

puts "======================================================================"
puts " Starting Vivado Four-Region Synthesis & Implementation for Basys 3"
puts " Working directory: [pwd]"
puts " Output directory:  $output_dir"
puts "======================================================================"

# 1. Read RTL Verilog Source Files
read_verilog [glob $proj_root/rtl/*.v]

# 2. Read Constraints
read_xdc $proj_root/constraints/basys3.xdc

# 3. Synthesis
puts "--> Running Synthesis (preserving module hierarchy for Pblock assignment)..."
synth_design -top fpga_health_top -part xc7a35tcpg236-1 -flatten_hierarchy rebuilt

# Allow intentional combinatorial feedback loop for the Ring Oscillators
set_property ALLOW_COMBINATORIAL_LOOPS TRUE [get_nets -hierarchical *stage*out*]
catch { set_property ALLOW_COMBINATORIAL_LOOPS TRUE [get_nets -hierarchical -quiet *ro*clk*] }
catch { set_property SEVERITY {Warning} [get_drc_checks LUTLP-1] }

write_checkpoint -force $output_dir/post_synth.dcp
report_utilization -file $output_dir/post_synth_utilization.rpt

# 4. Apply Four-Region Floorplan
puts "--> Applying Four-Region Physical Pblock Floorplan..."
source $proj_root/vivado/four_region_floorplan.tcl

# Verify all four regional modules are strictly assigned to their intended Pblocks
puts "--> Verifying Pblock containment..."
set required_pbs {pblock_R1 pblock_R2 pblock_R3 pblock_R4}
foreach pb $required_pbs {
    if {[llength [get_pblocks -quiet $pb]] == 0} {
        error "BUILD FAILED: Required Pblock '$pb' does not exist in design!"
    }
    set assigned_cells [get_cells -of [get_pblocks $pb]]
    if {[llength $assigned_cells] == 0} {
        error "BUILD FAILED: Pblock '$pb' has no assigned cells (module was not constrained)!"
    }
    puts "    $pb: Verified [llength $assigned_cells] assigned cells."
}

# 5. Logic Optimization
puts "--> Running Logic Optimization (opt_design)..."
opt_design
write_checkpoint -force $output_dir/post_opt.dcp

# 6. Placement
puts "--> Running Placement (place_design with regional Pblocks)..."
place_design
write_checkpoint -force $output_dir/post_place.dcp

# 7. Routing
puts "--> Running Routing (route_design)..."
route_design
write_checkpoint -force $output_dir/post_route.dcp

# 8. Generate Reports
puts "--> Generating Implementation Reports..."
report_timing_summary -file $output_dir/timing_summary.rpt
report_utilization -file $output_dir/utilization.rpt
foreach pb [get_pblocks] {
    catch { report_utilization -pblocks $pb -file "$output_dir/utilization_${pb}.rpt" }
}
report_drc -file $output_dir/drc.rpt

# 9. Write Bitstream
catch { set_property SEVERITY {Warning} [get_drc_checks LUTLP-1] }
set bitstream_path "$output_dir/fpga_health_top.bit"
puts "--> Writing Bitstream to $bitstream_path..."
write_bitstream -force $bitstream_path

# Copy fresh bitstream to project hardware root
set local_bit "$proj_root/fpga_health_top.bit"
file copy -force $bitstream_path $local_bit
puts "--> Copied fresh bitstream to: $local_bit"

puts "======================================================================"
puts " SUCCESS: Four-Region Bitstream successfully generated at:"
puts " $bitstream_path"
puts "======================================================================"
