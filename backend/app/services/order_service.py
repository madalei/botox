from datetime import datetime
from sqlalchemy.orm import Session

from app.infrastructure.adapters.binance_adapter import BinanceAdapter
from app.models.order import Order
from app.repositories.order_repository import OrderRepository
from app.services.logging import bot_logger


class OrderService:
    """
    Handles order execution.
    """

    def __init__(self, exchange: BinanceAdapter = None):
        self.repository = OrderRepository() # creates its own session internally
        self.exchange = exchange  # Can be None if no exchange configured

    async def create_order(self, order: Order) -> Order:
        """
        Persist order to DB and execute it if a broker is configured.
        """

        bot_logger.info(
            f"Creating order {order.side} {order.amount} {order.symbol}",
            extra={"symbol": order.symbol}
        )

        self.repository.create_order(order)
        self.repository.close()

        # Move this to a separate method
        # Execute on exchange (optional)
        if self.exchange:
            try:
                if order.side == "BUY":
                    await self.exchange.place_market_buy(order.symbol, order.amount)
                elif order.side == "SELL":
                    await self.exchange.place_market_sell(order.symbol, order.amount)
                # order.status = "EXECUTED"
            except Exception as e:
                # order.status = "FAILED"
                bot_logger.error(f"Binance Order Execution failed: {e}")

            self.repository.update_order(
                id=order.id,
                updates={
                    "status": "EXECUTED",
                    "executed_at": datetime.now()
                }
            )

        return order
