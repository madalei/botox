# tests/factories/order_factory.py
from datetime import datetime
from app.models.order import Order


def build_order(
    side="BUY",
    symbol="BTC/USDT",
    amount=0.5,
    price=30_000,
    stop_loss=None,
    take_profit=None,
):
    return Order(
        id=None,
        symbol=symbol,
        side=side,
        amount=amount,
        price=price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
