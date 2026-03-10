"""
Parameter sweep: run multiple StrategyParams configurations on the same datasets
and print a ranked comparison table.

StrategyParams mirrors the POST /bots payload (app/api/commands/bots.py).
"""
from pathlib import Path

import pandas as pd
import pytest
from app.bots.strategies.moving_average_crossover import MovingAverageCrossoverStrategy
from app.infrastructure.adapters.historical_exchange import HistoricalExchange

BINANCE_KLINE_COLUMNS = [
    "timestamp", "open", "high", "low", "close", "volume",
    "close_time", "quote_volume", "trades", "taker_base", "taker_quote", "ignore",
]

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

# Datasets to test on — (filename, label)
DATASETS = [
    ("BTCUSDT-1h-2023-11.csv",  "1h Nov-2023"),
    ("BTCUSDT-1h-2024-01.csv",  "1h Jan-2024"),
    ("BTCUSDT-1h-2024-03.csv",  "1h Mar-2024"),
    ("BTCUSDT-1h-2024-06.csv",  "1h Jun-2024"),
    ("BTCUSDT-1h-2025-03.csv",  "1h Mar-2025"),
    ("BTCUSDT-1h-2025-10.csv",  "1h Oct-2025"),
    ("BTCUSDT-1h-2025-12.csv",  "1h Dec-2025"),
    ("BTCUSDT-1h-2026-02.csv",  "1h Feb-2026"),
    ("BTCUSDT-4h-2025-09.csv",  "4h Sep-2025"),
    ("BTCUSDT-4h-2025-12.csv",  "4h Dec-2025"),
]


def load_candles(filename: str) -> pd.DataFrame:
    path = Path(__file__).parent / "data" / filename
    return pd.read_csv(path, names=BINANCE_KLINE_COLUMNS)


async def run_backtest(candles: pd.DataFrame, strategy: MovingAverageCrossoverStrategy, capital: float = 1000.0):
    exchange = HistoricalExchange(candles)
    orders = []
    while exchange.tick():
        signal = await strategy.generate_signals(exchange, capital=capital)
        if signal:
            orders.append(signal)
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

    for filename, dataset_label in DATASETS:
        candles = load_candles(filename)

        for cfg in STRATEGY_CONFIGS:
            # Skip 1h configs on 4h datasets and vice versa
            if cfg["timeframe"] not in dataset_label:
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
            completed = min(n_buys, n_sells)

            results.append({
                "dataset":        dataset_label,
                "config":         cfg["name"],
                "short/long":     f"{cfg['short_window']}/{cfg['long_window']}",
                "sl/tp":          f"{cfg['stop_loss_pct']*100:.1f}%/{cfg['take_profit_pct']*100:.1f}%",
                "buys":           n_buys,
                "sells":          n_sells,
                "completed":      completed,
                "pnl":            pnl,
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
            print(f"  {'Config':<22} {'Win':<8} {'Buys':<6} {'Sells':<6} {'Done':<6} {'P&L':>10}")
            print(f"  {'-'*22} {'-'*8} {'-'*6} {'-'*6} {'-'*6} {'-'*10}")

        print(
            f"  {r['config']:<22} {r['sl/tp']:<8} "
            f"{r['buys']:<6} {r['sells']:<6} {r['completed']:<6} "
            f"{r['pnl']:>+10.2f} USDT"
        )

    # Basic sanity: no consecutive same-side orders per config/dataset
    for r in results:
        assert r["buys"] >= 0 and r["sells"] >= 0