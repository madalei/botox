# tests/factories/order_factory.py
from datetime import datetime
from app.models.order import Order


def build_order(
    side="BUY",
    symbol="BTC/USDT",
    bot_id="test_bot_default",
    amount=0.5,
    price=30_000,
    stop_loss=None,
    take_profit=None,
):
    return Order(
        id=None,
        bot_id=bot_id,
        symbol=symbol,
        side=side,
        amount=amount,
        price=price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        created_at=datetime.now()
    )
