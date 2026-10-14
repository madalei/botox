"""
RSI strategy parameter sweep.
Runs multiple RSI configurations on yearly datasets and prints a ranked comparison table.
"""

import logging
import pytest
from app.bots.strategies.rsi_strategy import RsiStrategy
from tests.backtests.binance.market import FEE_RATE, load_year
from tests.backtests.engine import compute_pnl, run_backtest

logging.disable(logging.CRITICAL)

# ---------------------------------------------------------------------------
# RSI configurations to compare
# ---------------------------------------------------------------------------
RSI_CONFIGS = [
    # Standard
    {"name": "rsi14 30/70",     "timeframe": "1h", "rsi_period": 14, "rsi_oversold": 30, "rsi_overbought": 70, "stop_loss_pct": 0.02, "take_profit_pct": 0.04},
    # Faster period
    {"name": "rsi7 30/70",      "timeframe": "1h", "rsi_period": 7,  "rsi_oversold": 30, "rsi_overbought": 70, "stop_loss_pct": 0.02, "take_profit_pct": 0.04},
    # Slower period
    {"name": "rsi21 30/70",     "timeframe": "1h", "rsi_period": 21, "rsi_oversold": 30, "rsi_overbought": 70, "stop_loss_pct": 0.02, "take_profit_pct": 0.04},
    # Stricter thresholds — only extreme reversals
    {"name": "rsi14 25/75",     "timeframe": "1h", "rsi_period": 14, "rsi_oversold": 25, "rsi_overbought": 75, "stop_loss_pct": 0.02, "take_profit_pct": 0.04},
    # More permissive thresholds — more trades
    {"name": "rsi14 35/65",     "timeframe": "1h", "rsi_period": 14, "rsi_oversold": 35, "rsi_overbought": 65, "stop_loss_pct": 0.02, "take_profit_pct": 0.04},
    # Wide risk/reward
    {"name": "rsi14 30/70 wRR", "timeframe": "1h", "rsi_period": 14, "rsi_oversold": 30, "rsi_overbought": 70, "stop_loss_pct": 0.015,"take_profit_pct": 0.06},
    # Tight stop loss
    {"name": "rsi14 30/70 tSL", "timeframe": "1h", "rsi_period": 14, "rsi_oversold": 30, "rsi_overbought": 70, "stop_loss_pct": 0.01, "take_profit_pct": 0.04},
]

YEARLY_DATASETS = [
    {"symbol": "BTCUSDT", "timeframe": "1h", "year": 2022},
    {"symbol": "BTCUSDT", "timeframe": "1h", "year": 2023},
    {"symbol": "BTCUSDT", "timeframe": "1h", "year": 2024},
    {"symbol": "BTCUSDT", "timeframe": "1h", "year": 2025},
    {"symbol": "BTCUSDT", "timeframe": "1h", "year": 2026},
]


@pytest.mark.asyncio
async def test_rsi_param_sweep():
    results = []

    for ds in YEARLY_DATASETS:
        candles, loaded_months = load_year(ds["symbol"], ds["timeframe"], ds["year"])
        if candles.empty:
            continue

        label = f"{ds['timeframe']} {ds['year']} ({len(loaded_months)}/12 months)"

        for cfg in RSI_CONFIGS:
            if cfg["timeframe"] != ds["timeframe"]:
                continue

            strategy = RsiStrategy(
                timeframe=cfg["timeframe"],
                rsi_period=cfg["rsi_period"],
                rsi_oversold=cfg["rsi_oversold"],
                rsi_overbought=cfg["rsi_overbought"],
                stop_loss_pct=cfg["stop_loss_pct"],
                take_profit_pct=cfg["take_profit_pct"],
            )

            orders = await run_backtest(candles, strategy)
            pnl, fees, completed = compute_pnl(orders, FEE_RATE)
            n_buys = sum(o.side == "BUY" for o in orders)
            n_sells = sum(o.side == "SELL" for o in orders)

            results.append({
                "dataset":   label,
                "config":    cfg["name"],
                "sl/tp":     f"{cfg['stop_loss_pct']*100:.1f}%/{cfg['take_profit_pct']*100:.1f}%",
                "buys":      n_buys,
                "sells":     n_sells,
                "completed": completed,
                "fees":      fees,
                "pnl":       pnl,
            })

    print()
    current_dataset = None
    for r in sorted(results, key=lambda x: (x["dataset"], -x["pnl"])):
        if r["dataset"] != current_dataset:
            current_dataset = r["dataset"]
            print(f"\n{'='*72}")
            print(f"  {current_dataset}")
            print(f"{'='*72}")
            print(f"  {'Config':<22} {'SL/TP':<10} {'Buys':<6} {'Sells':<6} {'Done':<6} {'Fees':>8} {'P&L (net)':>10}")
            print(f"  {'-'*22} {'-'*10} {'-'*6} {'-'*6} {'-'*6} {'-'*8} {'-'*10}")

        print(
            f"  {r['config']:<22} {r['sl/tp']:<10} "
            f"{r['buys']:<6} {r['sells']:<6} {r['completed']:<6} {r['fees']:>8.2f} "
            f"{r['pnl']:>+10.2f} USDT"
        )

    assert len(results) > 0, "No results — check that CSV files exist in tests/backtests/binance/data/"