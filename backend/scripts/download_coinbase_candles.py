"""
Download historical Coinbase candles into tests/backtests/coinbase/data/ for backtesting.

Uses the public Coinbase market data endpoint through ccxt: no API key needed.
One CSV per month, named like the Binance ones: BTC-EUR-1h-2024-03.csv
Columns (with a header row): timestamp (ms), open, high, low, close, volume — oldest first.

Usage (from backend/):
    python scripts/download_coinbase_candles.py --symbol BTC/EUR --timeframe 1h --start 2024-01 --end 2024-12
"""
import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path

import ccxt

DATA_DIR = Path(__file__).resolve().parents[1] / "tests" / "backtests" / "coinbase" / "data"
COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]
MAX_CANDLES_PER_REQUEST = 300  # Coinbase limit


def parse_month(value: str) -> tuple[int, int]:
    parsed = datetime.strptime(value, "%Y-%m")
    return parsed.year, parsed.month


def month_start_ms(year: int, month: int) -> int:
    return int(datetime(year, month, 1, tzinfo=timezone.utc).timestamp() * 1000)


def next_month(year: int, month: int) -> tuple[int, int]:
    return (year + 1, 1) if month == 12 else (year, month + 1)


def fetch_candles(exchange: ccxt.Exchange, symbol: str, timeframe: str, start_ms: int, end_ms: int) -> list[list]:
    """Fetch all closed candles with start_ms <= timestamp < end_ms, 300 at a time."""
    timeframe_ms = exchange.parse_timeframe(timeframe) * 1000
    # A candle still being built would change later: only keep the ones already closed
    end_ms = min(end_ms, exchange.milliseconds() - timeframe_ms + 1)

    candles = {}
    since = start_ms
    while since < end_ms:
        batch = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=MAX_CANDLES_PER_REQUEST)
        for candle in batch:
            if start_ms <= candle[0] < end_ms:
                candles[candle[0]] = candle
        # Coinbase returns no candle for periods without trades, so always move one full window forward
        since += MAX_CANDLES_PER_REQUEST * timeframe_ms

    return [candles[timestamp] for timestamp in sorted(candles)]


def main():
    parser = argparse.ArgumentParser(description="Download Coinbase candles into tests/backtests/coinbase/data/")
    parser.add_argument("--symbol", default="BTC/EUR", help='e.g. "BTC/EUR", "BTC/USDC"')
    parser.add_argument("--timeframe", default="1h", help="1m, 5m, 15m, 30m, 1h, 2h, 6h, 1d (no 4h on Coinbase)")
    parser.add_argument("--start", required=True, help="first month, YYYY-MM")
    parser.add_argument("--end", help="last month included, YYYY-MM (default: same as --start)")
    args = parser.parse_args()

    exchange = ccxt.coinbase()
    if args.timeframe not in exchange.timeframes:
        parser.error(f"timeframe must be one of {', '.join(exchange.timeframes)}")

    year, month = parse_month(args.start)
    last = parse_month(args.end or args.start)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    while (year, month) <= last:
        following = next_month(year, month)
        candles = fetch_candles(
            exchange, args.symbol, args.timeframe,
            month_start_ms(year, month), month_start_ms(*following),
        )
        filename = f"{args.symbol.replace('/', '-')}-{args.timeframe}-{year}-{month:02d}.csv"
        if candles:
            with open(DATA_DIR / filename, "w", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(COLUMNS)
                writer.writerows(candles)
            print(f"{filename}: {len(candles)} candles")
        else:
            print(f"{filename}: no data, skipped")
        year, month = following


if __name__ == "__main__":
    main()
