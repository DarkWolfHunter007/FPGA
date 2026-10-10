# ==============================================================================
# Vivado Implementation Pre-Bitstream Hook Script
# Target: Digilent Basys 3 (XC7A35T)
# Purpose: Downgrade LUTLP-1 DRC error to Warning to permit bitstream generation
# ==============================================================================
catch { set_property SEVERITY {Warning} [get_drc_checks LUTLP-1] }
catch { set_property ALLOW_COMBINATORIAL_LOOPS TRUE [get_nets -hierarchical *stage*out*] }
catch { set_property ALLOW_COMBINATORIAL_LOOPS TRUE [get_nets -hierarchical -quiet *ro*clk*] }
