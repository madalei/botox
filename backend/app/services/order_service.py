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

        repo = OrderRepository()  # creates its own session internally
        repo.create_order(order)
        repo.close()

        # Execute on exchange (optional)
        # if self.binance_service:
        #     try:
        #         await self.binance_service.execute_order(order)
        #         order.status = "EXECUTED"
        #     except Exception as e:
        #         order.status = "FAILED"
        #         logger.error(f"Execution failed: {e}")
        #
        #     order.updated_at = datetime.utcnow()
        #     self.db.commit()

        return order
