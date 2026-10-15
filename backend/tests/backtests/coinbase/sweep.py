"""
Shared parameter sweep runner for Coinbase backtests: run each strategy config on every yearly
dataset of the same timeframe, then print one ranked table per dataset and a summary over all years.

run_full_period / print_full_period : un seul backtest continu sur toute la période (pas de remise à zéro
du préchauffage des MA chaque 1er janvier, pas de vente forcée au 31 décembre), avec le rendement en %
en investissant tout le capital, pour plusieurs niveaux de frais (= plusieurs plateformes), comparé au buy & hold.

Missing months are skipped; the dataset label shows how many months were loaded.
Download the candles first, e.g.:
    python scripts/download_coinbase_candles.py --symbol BTC/EUR --timeframe 1h --start 2022-01 --end 2026-09
    python scripts/download_coinbase_candles.py --symbol BTC/EUR --timeframe 6h --start 2022-01 --end 2026-09
    python scripts/download_coinbase_candles.py --symbol BTC/EUR --timeframe 1d --start 2022-01 --end 2026-09
"""
from collections import defaultdict
from typing import Callable

import pandas as pd

from tests.backtests.coinbase.market import FEE_RATE, load_year
from tests.backtests.engine import compounded_return_pct, compute_pnl, run_backtest

CURRENCY = "EUR"

# Coinbase has no 4h candles: 6h is the closest slower timeframe
YEARLY_DATASETS = [
    {"symbol": "BTC-EUR", "timeframe": timeframe, "year": year}
    for timeframe in ("1h", "6h")
    for year in (2022, 2023, 2024, 2025, 2026)
]


YEARS = (2022, 2023, 2024, 2025, 2026)

# Frais par côté (achat et vente) pour simuler d'autres plateformes ou types d'ordre.
# Ordres de grandeur du premier palier de volume, à vérifier sur les grilles officielles avant de choisir.
FEE_SCENARIOS = [
    (0.0060, "Coinbase Advanced, ordre au marché (taker)"),
    (0.0040, "Coinbase Advanced, ordre limite (maker) / Kraken Pro taker"),
    (0.0025, "Bitvavo taker (approx.)"),
    (0.0010, "OKX taker (approx.)"),
    (0.0, "Sans frais (potentiel brut de la stratégie)"),
]


def exit_rule(cfg: dict) -> str:
    """Règle de sortie lisible : "2.0%/4.0%" (stop loss / take profit) ou "trail 8.0%" (stop suiveur sans take profit)."""
    if cfg["stop_loss_pct"] >= 0.99 and not cfg["take_profit_pct"]:
        return "croisement"  # ni stop ni take profit : sortie uniquement au croisement baissier
    if cfg.get("trailing_stop_pct") and not cfg["take_profit_pct"]:
        return f"trail {cfg['trailing_stop_pct']*100:.1f}%"
    return f"{cfg['stop_loss_pct']*100:.1f}%/{cfg['take_profit_pct']*100:.1f}%"


async def run_sweep(configs: list[dict], build_strategy: Callable[[dict], object]) -> list[dict]:
    """
    Run every config on the datasets of its timeframe.
    build_strategy(cfg) returns the strategy instance for a config.
    """
    results = []

    for ds in YEARLY_DATASETS:
        candles, loaded_months = load_year(ds["symbol"], ds["timeframe"], ds["year"])
        if candles.empty:
            continue
        # Benchmark: buy at the first candle, sell at the last one
        hold_pct = (float(candles.iloc[-1]["close"]) / float(candles.iloc[0]["open"]) - 1) * 100

        for cfg in configs:
            if cfg["timeframe"] != ds["timeframe"]:
                continue

            orders = await run_backtest(candles, build_strategy(cfg))
            pnl, fees, completed = compute_pnl(orders, FEE_RATE)

            results.append({
                "timeframe": ds["timeframe"],
                "year":      ds["year"],
                "dataset":   f"{ds['symbol']} {ds['timeframe']} {ds['year']} ({len(loaded_months)}/12 months)"
                             f" — buy & hold {hold_pct:+.1f}%",
                "hold_pct":  hold_pct,
                "config":    cfg["name"],
                "sl/tp":     exit_rule(cfg),
                "completed": completed,
                "fees":      fees,
                "pnl":       pnl,
            })

    return results


