"""
Exchange-agnostic backtest engine: replay candles through a strategy and compute P&L.
Exchange-specific parts (CSV format, data folder, fee rate) live in binance/ and coinbase/.
"""
from datetime import datetime

import pandas as pd
from app.infrastructure.adapters.historical_exchange import HistoricalExchange
from app.models.order import Order


async def run_backtest(candles: pd.DataFrame, strategy, capital: float = 1000.0) -> list[Order]:
    """
    Replay candles through the strategy using HistoricalExchange.
    Returns the list of Order signals generated.
    If the backtest ends with an open position, it is closed at the last candle price.
    """
    exchange = HistoricalExchange(candles)
    orders = []

    while exchange.tick():
        signal = await strategy.generate_signals(exchange, capital=capital)
        if signal:
            orders.append(signal)

    # Close any open position at the final candle price so it is included in P&L
    buys = [o for o in orders if o.side == "BUY"]
    sells = [o for o in orders if o.side == "SELL"]
    if len(buys) > len(sells):
        last_price = float(candles.iloc[-1]["close"])
        orders.append(Order(
            bot_id="",
            symbol=buys[-1].symbol,
            side="SELL",
            amount=buys[-1].amount,
            price=last_price,
            created_at=datetime.now(),
        ))

    return orders


def compute_pnl(orders, fee_rate: float):
    """
    Compute P&L by pairing each BUY with the next SELL, net of fees.
    Fees are paid on both sides: fee_rate × price × amount on the BUY and on the SELL.
    Returns (net_pnl, fees, completed_trades).
    """
    gross_pnl = 0.0
    fees = 0.0
    completed_trades = 0
    buys = [o for o in orders if o.side == "BUY"]
    sells = [o for o in orders if o.side == "SELL"]

    for buy, sell in zip(buys, sells):
        amount = float(buy.amount)
        gross_pnl += (float(sell.price) - float(buy.price)) * amount
        fees += (float(buy.price) + float(sell.price)) * amount * fee_rate
        completed_trades += 1

    return gross_pnl - fees, fees, completed_trades


def assert_alternating_sides(orders):
    """The strategy must never open a second position while one is already open."""
    for i in range(len(orders) - 1):
        assert orders[i].side != orders[i + 1].side, (
            f"Two consecutive {orders[i].side} orders at index {i} — position tracking broken"
        )
