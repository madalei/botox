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

    def __init__(self, exchange: BinanceAdapter = None, repository: OrderRepository | None = None):
        self.repository = repository or OrderRepository() # creates its own session internally
        self.exchange = exchange  # Can be None if no exchange configured


    async def create_order(self, order: Order) -> Order:
        """Create and persist order to DB"""
        bot_logger.info(f"Creating order {order.side} {order.amount} {order.symbol}")

        db_order = self.repository.create_order(order)
        self.repository.close()
        return db_order

    async def execute_order(self, order_id) -> Order:
        """
        Execute an order if a broker is configured.
        """

        order = self.repository.get_order_by_id(order_id)

        bot_logger.info(f"Executing order {order.side} {order.amount} {order.symbol}")

        if self.exchange:
            status = "EXECUTED"
            try:
                if order.side == "BUY":
                    exchange_order = await self.exchange.place_market_buy(order.symbol, order.amount)
                elif order.side == "SELL":
                    exchange_order = await self.exchange.place_market_sell(order.symbol, order.amount)
            except Exception as e:
                status = "FAILED"
                bot_logger.error(f"Binance Order Execution failed: {e}")

            updated_order = self.repository.update_order(
                id=order.id,
                updates={
                    "status": status,
                    "executed_at": datetime.now()
                    # "external_order_id": exchange_order.get("id")
                }
            )

        self.repository.close()

        return updated_order
