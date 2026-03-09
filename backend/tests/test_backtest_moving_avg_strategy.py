from pathlib import Path

import pandas as pd
import pytest
from app.bots.strategies.moving_average_crossover import MovingAverageCrossoverStrategy
from app.infrastructure.adapters.historical_exchange import HistoricalExchange

# Binance monthly klines CSVs have no header row — these are the standard column names
BINANCE_KLINE_COLUMNS = [
    "timestamp", "open", "high", "low", "close", "volume",
    "close_time", "quote_volume", "trades", "taker_base", "taker_quote", "ignore",
]


def load_candles(filename: str) -> pd.DataFrame:
    path = Path(__file__).parent / "data" / filename
    return pd.read_csv(path, names=BINANCE_KLINE_COLUMNS)


async def run_backtest(candles: pd.DataFrame, strategy: MovingAverageCrossoverStrategy, capital: float = 1000.0):
    """
    Replay candles through the strategy using HistoricalExchange.
    Returns the list of Order signals generated.
    """
    exchange = HistoricalExchange(candles)
    orders = []

    while exchange.tick():
        signal = await strategy.generate_signals(exchange, capital=capital)
        if signal:
            orders.append(signal)

    return orders


def compute_pnl(orders):
    """
    Compute P&L by pairing each BUY with the next SELL.
    Returns the net gain or loss (pnl, completed_trades).
    """
    pnl = 0.0
    completed_trades = 0
    buys = [o for o in orders if o.side == "BUY"]
    sells = [o for o in orders if o.side == "SELL"]

    for buy, sell in zip(buys, sells):
        pnl += (float(sell.price) - float(buy.price)) * float(buy.amount)
        completed_trades += 1

    return pnl, completed_trades


@pytest.mark.asyncio
async def test_backtest_1h_march_2024():
    candles = load_candles("BTCUSDT-1h-2024-03.csv")
    strategy = MovingAverageCrossoverStrategy()

    orders = await run_backtest(candles, strategy)
    buys = [o for o in orders if o.side == "BUY"]
    sells = [o for o in orders if o.side == "SELL"]
    pnl, completed_trades = compute_pnl(orders)

    print(f"\n=== Backtest: BTCUSDT 1h — March 2024 ===")
    print(f"Signals   : {len(orders)} total ({len(buys)} BUY, {len(sells)} SELL)")
    print(f"Completed : {completed_trades} round trips")
    print(f"P&L       : {pnl:+.2f} USDT")

    assert len(buys) > 0, "Expected at least one BUY signal"
    # Strategy should never open a second position while one is already open
    for i in range(len(orders) - 1):
        assert orders[i].side != orders[i + 1].side, (
            f"Two consecutive {orders[i].side} orders at index {i} — position tracking broken"
        )
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
    pnl, completed_trades = compute_pnl(orders)

    print(f"\n=== Backtest: BTCUSDT 1h — October 2025 ===")
    print(f"Signals   : {len(orders)} total ({len(buys)} BUY, {len(sells)} SELL)")
    print(f"Completed : {completed_trades} round trips")
    print(f"P&L       : {pnl:+.2f} USDT")

    assert len(buys) > 0
    for i in range(len(orders) - 1):
        assert orders[i].side != orders[i + 1].side


@pytest.mark.asyncio
async def test_backtest_4h_september_2025():
    candles = load_candles("BTCUSDT-4h-2025-09.csv")
    # 4h candles — use a tighter window to get enough signals in one month
    strategy = MovingAverageCrossoverStrategy(timeframe="4h", short_window=9, long_window=21)

    orders = await run_backtest(candles, strategy)
    buys = [o for o in orders if o.side == "BUY"]
    sells = [o for o in orders if o.side == "SELL"]
    pnl, completed_trades = compute_pnl(orders)

    print(f"\n=== Backtest: BTCUSDT 4h — September 2025 ===")
    print(f"Signals   : {len(orders)} total ({len(buys)} BUY, {len(sells)} SELL)")
    print(f"Completed : {completed_trades} round trips")
    print(f"P&L       : {pnl:+.2f} USDT")

    for i in range(len(orders) - 1):
        assert orders[i].side != orders[i + 1].side