def print_results(results: list[dict]):
    """One table per dataset sorted by net P&L, then a summary of every config over all years."""
    print()
    current_dataset = None
    for r in sorted(results, key=lambda x: (x["timeframe"], x["year"], -x["pnl"])):
        if r["dataset"] != current_dataset:
            current_dataset = r["dataset"]
            print(f"\n{'='*72}")
            print(f"  {current_dataset}")
            print(f"{'='*72}")
            print(f"  {'Config':<30} {'Exit':<11} {'Trades':>6} {'Fees':>10} {'P&L (net)':>14}")
            print(f"  {'-'*30} {'-'*11} {'-'*6} {'-'*10} {'-'*14}")

        print(
            f"  {r['config']:<30} {r['sl/tp']:<11} {r['completed']:>6} "
            f"{r['fees']:>10.2f} {r['pnl']:>+10.2f} {CURRENCY}"
        )

    # Summary: net P&L per year and total, best config first
    years = sorted({r["year"] for r in results})
    by_config = defaultdict(dict)
    totals = defaultdict(lambda: {"pnl": 0.0, "fees": 0.0, "trades": 0})
    for r in results:
        by_config[r["config"]][r["year"]] = r["pnl"]
        totals[r["config"]]["pnl"] += r["pnl"]
        totals[r["config"]]["fees"] += r["fees"]
        totals[r["config"]]["trades"] += r["completed"]

    print(f"\n{'='*72}")
    print(f"  Summary — net P&L in {CURRENCY} after {FEE_RATE*100:.2f}% fee per side")
    print(f"{'='*72}")
    year_headers = " ".join(f"{year:>9}" for year in years)
    print(f"  {'Config':<30} {year_headers} {'Total':>9} {'Fees':>9} {'Trades':>6}")
    for config in sorted(totals, key=lambda c: -totals[c]["pnl"]):
        per_year = " ".join(
            f"{by_config[config][year]:>+9.2f}" if year in by_config[config] else f"{'-':>9}"
            for year in years
        )
        total = totals[config]
        print(f"  {config:<30} {per_year} {total['pnl']:>+9.2f} {total['fees']:>9.2f} {total['trades']:>6}")

    hold_by_year = {r["year"]: r["hold_pct"] for r in results}
    hold = " ".join(f"{hold_by_year[year]:>+8.1f}%" for year in years)
    print(f"  {'BTC buy & hold':<30} {hold}")


async def run_full_period(configs: list[dict], build_strategy: Callable[[dict], object]) -> list[dict]:
    """
    Un seul backtest continu par config, sur toutes les années disponibles de son timeframe.
    Le rendement est calculé pour chaque niveau de frais de FEE_SCENARIOS.
    """
    candles_by_timeframe = {}
    for timeframe in sorted({cfg["timeframe"] for cfg in configs}):
        frames = [load_year("BTC-EUR", timeframe, year)[0] for year in YEARS]
        frames = [frame for frame in frames if not frame.empty]
        if frames:
            candles_by_timeframe[timeframe] = pd.concat(frames, ignore_index=True)

    results = []
    for cfg in configs:
        candles = candles_by_timeframe.get(cfg["timeframe"])
        if candles is None:
            continue
        orders = await run_backtest(candles, build_strategy(cfg))
        _, _, completed = compute_pnl(orders, FEE_RATE)
        results.append({
            "config":  cfg["name"],
            "exit":    exit_rule(cfg),
            "trades":  completed,
            "returns": [compounded_return_pct(orders, fee_rate) for fee_rate, _ in FEE_SCENARIOS],
            # Buy & hold sur exactement les mêmes bougies
            "hold_pct": (float(candles.iloc[-1]["close"]) / float(candles.iloc[0]["open"]) - 1) * 100,
            "period":  f"{pd.to_datetime(candles.iloc[0]['timestamp'], unit='ms'):%Y-%m} → "
                       f"{pd.to_datetime(candles.iloc[-1]['timestamp'], unit='ms'):%Y-%m}",
        })
    return results


def print_full_period(results: list[dict]):
    """Classement par rendement avec les frais Coinbase actuels, une colonne par niveau de frais."""
    if not results:
        return
    print(f"\n{'='*100}")
    print(f"  Période complète {results[0]['period']} — un seul backtest continu, tout le capital investi à chaque trade")
    print(f"  Rendement en % selon les frais par côté (achat et vente) :")
    for fee_rate, label in FEE_SCENARIOS:
        print(f"    {fee_rate*100:.2f}% = {label}")
    print(f"{'='*100}")
    fee_headers = " ".join(f"{f'{fee_rate*100:.2f}%':>9}" for fee_rate, _ in FEE_SCENARIOS)
    print(f"  {'Config':<30} {'Exit':<11} {'Trades':>6} {fee_headers} {'Buy&hold':>9}")
    for r in sorted(results, key=lambda x: -x["returns"][0]):
        returns = " ".join(f"{value:>+8.1f}%" for value in r["returns"])
        print(f"  {r['config']:<30} {r['exit']:<11} {r['trades']:>6} {returns} {r['hold_pct']:>+8.1f}%")
