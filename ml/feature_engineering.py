import pandas as pd


def create_features(df):

    # --------------------------------------------------------
    # Basic features
    # --------------------------------------------------------

    df["Temperature_change"] = (
        df["Temperature"]
        .diff()
        .fillna(0)
    )

    df["RO_Frequency_change"] = (
        df["RO_Frequency"]
        .diff()
        .fillna(0)
    )

    df["RO_Delay_change"] = (
        df["RO_Delay_ns"]
        .diff()
        .fillna(0)
    )

    df["Error_Rate_change"] = (
        df["Error_Rate"]
        .diff()
        .fillna(0)
    )

    # --------------------------------------------------------
    # Rolling features
    # --------------------------------------------------------

    window = 20

    df["Temperature_mean"] = (
        df["Temperature"]
        .rolling(window)
        .mean()
        .bfill()
    )

    df["Temperature_std"] = (
        df["Temperature"]
        .rolling(window)
        .std()
        .fillna(0)
    )

    df["RO_Frequency_mean"] = (
        df["RO_Frequency"]
        .rolling(window)
        .mean()
        .bfill()
    )

    df["RO_Frequency_std"] = (
        df["RO_Frequency"]
        .rolling(window)
        .std()
        .fillna(0)
    )

    df["Error_Rate_mean"] = (
        df["Error_Rate"]
        .rolling(window)
        .mean()
        .bfill()
    )

    return df