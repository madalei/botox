"""
Moving average crossover parameter sweep on Coinbase BTC-EUR, net of fees.
Configs mirror the POST /bots StrategyParams (app/api/commands/bots.py).

Slow: excluded from a plain `pytest` by pytest.ini, run it with:
    pytest tests/backtests/coinbase/test_moving_avg_params_sweep.py -s -o addopts=""
"""
import logging

import pytest
from app.bots.strategies.moving_average_crossover import MovingAverageCrossoverStrategy
from tests.backtests.coinbase.sweep import print_full_period, print_results, run_full_period, run_sweep

logging.disable(logging.CRITICAL)  # suppress all logs for this test

# Les noms doivent être uniques : le résumé regroupe les résultats par nom.
# Légende des noms :
#   T200     = filtre de tendance : achat seulement au-dessus de la MA 200 bougies
#   trail 8% = stop suiveur à 8 % sous le plus haut, sans take profit (le stop initial est à la même distance)
#   BT       = buy_while_trend : achat à toute bougie où la courte > longue, pas seulement au croisement
#              (rachat après un stop si la tendance continue)
#   noX      = exit_on_crossover=False : pas de vente au croisement baissier, seul le stop ferme la position
NO_STOP = 0.99  # stop loss si large qu'il ne se déclenche jamais : sortie uniquement au croisement baissier
STRATEGY_CONFIGS = [
    # --- Références des sweeps précédents ---
    {"name": "1h 20/50",                    "timeframe": "1h", "short_window": 20, "long_window": 50,  "stop_loss_pct": 0.02, "take_profit_pct": 0.04},
    {"name": "6h 20/50 T200 trail 5%",      "timeframe": "6h", "short_window": 20, "long_window": 50,  "stop_loss_pct": 0.05, "take_profit_pct": 0, "trailing_stop_pct": 0.05, "trend_window": 200},

    # --- 6h : rachat tant que la tendance est haussière (BT), avec ou sans vente au croisement (noX) ---
    {"name": "6h 20/50 T200 trail 5% BT",       "timeframe": "6h", "short_window": 20, "long_window": 50, "stop_loss_pct": 0.05, "take_profit_pct": 0, "trailing_stop_pct": 0.05, "trend_window": 200, "buy_while_trend": True},
    {"name": "6h 20/50 T200 trail 10% BT",      "timeframe": "6h", "short_window": 20, "long_window": 50, "stop_loss_pct": 0.10, "take_profit_pct": 0, "trailing_stop_pct": 0.10, "trend_window": 200, "buy_while_trend": True},
    {"name": "6h 20/50 T200 trail 10% BT noX",  "timeframe": "6h", "short_window": 20, "long_window": 50, "stop_loss_pct": 0.10, "take_profit_pct": 0, "trailing_stop_pct": 0.10, "trend_window": 200, "buy_while_trend": True, "exit_on_crossover": False},
    {"name": "6h 20/50 T200 trail 15% BT noX",  "timeframe": "6h", "short_window": 20, "long_window": 50, "stop_loss_pct": 0.15, "take_profit_pct": 0, "trailing_stop_pct": 0.15, "trend_window": 200, "buy_while_trend": True, "exit_on_crossover": False},
    {"name": "6h 20/50 T200 trail 20% BT noX",  "timeframe": "6h", "short_window": 20, "long_window": 50, "stop_loss_pct": 0.20, "take_profit_pct": 0, "trailing_stop_pct": 0.20, "trend_window": 200, "buy_while_trend": True, "exit_on_crossover": False},
    {"name": "1h 20/50 T200 trail 10% BT noX",  "timeframe": "1h", "short_window": 20, "long_window": 50, "stop_loss_pct": 0.10, "take_profit_pct": 0, "trailing_stop_pct": 0.10, "trend_window": 200, "buy_while_trend": True, "exit_on_crossover": False},

    # --- 1d (bougies journalières) : seulement dans le backtest continu, 200 jours de préchauffage ---
    # Croisements "classiques" : achat au croisement haussier, vente au croisement baissier, rien d'autre
    {"name": "1d 50/200 classique",         "timeframe": "1d", "short_window": 50, "long_window": 200, "stop_loss_pct": NO_STOP, "take_profit_pct": 0},
    {"name": "1d 20/50 classique",          "timeframe": "1d", "short_window": 20, "long_window": 50,  "stop_loss_pct": NO_STOP, "take_profit_pct": 0},
    {"name": "1d 20/50 BT",                 "timeframe": "1d", "short_window": 20, "long_window": 50,  "stop_loss_pct": NO_STOP, "take_profit_pct": 0, "buy_while_trend": True},
    {"name": "1d 20/50 trail 15% BT noX",   "timeframe": "1d", "short_window": 20, "long_window": 50,  "stop_loss_pct": 0.15, "take_profit_pct": 0, "trailing_stop_pct": 0.15, "buy_while_trend": True, "exit_on_crossover": False},
    {"name": "1d 20/50 T200 trail 15% BT noX", "timeframe": "1d", "short_window": 20, "long_window": 50, "stop_loss_pct": 0.15, "take_profit_pct": 0, "trailing_stop_pct": 0.15, "trend_window": 200, "buy_while_trend": True, "exit_on_crossover": False},
    {"name": "1d 20/50 trail 25% BT noX",   "timeframe": "1d", "short_window": 20, "long_window": 50,  "stop_loss_pct": 0.25, "take_profit_pct": 0, "trailing_stop_pct": 0.25, "buy_while_trend": True, "exit_on_crossover": False},
]


def build_strategy(cfg: dict) -> MovingAverageCrossoverStrategy:
    return MovingAverageCrossoverStrategy(
        symbol="BTC/EUR",
        timeframe=cfg["timeframe"],
        short_window=cfg["short_window"],
        long_window=cfg["long_window"],
        stop_loss_pct=cfg["stop_loss_pct"],
        take_profit_pct=cfg["take_profit_pct"],
        trend_window=cfg.get("trend_window", 0),
        trailing_stop_pct=cfg.get("trailing_stop_pct", 0),
        buy_while_trend=cfg.get("buy_while_trend", False),
        exit_on_crossover=cfg.get("exit_on_crossover", True),
    )


@pytest.mark.asyncio
async def test_moving_avg_param_sweep():
    # Par année (1h et 6h), puis un backtest continu sur toute la période (tous les timeframes, dont 1d)
    results = await run_sweep(STRATEGY_CONFIGS, build_strategy)
    print_results(results)
    print_full_period(await run_full_period(STRATEGY_CONFIGS, build_strategy))

    assert results, "No results — download candles into tests/backtests/coinbase/data/, see scripts/download_coinbase_candles.py"
