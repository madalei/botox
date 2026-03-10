"""
Parameter sweep: run multiple StrategyParams configurations on the same datasets
and print a ranked comparison table.

StrategyParams mirrors the POST /bots payload (app/api/commands/bots.py).

Datasets are built by concatenating monthly CSV files from tests/data/.
Missing months are skipped automatically — the label shows how many months
were actually loaded, so you know how complete each dataset is.
"""
from pathlib import Path

import pandas as pd
import pytest
from app.bots.strategies.moving_average_crossover import MovingAverageCrossoverStrategy
from app.infrastructure.adapters.historical_exchange import HistoricalExchange

import logging

logging.disable(logging.CRITICAL)  # suppress all logs for this test

BINANCE_KLINE_COLUMNS = [
    "timestamp", "open", "high", "low", "close", "volume",
    "close_time", "quote_volume", "trades", "taker_base", "taker_quote", "ignore",
]

DATA_DIR = Path(__file__).parent / "data"

# ---------------------------------------------------------------------------
# Strategy configurations — mirrors POST /bots StrategyParams
# ---------------------------------------------------------------------------
STRATEGY_CONFIGS = [
    # 1h timeframe
    {"name": "default 20/50",   "timeframe": "1h", "short_window": 20, "long_window": 50,  "stop_loss_pct": 0.02, "take_profit_pct": 0.04},
    {"name": "aggressive 9/21", "timeframe": "1h", "short_window": 9,  "long_window": 21,  "stop_loss_pct": 0.02, "take_profit_pct": 0.04},
    {"name": "tight SL 9/21",   "timeframe": "1h", "short_window": 9,  "long_window": 21,  "stop_loss_pct": 0.01, "take_profit_pct": 0.04},
    {"name": "wide RR 20/50",   "timeframe": "1h", "short_window": 20, "long_window": 50,  "stop_loss_pct": 0.015,"take_profit_pct": 0.06},
    # 4h timeframe
    {"name": "4h 9/21",         "timeframe": "4h", "short_window": 9,  "long_window": 21,  "stop_loss_pct": 0.02, "take_profit_pct": 0.04},
]

# results:
#   ┌─────────────────┬──────┬───────┬──────┬──────┬───────┐
#   │     Config      │ 2022 │ 2023  │ 2024 │ 2025 │ Total │
#   ├─────────────────┼──────┼───────┼──────┼──────┼───────┤
#   │ tight SL 9/21   │ -566 │ +1059 │ +534 │ -159 │ +868  │
#   ├─────────────────┼──────┼───────┼──────┼──────┼───────┤
#   │ aggressive 9/21 │ -283 │ +529  │ +267 │ -79  │ +434  │
#   ├─────────────────┼──────┼───────┼──────┼──────┼───────┤
#   │ wide RR 20/50   │ -197 │ +527  │ +362 │ -279 │ +413  │
#   ├─────────────────┼──────┼───────┼──────┼──────┼───────┤
#   │ default 20/50   │ -148 │ +395  │ +271 │ -209 │ +309  │
#   └─────────────────┴──────┴───────┴──────┴──────┴───────┘

# ---------------------------------------------------------------------------
# Yearly datasets — each entry defines a symbol, timeframe, and year.
# Monthly CSVs are concatenated automatically; missing months are skipped.
# ---------------------------------------------------------------------------
YEARLY_DATASETS = [
    {"symbol": "BTCUSDT", "timeframe": "1h", "year": 2022},
    {"symbol": "BTCUSDT", "timeframe": "1h", "year": 2023},
    {"symbol": "BTCUSDT", "timeframe": "1h", "year": 2024},
    {"symbol": "BTCUSDT", "timeframe": "1h", "year": 2025},
    {"symbol": "BTCUSDT", "timeframe": "1h", "year": 2026},
    {"symbol": "BTCUSDT", "timeframe": "4h", "year": 2025},
]


