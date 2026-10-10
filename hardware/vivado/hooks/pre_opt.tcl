# ==============================================================================
# Vivado Implementation Pre-Opt Hook Script
# Target: Digilent Basys 3 (XC7A35T)
# Purpose: Allow intentional combinatorial feedback loops for Ring Oscillators
# ==============================================================================
catch { set_property ALLOW_COMBINATORIAL_LOOPS TRUE [get_nets -hierarchical *stage*out*] }
catch { set_property ALLOW_COMBINATORIAL_LOOPS TRUE [get_nets -hierarchical -quiet *ro*clk*] }
catch { set_property SEVERITY {Warning} [get_drc_checks LUTLP-1] }
