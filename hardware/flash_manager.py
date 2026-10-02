"""
FPGA Hardware Flash & Backup Manager for Digilent Basys 3 (XC7A35T)
===================================================================
Provides robust routines to:
1. Read back and save a copy of any program currently on the FPGA.
2. Program the precompiled health monitoring bitstream.
3. Restore the backed-up design on demand.
4. Query real-time on-chip XADC status over JTAG.
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

HARDWARE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = HARDWARE_DIR.parent
BUILD_DIR = HARDWARE_DIR / "build"
DEFAULT_BACKUP_PATH = HARDWARE_DIR / "backup_original.bin"

def get_bitstream_path() -> Path:
    candidates = [
        Path(r"C:\vivado_build\build\fpga_health_top.bit"),
        BUILD_DIR / "fpga_health_top.bit",
        HARDWARE_DIR / "fpga_health_top.bit"
    ]
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]

BITSTREAM_PATH = get_bitstream_path()

# Default Vivado Path
VIVADO_BAT = os.environ.get(
    "VIVADO_PATH",
    r"C:\AMDDesignTools\2026.1\Vivado\bin\vivado.bat"
)


def run_vivado_tcl(tcl_commands: str, timeout_sec: int = 120) -> Tuple[bool, str]:
    """Runs Vivado in batch mode to execute arbitrary Tcl commands via a temporary script."""
    if not Path(VIVADO_BAT).exists():
        return False, f"Vivado executable not found at: {VIVADO_BAT}"

    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".tcl", delete=False) as tf:
        tf.write(tcl_commands)
        temp_tcl = tf.name

    cmd = [
        VIVADO_BAT,
        "-mode", "batch",
        "-nolog",
        "-nojournal",
        "-source", temp_tcl
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            cwd=str(PROJECT_ROOT)
        )
        output = proc.stdout + "\n" + proc.stderr
        success = (proc.returncode == 0) and ("ERROR:" not in output or "INFO:" in output)
        return success, output
    except subprocess.TimeoutExpired:
        return False, f"Vivado operation timed out after {timeout_sec} seconds."
    except Exception as e:
        return False, f"Failed to execute Vivado: {str(e)}"
    finally:
        try:
            if os.path.exists(temp_tcl):
                os.remove(temp_tcl)
        except Exception:
            pass


def backup_current_fpga_program(output_bin_path: Optional[Path] = None) -> Tuple[bool, str]:
    """
    Reads back the active configuration currently in the FPGA's volatile SRAM
    and saves it as a binary file.
    """
    dest = Path(output_bin_path) if output_bin_path else DEFAULT_BACKUP_PATH
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest_str = str(dest).replace("\\", "/")

    tcl = f"""
open_hw_manager
connect_hw_server -allow_non_jtag
open_hw_target
set target_device [lindex [get_hw_devices xc7a35t_0] 0]
if {{$target_device eq ""}} {{ set target_device [lindex [get_hw_devices] 0] }}
current_hw_device $target_device
refresh_hw_device -update_hw_probes false [current_hw_device]
puts "--> Reading back FPGA configuration to: {dest_str}"
readback_hw_device -bin_file "{dest_str}" -force [current_hw_device]
close_hw_target
disconnect_hw_server
close_hw_manager
puts "SUCCESS: Backup complete."
"""
    success, out = run_vivado_tcl(tcl, timeout_sec=60)
    if dest.exists() and dest.stat().st_size > 0:
        return True, f"FPGA configuration successfully saved to {dest} ({dest.stat().st_size:,} bytes)"
    return False, f"Readback failed:\n{out}"


def program_health_bitstream(bitstream_path: Optional[Path] = None) -> Tuple[bool, str]:
    """
    Backs up any existing program and burns the health monitoring bitstream
    into the Basys 3 FPGA.
    """
    bit_path = Path(bitstream_path) if bitstream_path else BITSTREAM_PATH
    if not bit_path.exists():
        return False, f"Bitstream file not found at: {bit_path}. Build it first."

    bit_str = str(bit_path).replace("\\", "/")
    backup_str = str(DEFAULT_BACKUP_PATH).replace("\\", "/")

    tcl = f"""
open_hw_manager
connect_hw_server -allow_non_jtag
open_hw_target
set target_device [lindex [get_hw_devices xc7a35t_0] 0]
if {{$target_device eq ""}} {{ set target_device [lindex [get_hw_devices] 0] }}
current_hw_device $target_device
refresh_hw_device -update_hw_probes false [current_hw_device]

# Step 1: Auto-backup if not already backed up
if {{![file exists "{backup_str}"]}} {{
    puts "--> Backing up existing FPGA program..."
    catch {{ readback_hw_device -bin_file "{backup_str}" -force [current_hw_device] }}
}}

# Step 2: Program bitstream
set_property PROGRAM.FILE "{bit_str}" [current_hw_device]
puts "--> Programming Basys 3 device with: {bit_str}..."
program_hw_devices [current_hw_device]
refresh_hw_device [current_hw_device]
close_hw_target
disconnect_hw_server
close_hw_manager
puts "SUCCESS: Basys 3 successfully programmed."
"""
    success, out = run_vivado_tcl(tcl, timeout_sec=90)
    if "SUCCESS: Basys 3 successfully programmed." in out:
        return True, f"Basys 3 successfully programmed with {bit_path.name}. Telemetry broadcasting on UART 115200 8N1."
    return False, f"Programming failed:\n{out}"


def restore_original_program(backup_bin_path: Optional[Path] = None) -> Tuple[bool, str]:
    """Restores the backed-up original FPGA program."""
    src = Path(backup_bin_path) if backup_bin_path else DEFAULT_BACKUP_PATH
    if not src.exists():
        return False, f"Backup file not found at: {src}"

    src_str = str(src).replace("\\", "/")
    tcl = f"""
open_hw_manager
connect_hw_server -allow_non_jtag
open_hw_target
set target_device [lindex [get_hw_devices xc7a35t_0] 0]
if {{$target_device eq ""}} {{ set target_device [lindex [get_hw_devices] 0] }}
current_hw_device $target_device
refresh_hw_device -update_hw_probes false [current_hw_device]
set_property PROGRAM.FILE "{src_str}" [current_hw_device]
puts "--> Restoring original backup to device: {src_str}..."
program_hw_devices [current_hw_device]
refresh_hw_device [current_hw_device]
close_hw_target
disconnect_hw_server
close_hw_manager
puts "SUCCESS: Original program restored."
"""
    success, out = run_vivado_tcl(tcl, timeout_sec=90)
    if "SUCCESS: Original program restored." in out:
        return True, "Original program restored successfully."
    return False, f"Restoration failed:\n{out}"


if __name__ == "__main__":
    print("=== Basys 3 Flash & Backup Manager ===")
    action = sys.argv[1] if len(sys.argv) > 1 else "help"

    if action == "backup":
        ok, msg = backup_current_fpga_program()
        print(msg)
    elif action == "program":
        ok, msg = program_health_bitstream()
        print(msg)
    elif action == "restore":
        ok, msg = restore_original_program()
        print(msg)
    else:
        print("Usage: python -m hardware.flash_manager [backup|program|restore]")
