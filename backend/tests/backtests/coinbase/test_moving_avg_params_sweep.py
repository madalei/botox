"""
Moving average crossover parameter sweep on Coinbase BTC-EUR, net of fees.
Configs mirror the POST /bots StrategyParams (app/api/commands/bots.py).

Slow: excluded from a plain `pytest` by pytest.ini, run it with:
    pytest tests/backtests/coinbase/test_moving_avg_params_sweep.py -s -o addopts=""
"""
import logging

import pytest
from app.bots.strategies.moving_average_crossover import MovingAverageCrossoverStrategy
from tests.backtests.coinbase.sweep import print_results, run_sweep

logging.disable(logging.CRITICAL)  # suppress all logs for this test

# Names must be unique: the summary groups results by name.
# A round trip costs 1.2% of fees on Coinbase, so slower / wider configs are included:
# fewer trades, and a take profit large compared to the fees.
STRATEGY_CONFIGS = [
    # 1h timeframe
    {"name": "1h 20/50",          "timeframe": "1h", "short_window": 20, "long_window": 50,  "stop_loss_pct": 0.02,  "take_profit_pct": 0.04},
    {"name": "1h 9/21",           "timeframe": "1h", "short_window": 9,  "long_window": 21,  "stop_loss_pct": 0.02,  "take_profit_pct": 0.04},
    {"name": "1h 20/50 wide RR",  "timeframe": "1h", "short_window": 20, "long_window": 50,  "stop_loss_pct": 0.015, "take_profit_pct": 0.06},
    {"name": "1h 50/200",         "timeframe": "1h", "short_window": 50, "long_window": 200, "stop_loss_pct": 0.02,  "take_profit_pct": 0.04},
    {"name": "1h 50/200 3/9",     "timeframe": "1h", "short_window": 50, "long_window": 200, "stop_loss_pct": 0.03,  "take_profit_pct": 0.09},
    # 6h timeframe
    {"name": "6h 9/21",           "timeframe": "6h", "short_window": 9,  "long_window": 21,  "stop_loss_pct": 0.02,  "take_profit_pct": 0.04},
    {"name": "6h 20/50",          "timeframe": "6h", "short_window": 20, "long_window": 50,  "stop_loss_pct": 0.02,  "take_profit_pct": 0.04},
    {"name": "6h 20/50 3/9",      "timeframe": "6h", "short_window": 20, "long_window": 50,  "stop_loss_pct": 0.03,  "take_profit_pct": 0.09},
]


def build_strategy(cfg: dict) -> MovingAverageCrossoverStrategy:
    return MovingAverageCrossoverStrategy(
        symbol="BTC/EUR",
        timeframe=cfg["timeframe"],
        short_window=cfg["short_window"],
        long_window=cfg["long_window"],
        stop_loss_pct=cfg["stop_loss_pct"],
        take_profit_pct=cfg["take_profit_pct"],
    )


@pytest.mark.asyncio
async def test_moving_avg_param_sweep():
    results = await run_sweep(STRATEGY_CONFIGS, build_strategy)
    print_results(results)

    assert results, "No results — download candles into tests/backtests/coinbase/data/, see scripts/download_coinbase_candles.py"
