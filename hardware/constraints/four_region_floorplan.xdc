# ==============================================================================
# Four-Region Physical Health Floorplan for Digilent Basys 3 (xc7a35tcpg236-1)
# ==============================================================================

# R1 Northwest (Clock Region X0Y2)
create_pblock pblock_R1
add_cells_to_pblock [get_pblocks pblock_R1] [get_cells -hierarchical -filter {NAME =~ *u_region1*}]
resize_pblock [get_pblocks pblock_R1] -add {SLICE_X0Y100:SLICE_X35Y149}
set_property CONTAIN_ROUTING false [get_pblocks pblock_R1]
set_property EXCLUDE_PLACEMENT false [get_pblocks pblock_R1]

# R2 Northeast (Clock Region X1Y2)
create_pblock pblock_R2
add_cells_to_pblock [get_pblocks pblock_R2] [get_cells -hierarchical -filter {NAME =~ *u_region2*}]
resize_pblock [get_pblocks pblock_R2] -add {SLICE_X36Y100:SLICE_X57Y149}
set_property CONTAIN_ROUTING false [get_pblocks pblock_R2]
set_property EXCLUDE_PLACEMENT false [get_pblocks pblock_R2]

# R3 Southwest (Clock Region X0Y0)
create_pblock pblock_R3
add_cells_to_pblock [get_pblocks pblock_R3] [get_cells -hierarchical -filter {NAME =~ *u_region3*}]
resize_pblock [get_pblocks pblock_R3] -add {SLICE_X0Y0:SLICE_X35Y49}
set_property CONTAIN_ROUTING false [get_pblocks pblock_R3]
set_property EXCLUDE_PLACEMENT false [get_pblocks pblock_R3]

# R4 Southeast (Clock Region X1Y0)
create_pblock pblock_R4
add_cells_to_pblock [get_pblocks pblock_R4] [get_cells -hierarchical -filter {NAME =~ *u_region4*}]
resize_pblock [get_pblocks pblock_R4] -add {SLICE_X36Y0:SLICE_X65Y49}
set_property CONTAIN_ROUTING false [get_pblocks pblock_R4]
set_property EXCLUDE_PLACEMENT false [get_pblocks pblock_R4]
