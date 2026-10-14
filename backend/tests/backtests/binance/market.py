"""
Binance historical candles, from data.binance.vision (spot / monthly / klines), e.g. BTCUSDT-1h-2024-03.csv.
"""
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent / "data"

# Bots send market orders, so they pay the taker fee of the lowest volume tier
FEE_RATE = 0.001  # Binance spot: 0.10% taker, per side

# Binance monthly klines CSVs have no header row — these are the standard column names
KLINE_COLUMNS = [
    "timestamp", "open", "high", "low", "close", "volume",
    "close_time", "quote_volume", "trades", "taker_base", "taker_quote", "ignore",
]


def load_candles(filename: str) -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / filename, names=KLINE_COLUMNS)


def load_year(symbol: str, timeframe: str, year: int) -> tuple[pd.DataFrame, list[int]]:
    """
    Concatenate all available monthly CSVs of a year, e.g. ("BTCUSDT", "1h", 2024).
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
