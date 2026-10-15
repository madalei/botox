"""
RSI strategy parameter sweep on Coinbase BTC-EUR, net of fees.

Slow: excluded from a plain `pytest` by pytest.ini, run it with:
    pytest tests/backtests/coinbase/test_rsi_params_sweep.py -s -o addopts=""
"""
import logging

import pytest
from app.bots.strategies.rsi_strategy import RsiStrategy
from tests.backtests.coinbase.sweep import print_results, run_sweep

logging.disable(logging.CRITICAL)

# Names must be unique: the summary groups results by name.
RSI_CONFIGS = [
    # 1h timeframe
    {"name": "1h rsi14 30/70",      "timeframe": "1h", "rsi_period": 14, "rsi_oversold": 30, "rsi_overbought": 70, "stop_loss_pct": 0.02,  "take_profit_pct": 0.04},
    {"name": "1h rsi7 30/70",       "timeframe": "1h", "rsi_period": 7,  "rsi_oversold": 30, "rsi_overbought": 70, "stop_loss_pct": 0.02,  "take_profit_pct": 0.04},
    {"name": "1h rsi21 30/70",      "timeframe": "1h", "rsi_period": 21, "rsi_oversold": 30, "rsi_overbought": 70, "stop_loss_pct": 0.02,  "take_profit_pct": 0.04},
    {"name": "1h rsi14 25/75",      "timeframe": "1h", "rsi_period": 14, "rsi_oversold": 25, "rsi_overbought": 75, "stop_loss_pct": 0.02,  "take_profit_pct": 0.04},
    {"name": "1h rsi14 30/70 wRR",  "timeframe": "1h", "rsi_period": 14, "rsi_oversold": 30, "rsi_overbought": 70, "stop_loss_pct": 0.015, "take_profit_pct": 0.06},
    {"name": "1h rsi14 30/70 tSL",  "timeframe": "1h", "rsi_period": 14, "rsi_oversold": 30, "rsi_overbought": 70, "stop_loss_pct": 0.01,  "take_profit_pct": 0.04},
    {"name": "1h rsi14 25/75 3/9",  "timeframe": "1h", "rsi_period": 14, "rsi_oversold": 25, "rsi_overbought": 75, "stop_loss_pct": 0.03,  "take_profit_pct": 0.09},
    # 6h timeframe
    {"name": "6h rsi14 30/70",      "timeframe": "6h", "rsi_period": 14, "rsi_oversold": 30, "rsi_overbought": 70, "stop_loss_pct": 0.02,  "take_profit_pct": 0.04},
    {"name": "6h rsi14 30/70 3/9",  "timeframe": "6h", "rsi_period": 14, "rsi_oversold": 30, "rsi_overbought": 70, "stop_loss_pct": 0.03,  "take_profit_pct": 0.09},
]


def build_strategy(cfg: dict) -> RsiStrategy:
    return RsiStrategy(
        symbol="BTC/EUR",
        timeframe=cfg["timeframe"],
        rsi_period=cfg["rsi_period"],
        rsi_oversold=cfg["rsi_oversold"],
        rsi_overbought=cfg["rsi_overbought"],
        stop_loss_pct=cfg["stop_loss_pct"],
        take_profit_pct=cfg["take_profit_pct"],
    )


@pytest.mark.asyncio
async def test_rsi_param_sweep():
    results = await run_sweep(RSI_CONFIGS, build_strategy)
    print_results(results)

    assert results, "No results — download candles into tests/backtests/coinbase/data/, see scripts/download_coinbase_candles.py"
