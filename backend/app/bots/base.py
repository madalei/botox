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
    def __init__(self, bot_id: str, strategy: BaseStrategy):
        self.bot_id = bot_id
        self.strategy = strategy

        self.status = BotStatus.CREATED
        self._task: asyncio.Task | None = None

    async def run(self):
        # Example tick
        logger.info("Bot started", extra={"bot_id": self.bot_id})
        while self.status == BotStatus.RUNNING:
            logger.info("Bot tick", extra={"bot_id": self.bot_id})
            await asyncio.sleep(2)

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