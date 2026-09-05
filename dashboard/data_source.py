"""
Modular Data Source Interface for FPGA Health Monitoring
=========================================================
Provides clean abstraction for swapping between:
- Mock CSV Dataset Replay (MockCSVDataSource)
- Real-Time Dynamic Simulation (LiveSimulationDataSource)
- Physical Basys 3 Artix-7 UART Stream (LiveUARTDataSource)
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List
import time
import random
import numpy as np
import pandas as pd

from config import RO_STAGES, calculate_ro_delay_ns
from ml.feature_engineering import create_features
from communication.uart_receiver import FPGAUARTReceiver
from dashboard.config import SENSOR_CONFIG


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CSV_PATH = PROJECT_ROOT / "data" / "raw" / "mock_fpga_data.csv"


def validate_and_clean_data(df: pd.DataFrame) -> Tuple[pd.DataFrame, bool, List[str]]:
    """
    Validates sensor telemetry for missing columns, NaNs, and impossible physical bounds.
    Returns: (cleaned_df, is_valid, warning_messages)
    """
    warnings: List[str] = []
    if df is None or df.empty:
        return pd.DataFrame(), False, ["No telemetry data received."]

    required_cols = ["Temperature", "VCCINT", "VCCAUX", "VCCBRAM", "RO_Frequency", "Error_Rate"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        return df, False, [f"Missing required sensor channels: {', '.join(missing)}"]

    clean_df = df.copy()

    # Fill NaNs or drop invalid rows
    if clean_df[required_cols].isna().any().any():
        warnings.append("NaN values detected in sensor stream; applying forward-fill interpolation.")
        clean_df = clean_df.ffill().bfill()

    # Check and derive RO_Delay_ns using correct physical formula if missing
    if "RO_Delay_ns" not in clean_df.columns or clean_df["RO_Delay_ns"].isna().any():
        clean_df["RO_Delay_ns"] = clean_df["RO_Frequency"].apply(lambda f: calculate_ro_delay_ns(f, RO_STAGES))

    # Physical bounds checks
    for col, cfg in SENSOR_CONFIG.items():
        if col in clean_df.columns:
            min_v, max_v = cfg["min_valid"], cfg["max_valid"]
            out_of_bounds = ((clean_df[col] < min_v) | (clean_df[col] > max_v)).sum()
            if out_of_bounds > 0:
                warnings.append(f"{out_of_bounds} samples in {col} exceeded physical bounds [{min_v}, {max_v}]. Clipping to valid range.")
                clean_df[col] = clean_df[col].clip(lower=min_v, upper=max_v)

    return clean_df, True, warnings


class BaseDataSource(ABC):
    """Abstract interface for FPGA Telemetry Providers."""

    @abstractmethod
    def get_data(self, window_size: int = 150, sample_idx: Optional[int] = None) -> Tuple[pd.DataFrame, pd.Series, Dict[str, Any]]:
        pass

    @abstractmethod
    def reset(self):
        pass


class MockCSVDataSource(BaseDataSource):
    """
    Replays historical mock dataset from CSV file.
    Supports step-by-step scrubber/playhead indexing.
    """

    def __init__(self, csv_path: Path = DEFAULT_CSV_PATH):
        self.csv_path = csv_path
        self.raw_df: pd.DataFrame = pd.DataFrame()
        self.engineered_df: pd.DataFrame = pd.DataFrame()
        self.baseline_sample: Optional[pd.Series] = None
        self.load_data()

    def load_data(self):
        if not self.csv_path.exists():
            raise FileNotFoundError(f"Mock FPGA data file not found at: {self.csv_path}")

        raw = pd.read_csv(self.csv_path)
        clean_df, is_valid, _ = validate_and_clean_data(raw)
        if not is_valid:
            raise ValueError("Mock dataset failed validation checks.")

        self.raw_df = clean_df
        # Baseline from early healthy samples (first 50 samples average)
        early_window = clean_df.head(50)
        self.baseline_sample = early_window[["Temperature", "VCCINT", "VCCAUX", "VCCBRAM", "RO_Frequency", "RO_Delay_ns", "Error_Rate"]].mean()
        
        # Precompute features across full historical dataset
        self.engineered_df = create_features(self.raw_df.copy())

    def get_data(self, window_size: int = 150, sample_idx: Optional[int] = None) -> Tuple[pd.DataFrame, pd.Series, Dict[str, Any]]:
        total_samples = len(self.engineered_df)
        if sample_idx is None or sample_idx >= total_samples:
            sample_idx = total_samples - 1
        elif sample_idx < 0:
            sample_idx = 0

        # Extract window up to sample_idx
        start_idx = max(0, sample_idx - window_size + 1)
        history_df = self.engineered_df.iloc[start_idx:sample_idx + 1].copy()
        latest_sample = self.engineered_df.iloc[sample_idx].copy()

        metadata = {
            "source_type": "MOCK",
            "source_label": "MOCK CSV DATASET",
            "total_samples": total_samples,
            "current_index": sample_idx,
            "baseline": self.baseline_sample.to_dict() if self.baseline_sample is not None else {}
        }
        return history_df, latest_sample, metadata

    def reset(self):
        pass


class LiveSimulationDataSource(BaseDataSource):
    """
    Generates dynamic step-by-step FPGA sensor measurements in real time,
    gradually simulating aging degradation drift.
    """

    def __init__(self, buffer_size: int = 200):
        self.buffer_size = buffer_size
        self.buffer: List[Dict[str, float]] = []
        self.step_count = 0
        self.baseline_sample = {
            "Temperature": 35.0,
            "VCCINT": 1.000,
            "VCCAUX": 1.800,
            "VCCBRAM": 1.000,
            "RO_Frequency": 250.0,
            "RO_Delay_ns": 0.4000,
            "Error_Rate": 0.00001
        }
        self._initialize_buffer()

    def _initialize_buffer(self):
        self.buffer.clear()
        self.step_count = 0
        for i in range(50):
            deg = i / 1000.0
            meas = self._generate_step(deg)
            self.buffer.append(meas)

    def _generate_step(self, degradation: float) -> Dict[str, float]:
        self.step_count += 1
        deg = min(1.0, max(0.0, degradation))
        
        temp = 35.0 + 18.0 * deg + np.random.normal(0, 0.7)
        vccint = 1.000 - 0.010 * deg + np.random.normal(0, 0.0008)
        vccaux = 1.800 - 0.010 * deg + np.random.normal(0, 0.0008)
        vccbram = 1.000 - 0.008 * deg + np.random.normal(0, 0.0008)
        ro_freq = 250.0 - 15.0 * deg + np.random.normal(0, 0.6)
        ro_delay = calculate_ro_delay_ns(ro_freq, stages=RO_STAGES)
        base_err = 0.00001 + 0.003 * deg
        err_rate = max(0.0, base_err + np.random.normal(0, 0.00015))

        return {
            "Timestamp": time.time(),
            "Temperature": round(temp, 2),
            "VCCINT": round(vccint, 4),
            "VCCAUX": round(vccaux, 4),
            "VCCBRAM": round(vccbram, 4),
            "RO_Frequency": round(ro_freq, 2),
            "RO_Delay_ns": round(ro_delay, 4),
            "Error_Rate": round(err_rate, 6)
        }

    def step(self, degradation: float = 0.0):
        new_meas = self._generate_step(degradation)
        self.buffer.append(new_meas)
        if len(self.buffer) > self.buffer_size:
            self.buffer.pop(0)

    def get_data(self, window_size: int = 150, sample_idx: Optional[int] = None) -> Tuple[pd.DataFrame, pd.Series, Dict[str, Any]]:
        raw_df = pd.DataFrame(self.buffer)
        clean_df, _, _ = validate_and_clean_data(raw_df)
        engineered_df = create_features(clean_df)

        history_df = engineered_df.tail(window_size).copy()
        latest_sample = engineered_df.iloc[-1].copy()

        metadata = {
            "source_type": "SIMULATION",
            "source_label": "DYNAMIC SIMULATION STREAM",
            "total_samples": len(engineered_df),
            "current_index": len(engineered_df) - 1,
            "baseline": self.baseline_sample
        }
        return history_df, latest_sample, metadata

    def reset(self):
        self._initialize_buffer()


class LiveUARTDataSource(BaseDataSource):
    """
    Receives live sensor telemetry over Serial/UART from the physical Artix-7 board.
    Buffers historical incoming measurements to generate rolling feature windows.
    """

    def __init__(self, port: str = "COM3", baudrate: int = 115200, buffer_size: int = 200):
        self.receiver = FPGAUARTReceiver(port=port, baudrate=baudrate)
        self.buffer_size = buffer_size
        self.buffer: List[Dict[str, float]] = []
        self.baseline_sample: Optional[Dict[str, float]] = None

    def connect(self) -> bool:
        return self.receiver.connect()

    def disconnect(self):
        self.receiver.disconnect()

    def poll_hardware(self) -> Optional[Dict[str, float]]:
        packet = self.receiver.read_packet()
        if packet:
            self.buffer.append(packet)
            if len(self.buffer) > self.buffer_size:
                self.buffer.pop(0)
            if self.baseline_sample is None and len(self.buffer) >= 5:
                init_df = pd.DataFrame(self.buffer[:5])
                self.baseline_sample = init_df[["Temperature", "VCCINT", "VCCAUX", "VCCBRAM", "RO_Frequency", "RO_Delay_ns", "Error_Rate"]].mean().to_dict()
        return packet

    def get_data(self, window_size: int = 150, sample_idx: Optional[int] = None) -> Tuple[pd.DataFrame, pd.Series, Dict[str, Any]]:
        if not self.buffer:
            dummy = [{
                "Timestamp": time.time(),
                "Temperature": 35.0,
                "VCCINT": 1.000,
                "VCCAUX": 1.800,
                "VCCBRAM": 1.000,
                "RO_Frequency": 250.0,
                "RO_Delay_ns": 0.4000,
                "Error_Rate": 0.00001
            }]
            raw_df = pd.DataFrame(dummy)
        else:
            raw_df = pd.DataFrame(self.buffer)

        clean_df, _, _ = validate_and_clean_data(raw_df)
        engineered_df = create_features(clean_df)

        history_df = engineered_df.tail(window_size).copy()
        latest_sample = engineered_df.iloc[-1].copy()

        metadata = {
            "source_type": "LIVE_UART",
            "source_label": f"LIVE UART ({self.receiver.port})",
            "is_connected": self.receiver.is_connected,
            "packet_count": self.receiver.packet_count,
            "baseline": self.baseline_sample or {
                "Temperature": 35.0,
                "VCCINT": 1.000,
                "VCCAUX": 1.800,
                "VCCBRAM": 1.000,
                "RO_Frequency": 250.0,
                "RO_Delay_ns": 0.4000,
                "Error_Rate": 0.00001
            }
        }
        return history_df, latest_sample, metadata

    def reset(self):
        self.buffer.clear()
        self.baseline_sample = None