def load_year(symbol: str, timeframe: str, year: int) -> tuple[pd.DataFrame, list[int]]:
    """
    Concatenate all available monthly CSV files for the given symbol/timeframe/year.
    Returns (dataframe, list_of_loaded_months).
    Missing months are silently skipped.
    """
    frames = []
    loaded_months = []
    for month in range(1, 13):
        path = DATA_DIR / f"{symbol}-{timeframe}-{year}-{month:02d}.csv"
        if path.exists():
            frames.append(pd.read_csv(path, names=BINANCE_KLINE_COLUMNS))
            loaded_months.append(month)
    if not frames:
        return pd.DataFrame(), []
    return pd.concat(frames, ignore_index=True), loaded_months


async def run_backtest(candles: pd.DataFrame, strategy: MovingAverageCrossoverStrategy, capital: float = 1000.0):
    exchange = HistoricalExchange(candles)
    orders = []
    while exchange.tick():
        signal = await strategy.generate_signals(exchange, capital=capital)
        if signal:
            orders.append(signal)

    # If the backtest ends with an open position (last BUY has no matching SELL),
    # close it at the final candle's close price so it is included in P&L.
    buys = [o for o in orders if o.side == "BUY"]
    sells = [o for o in orders if o.side == "SELL"]
    if len(buys) > len(sells):
        from app.models.order import Order
        from datetime import datetime
        last_price = float(candles.iloc[-1]["close"])
        orders.append(Order(
            bot_id="",
            symbol=buys[-1].symbol,
            side="SELL",
            amount=buys[-1].amount,
            price=last_price,
            created_at=datetime.now(),
        ))

    return orders


def compute_pnl(orders):
    pnl = 0.0
    buys = [o for o in orders if o.side == "BUY"]
    sells = [o for o in orders if o.side == "SELL"]
    for buy, sell in zip(buys, sells):
        pnl += (float(sell.price) - float(buy.price)) * float(buy.amount)
    return pnl, len(buys), len(sells)


@pytest.mark.asyncio
async def test_param_sweep():
    results = []

    for ds in YEARLY_DATASETS:
        candles, loaded_months = load_year(ds["symbol"], ds["timeframe"], ds["year"])
        if candles.empty:
            continue

        # Label shows timeframe, year, and how many months were loaded
        label = f"{ds['timeframe']} {ds['year']} ({len(loaded_months)}/12 months)"

        for cfg in STRATEGY_CONFIGS:
            if cfg["timeframe"] != ds["timeframe"]:
                continue

            strategy = MovingAverageCrossoverStrategy(
                timeframe=cfg["timeframe"],
                short_window=cfg["short_window"],
                long_window=cfg["long_window"],
                stop_loss_pct=cfg["stop_loss_pct"],
                take_profit_pct=cfg["take_profit_pct"],
            )

            orders = await run_backtest(candles, strategy)
            pnl, n_buys, n_sells = compute_pnl(orders)

            results.append({
                "dataset":  label,
                "config":   cfg["name"],
                "sl/tp":    f"{cfg['stop_loss_pct']*100:.1f}%/{cfg['take_profit_pct']*100:.1f}%",
                "buys":     n_buys,
                "sells":    n_sells,
                "completed":min(n_buys, n_sells),
                "pnl":      pnl,
            })

    # Print grouped by dataset, sorted by P&L descending
    print()
    current_dataset = None
    for r in sorted(results, key=lambda x: (x["dataset"], -x["pnl"])):
        if r["dataset"] != current_dataset:
            current_dataset = r["dataset"]
            print(f"\n{'='*72}")
            print(f"  {current_dataset}")
            print(f"{'='*72}")
            print(f"  {'Config':<22} {'SL/TP':<10} {'Buys':<6} {'Sells':<6} {'Done':<6} {'P&L':>10}")
            print(f"  {'-'*22} {'-'*10} {'-'*6} {'-'*6} {'-'*6} {'-'*10}")

        print(
            f"  {r['config']:<22} {r['sl/tp']:<10} "
            f"{r['buys']:<6} {r['sells']:<6} {r['completed']:<6} "
            f"{r['pnl']:>+10.2f} USDT"
        )

    assert len(results) > 0, "No results — check that CSV files exist in tests/data/"
    for r in results:
        assert r["buys"] >= 0 and r["sells"] >= 0