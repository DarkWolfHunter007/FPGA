@echo off
REM Launch Vivado GUI with the generated FPGA Health Monitoring project
echo Opening Vivado Project: C:\vivado_projects\fpga_health_project\fpga_health_project.xpr ...
start "" "C:\AMDDesignTools\2026.1\Vivado\bin\vivado.bat" "C:\vivado_projects\fpga_health_project\fpga_health_project.xpr"
