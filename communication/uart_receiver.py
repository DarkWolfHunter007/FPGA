"""
UART Receiver Module for FPGA Telemetry Communication
=====================================================
Interfaces with the physical FPGA board (e.g., Digilent Basys 3 Artix-7)
over Serial / UART to receive real-time on-chip sensor telemetry.
"""

import json
import time
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import RO_STAGES, calculate_ro_delay_ns

try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False


class FPGAUARTReceiver:
    """
    UART Communication interface for physical FPGA telemetry collection.
    """

    def __init__(self, port: str = "COM3", baudrate: int = 115200, timeout: float = 1.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_conn: Optional[Any] = None
        self.is_connected = False
        self.last_valid_packet: Optional[Dict[str, float]] = None
        self.packet_count = 0

    @staticmethod
    def list_available_ports() -> List[str]:
        """List available serial communication ports on the host system."""
        if not SERIAL_AVAILABLE:
            return ["No PySerial Installed"]
        ports = serial.tools.list_ports.comports()
        return [p.device for p in ports] if ports else ["No Ports Detected"]

    def connect(self) -> bool:
        """Open serial connection to the FPGA UART interface."""
        if not SERIAL_AVAILABLE:
            self.is_connected = False
            return False

        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout
            )
            self.is_connected = self.serial_conn.is_open
            return self.is_connected
        except Exception:
            self.is_connected = False
            self.serial_conn = None
            return False

    def disconnect(self):
        """Safely close serial port connection."""
        if self.serial_conn and self.serial_conn.is_open:
            try:
                self.serial_conn.close()
            except Exception:
                pass
        self.is_connected = False
        self.serial_conn = None

    def read_packet(self) -> Optional[Dict[str, float]]:
        """
        Read and decode a single telemetry packet from the FPGA UART stream.
        Returns parsed sensor dictionary or None if packet is invalid or unavailable.
        """
        if not self.is_connected or not self.serial_conn:
            return None

        try:
            if self.serial_conn.in_waiting > 0:
                raw_line = self.serial_conn.readline().decode("utf-8", errors="ignore").strip()
                if not raw_line:
                    return None

                parsed = self._parse_raw_line(raw_line)
                if parsed:
                    self.last_valid_packet = parsed
                    self.packet_count += 1
                    return parsed
        except Exception:
            return None

        return None

    def _parse_raw_line(self, line: str) -> Optional[Dict[str, float]]:
        """Parse raw UART line into structured sensor dictionary."""
        if line.startswith("{") and line.endswith("}"):
            try:
                data = json.loads(line)
                return self._sanitize_packet(data)
            except json.JSONDecodeError:
                pass

        if ":" in line:
            data = {}
            parts = line.split(",")
            for part in parts:
                if ":" in part:
                    k, v = part.split(":", 1)
                    k = k.strip().upper()
                    try:
                        v_num = float(v.strip())
                        if "TEMP" in k:
                            data["Temperature"] = v_num
                        elif "VCCINT" in k:
                            data["VCCINT"] = v_num
                        elif "VCCAUX" in k:
                            data["VCCAUX"] = v_num
                        elif "VCCBRAM" in k:
                            data["VCCBRAM"] = v_num
                        elif "RO" in k or "FREQ" in k:
                            data["RO_Frequency"] = v_num
                        elif "ERR" in k:
                            data["Error_Rate"] = v_num
                    except ValueError:
                        continue
            if data:
                return self._sanitize_packet(data)

        return None

    def _sanitize_packet(self, data: Dict[str, Any]) -> Optional[Dict[str, float]]:
        """Validate and fill standard FPGA sensor measurement fields."""
        try:
            temp = float(data.get("Temperature", data.get("temp", 35.0)))
            vccint = float(data.get("VCCINT", data.get("vccint", 1.000)))
            vccaux = float(data.get("VCCAUX", data.get("vccaux", 1.800)))
            vccbram = float(data.get("VCCBRAM", data.get("vccbram", 1.000)))
            ro_freq = float(data.get("RO_Frequency", data.get("ro_frequency", 250.0)))
            error_rate = float(data.get("Error_Rate", data.get("error_rate", 0.0)))

            # Correct physical derivation: tau_ns = 1000 / (2 * N * f_MHz)
            ro_delay_ns = calculate_ro_delay_ns(ro_freq, stages=RO_STAGES) if ro_freq > 0 else 0.4000

            # Basic physical bounds validation
            if not (0 <= temp <= 125):
                return None
            if not (0.5 <= vccint <= 1.5):
                return None
            if not (1.0 <= vccaux <= 2.5):
                return None
            if not (0.5 <= vccbram <= 1.5):
                return None
            if not (50 <= ro_freq <= 500):
                return None

            return {
                "Temperature": round(temp, 2),
                "VCCINT": round(vccint, 4),
                "VCCAUX": round(vccaux, 4),
                "VCCBRAM": round(vccbram, 4),
                "RO_Frequency": round(ro_freq, 2),
                "RO_Delay_ns": round(ro_delay_ns, 4),
                "Error_Rate": max(0.0, float(error_rate)),
                "Timestamp": time.time()
            }
        except (ValueError, TypeError):
            return None


if __name__ == "__main__":
    print("Available Serial Ports:", FPGAUARTReceiver.list_available_ports())
    receiver = FPGAUARTReceiver(port="COM3")
    print(f"Receiver configured on {receiver.port} @ {receiver.baudrate} baud (RO_STAGES={RO_STAGES}).")
