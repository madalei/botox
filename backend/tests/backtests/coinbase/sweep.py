"""
Shared parameter sweep runner for Coinbase backtests: run each strategy config on every yearly
dataset of the same timeframe, then print one ranked table per dataset and a summary over all years.

Missing months are skipped; the dataset label shows how many months were loaded.
Download the candles first, e.g.:
    python scripts/download_coinbase_candles.py --symbol BTC/EUR --timeframe 1h --start 2022-01 --end 2026-09
    python scripts/download_coinbase_candles.py --symbol BTC/EUR --timeframe 6h --start 2022-01 --end 2026-09
"""
from collections import defaultdict
from typing import Callable

from tests.backtests.coinbase.market import FEE_RATE, load_year
from tests.backtests.engine import compute_pnl, run_backtest

CURRENCY = "EUR"

# Coinbase has no 4h candles: 6h is the closest slower timeframe
YEARLY_DATASETS = [
    {"symbol": "BTC-EUR", "timeframe": timeframe, "year": year}
    for timeframe in ("1h", "6h")
    for year in (2022, 2023, 2024, 2025, 2026)
]


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

        for cfg in configs:
            if cfg["timeframe"] != ds["timeframe"]:
                continue

            orders = await run_backtest(candles, build_strategy(cfg))
            pnl, fees, completed = compute_pnl(orders, FEE_RATE)

            results.append({
                "timeframe": ds["timeframe"],
                "year":      ds["year"],
                "dataset":   f"{ds['symbol']} {ds['timeframe']} {ds['year']} ({len(loaded_months)}/12 months)",
                "config":    cfg["name"],
                "sl/tp":     f"{cfg['stop_loss_pct']*100:.1f}%/{cfg['take_profit_pct']*100:.1f}%",
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
            print(f"  {'Config':<22} {'SL/TP':<11} {'Trades':>6} {'Fees':>10} {'P&L (net)':>14}")
            print(f"  {'-'*22} {'-'*11} {'-'*6} {'-'*10} {'-'*14}")

        print(
            f"  {r['config']:<22} {r['sl/tp']:<11} {r['completed']:>6} "
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
    print(f"  {'Config':<22} {year_headers} {'Total':>9} {'Fees':>9} {'Trades':>6}")
    for config in sorted(totals, key=lambda c: -totals[c]["pnl"]):
        per_year = " ".join(
            f"{by_config[config][year]:>+9.2f}" if year in by_config[config] else f"{'-':>9}"
            for year in years
        )
        total = totals[config]
        print(f"  {config:<22} {per_year} {total['pnl']:>+9.2f} {total['fees']:>9.2f} {total['trades']:>6}")
