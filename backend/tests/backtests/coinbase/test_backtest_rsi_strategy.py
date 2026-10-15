import pytest
from app.bots.strategies.rsi_strategy import RsiStrategy
from tests.backtests.coinbase.market import DATA_DIR, FEE_RATE, load_candles
from tests.backtests.engine import assert_alternating_sides, compute_pnl, run_backtest


@pytest.mark.asyncio
async def test_backtest_rsi_1h_march_2024():
    filename = "BTC-EUR-1h-2024-03.csv"
    if not (DATA_DIR / filename).exists():
        pytest.skip(f"{filename} missing, see scripts/download_coinbase_candles.py")

    candles = load_candles(filename)
    strategy = RsiStrategy()

    orders = await run_backtest(candles, strategy)
    buys = [o for o in orders if o.side == "BUY"]
    sells = [o for o in orders if o.side == "SELL"]
    pnl, fees, _ = compute_pnl(orders, FEE_RATE)

    print(f"\n=== RSI Backtest: Coinbase BTC-EUR 1h — March 2024 ===")
    print(f"Signals   : {len(orders)} total ({len(buys)} BUY, {len(sells)} SELL)")
    print(f"Fees      : {fees:.2f} EUR")
    print(f"P&L (net) : {pnl:+.2f} EUR")

    assert_alternating_sides(orders)
