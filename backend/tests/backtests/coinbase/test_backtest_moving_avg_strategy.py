import pytest
from app.bots.strategies.moving_average_crossover import MovingAverageCrossoverStrategy
from tests.backtests.coinbase.market import FEE_RATE, load_year
from tests.backtests.engine import assert_alternating_sides, compute_pnl, run_backtest


@pytest.mark.asyncio
async def test_backtest_1h_2024():
    candles, months = load_year("BTC-EUR", "1h", 2024)
    if not months:
        pytest.skip("No BTC-EUR 1h 2024 candles, see scripts/download_coinbase_candles.py")

    strategy = MovingAverageCrossoverStrategy(symbol="BTC/EUR", timeframe="1h")

    orders = await run_backtest(candles, strategy)
    buys = [o for o in orders if o.side == "BUY"]
    sells = [o for o in orders if o.side == "SELL"]
    pnl, fees, completed_trades = compute_pnl(orders, FEE_RATE)

    print(f"\n=== Backtest: Coinbase BTC-EUR 1h — 2024 ({len(months)} months) ===")
    print(f"Signals   : {len(orders)} total ({len(buys)} BUY, {len(sells)} SELL)")
    print(f"Completed : {completed_trades} round trips")
    print(f"Fees      : {fees:.2f} EUR")
    print(f"P&L (net) : {pnl:+.2f} EUR")

    assert len(buys) > 0
    assert_alternating_sides(orders)
