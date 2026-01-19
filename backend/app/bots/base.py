from app.services.logging import logger
from app.bots.strategies.base import BaseStrategy
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
        self.check_interval = check_interval  # seconds
        self.status = BotStatus.CREATED
        self._task: asyncio.Task | None = None

    async def run(self):
          """
          Internal loop: run the strategy and execute trades if signals appear.
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
                    if order_service:
                        await order_service.create_order(order)

                    # Call Binance API (pseudo)
                    # await binance_service.execute_order(order)
                else:
                    bot_logger.info(f"No signal generated", extra={"bot_id": self.bot_id})

                await asyncio.sleep(self.check_interval)

            except asyncio.CancelledError:
                logger.info(f"Bot {self.bot_id} task cancelled", extra={"bot_id": self.bot_id})
                break
            except Exception as e:
                bot_logger.error(f"Error in bot loop: {e}", extra={"bot_id": self.bot_id})
                await asyncio.sleep(self.check_interval)

        bot_logger.info(f"Bot {self.bot_id} stopped", extra={"bot_id": self.bot_id})

    async def start(self):
        self.status = BotStatus.RUNNING
        self._task = asyncio.create_task(self.run())

    async def stop(self):
        self.status = BotStatus.STOPPED
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                logger.info("Bot stopped", extra={"bot_id": self.bot_id})