import pytest
from app.bots.strategies.moving_average_crossover import MovingAverageCrossoverStrategy
from tests.backtests.binance.market import FEE_RATE, load_candles
from tests.backtests.engine import assert_alternating_sides, compute_pnl, run_backtest


@pytest.mark.asyncio
async def test_backtest_1h_march_2024():
    candles = load_candles("BTCUSDT-1h-2024-03.csv")
    strategy = MovingAverageCrossoverStrategy()

    orders = await run_backtest(candles, strategy)
    buys = [o for o in orders if o.side == "BUY"]
    sells = [o for o in orders if o.side == "SELL"]
    pnl, fees, completed_trades = compute_pnl(orders, FEE_RATE)

    print(f"\n=== Backtest: BTCUSDT 1h — March 2024 ===")
    print(f"Signals   : {len(orders)} total ({len(buys)} BUY, {len(sells)} SELL)")
    print(f"Completed : {completed_trades} round trips")
    print(f"Fees      : {fees:.2f} USDT")
    print(f"P&L (net) : {pnl:+.2f} USDT")

    assert len(buys) > 0, "Expected at least one BUY signal"
    assert_alternating_sides(orders)
    # Every BUY should have a stop_loss and take_profit set
    for order in buys:
        assert order.stop_loss is not None and order.stop_loss > 0
        assert order.take_profit is not None and order.take_profit > order.price


@pytest.mark.asyncio
async def test_backtest_1h_october_2025():
    candles = load_candles("BTCUSDT-1h-2025-10.csv")
    strategy = MovingAverageCrossoverStrategy()

    orders = await run_backtest(candles, strategy)
    buys = [o for o in orders if o.side == "BUY"]
    sells = [o for o in orders if o.side == "SELL"]
    pnl, fees, completed_trades = compute_pnl(orders, FEE_RATE)

    print(f"\n=== Backtest: BTCUSDT 1h — October 2025 ===")
    print(f"Signals   : {len(orders)} total ({len(buys)} BUY, {len(sells)} SELL)")
    print(f"Completed : {completed_trades} round trips")
    print(f"Fees      : {fees:.2f} USDT")
    print(f"P&L (net) : {pnl:+.2f} USDT")

    assert len(buys) > 0
    assert_alternating_sides(orders)


@pytest.mark.asyncio
async def test_backtest_4h_september_2025():
    candles = load_candles("BTCUSDT-4h-2025-09.csv")
    # 4h candles — use a tighter window to get enough signals in one month
    strategy = MovingAverageCrossoverStrategy(timeframe="4h", short_window=9, long_window=21)

    orders = await run_backtest(candles, strategy)
    buys = [o for o in orders if o.side == "BUY"]
    sells = [o for o in orders if o.side == "SELL"]
    pnl, fees, completed_trades = compute_pnl(orders, FEE_RATE)

    print(f"\n=== Backtest: BTCUSDT 4h — September 2025 ===")
    print(f"Signals   : {len(orders)} total ({len(buys)} BUY, {len(sells)} SELL)")
    print(f"Completed : {completed_trades} round trips")
    print(f"Fees      : {fees:.2f} USDT")
    print(f"P&L (net) : {pnl:+.2f} USDT")

    assert_alternating_sides(orders)


@pytest.mark.asyncio
async def test_backtest_4h_december_2025():
    candles = load_candles("BTCUSDT-4h-2025-12.csv")
    strategy = MovingAverageCrossoverStrategy(timeframe="4h", short_window=9, long_window=21)

    orders = await run_backtest(candles, strategy)
    buys = [o for o in orders if o.side == "BUY"]
    sells = [o for o in orders if o.side == "SELL"]
    pnl, fees, completed_trades = compute_pnl(orders, FEE_RATE)

    print(f"\n=== Backtest: BTCUSDT 4h — December 2025 ===")
    print(f"Signals   : {len(orders)} total ({len(buys)} BUY, {len(sells)} SELL)")
    print(f"Completed : {completed_trades} round trips")
    print(f"Fees      : {fees:.2f} USDT")
    print(f"P&L (net) : {pnl:+.2f} USDT")

    assert_alternating_sides(orders)


@pytest.mark.asyncio
async def test_backtest_1h_february_2026():
    candles = load_candles("BTCUSDT-1h-2026-02.csv")
    strategy = MovingAverageCrossoverStrategy()

    orders = await run_backtest(candles, strategy)
    buys = [o for o in orders if o.side == "BUY"]
    sells = [o for o in orders if o.side == "SELL"]
    pnl, fees, completed_trades = compute_pnl(orders, FEE_RATE)

    print(f"\n=== Backtest: BTCUSDT 1h — February 2026 ===")
    print(f"Signals   : {len(orders)} total ({len(buys)} BUY, {len(sells)} SELL)")
    print(f"Completed : {completed_trades} round trips")
    print(f"Fees      : {fees:.2f} USDT")
    print(f"P&L (net) : {pnl:+.2f} USDT")

    assert len(buys) > 0
    assert_alternating_sides(orders)

