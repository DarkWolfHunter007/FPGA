import pandas as pd


def create_features(df: pd.DataFrame) -> pd.DataFrame:
    """Extract differential and rolling statistical telemetry features for ML classification."""
    # Differential step-change features
    df["Temperature_change"] = df["Temperature"].diff().fillna(0)
    df["RO_Frequency_change"] = df["RO_Frequency"].diff().fillna(0)
    df["RO_Delay_change"] = df["RO_Delay_ns"].diff().fillna(0)
    df["Error_Rate_change"] = df["Error_Rate"].diff().fillna(0)

    # Rolling window statistics (window=20)
    w = 20
    df["Temperature_mean"] = df["Temperature"].rolling(w).mean().bfill()
    df["Temperature_std"] = df["Temperature"].rolling(w).std().fillna(0)
    df["RO_Frequency_mean"] = df["RO_Frequency"].rolling(w).mean().bfill()
    df["RO_Frequency_std"] = df["RO_Frequency"].rolling(w).std().fillna(0)
    df["Error_Rate_mean"] = df["Error_Rate"].rolling(w).mean().bfill()

    return df