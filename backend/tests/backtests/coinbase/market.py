"""
Coinbase historical candles, written by scripts/download_coinbase_candles.py, e.g. BTC-EUR-1h-2024-03.csv.
Unlike the Binance CSVs, these have a header row: timestamp (ms), open, high, low, close, volume.
"""
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent / "data"

# Bots send market orders, so they pay the taker fee of the lowest volume tier
FEE_RATE = 0.006  # Coinbase Advanced Trade: 0.60% taker, per side


def load_candles(filename: str) -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / filename)


def load_year(symbol: str, timeframe: str, year: int) -> tuple[pd.DataFrame, list[int]]:
    """
    Concatenate all available monthly CSVs of a year, e.g. ("BTC-EUR", "1h", 2024).
    Returns (candles, list_of_loaded_months). Missing months are silently skipped.
    """
    frames = []
    loaded_months = []
    for month in range(1, 13):
        filename = f"{symbol}-{timeframe}-{year}-{month:02d}.csv"
        if (DATA_DIR / filename).exists():
            frames.append(load_candles(filename))
            loaded_months.append(month)
    if not frames:
        return pd.DataFrame(), []
    return pd.concat(frames, ignore_index=True), loaded_months
