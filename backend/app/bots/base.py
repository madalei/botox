from app.services.logging import bot_logger
from enum import Enum
import asyncio

class BotStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"

class BaseBot:
    def __init__(self, bot_id: str, strategy, capital: float = 1000.0, check_interval: int = 900):
        self.bot_id = bot_id
        self.strategy = strategy
        self.capital = capital
        # Todo here maybe some other customisable params
        self.check_interval = check_interval  # seconds
        self.status = BotStatus.CREATED
        self._task: asyncio.Task | None = None

    async def run(self, exchange, order_service=None):
        """
        Internal loop: run the strategy each "check_interval" times and execute trades if signals appear.
        By default, checks every 15 minutes (900 seconds).
        """
        bot_logger.info("Bot started", extra={"bot_id": self.bot_id})
        while self.status == BotStatus.RUNNING:
            try:
                # Generate signal/order from strategy
                order = await self.strategy.generate_signals(exchange, self.capital)

                if order:
                    bot_logger.info(
                        f"Signal detected: {order.side} {order.amount} {order.symbol} at {order.price}",
                        extra={"bot_id": self.bot_id}
                    )

                    # Persist trade to DB if order_service is provided
                    order_service.create_order(order)

                    # Todo
                    # Call Binance API (pseudo)
                    # await binance_service.execute_order(order)
                else:
                    bot_logger.info(f"No signal generated", extra={"bot_id": self.bot_id})

                await asyncio.sleep(self.check_interval)

            except Exception as e:
                bot_logger.error(f"Error in bot loop: {e}", extra={"bot_id": self.bot_id})
                await asyncio.sleep(self.check_interval)

        bot_logger.info(f"Bot {self.bot_id} stopped", extra={"bot_id": self.bot_id})

    # async def start(self, exchange, order_service=None):
    #     self.status = BotStatus.RUNNING
    #     self._task = asyncio.create_task(self.run(exchange, order_service))

    async def stop(self):
        self.status = BotStatus.STOPPED
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                bot_logger.info("Bot stopped", extra={"bot_id": self.bot_id})

    def get_strategy_params(self):
        pass