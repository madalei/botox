import asyncio
from typing import Dict
from app.bots.base import BaseBot, BotStatus
from app.repositories.bot_repository import BotRepository
from app.services.logging import bot_logger

class BotManager:
    """
    Manages multiple BaseBot instances.
    """

    def __init__(self, exchange, order_service):
        self.exchange = exchange
        self.order_service = order_service
        self._bots: Dict[str, BaseBot] = {}

    def register_bot(self, bot: BaseBot):
        if bot.bot_id in self._bots:
            raise ValueError(f"Bot {bot.bot_id} already registered")
        self._bots[bot.bot_id] = bot
        bot_logger.info("Bot registered", extra={"bot_id": bot.bot_id})

    async def start_bot(self, bot_id: str):
        bot = self._get_bot(bot_id)
        bot.status = BotStatus.RUNNING
        bot._task = asyncio.create_task(bot.run(self.exchange, self.order_service))


    # async def stop_bot(self, bot_id: str):
    #     bot = self._get_bot(bot_id)
    #     await bot.stop()

    # async def restart_bot(self, bot_id: str):
    #     bot = self._get_bot(bot_id)
    #     await bot.stop()
    #     await asyncio.sleep(1)
    #     await bot.start(self.exchange, self.order_service)
    #
    # def list_bots(self):
    #     return [
    #         {
    #             "bot_id": bot.bot_id,
    #             "status": bot.status,
    #             "strategy": bot.strategy.__class__.__name__,
    #         }
    #         for bot in self._bots.values()
    #     ]
    #
    def _get_bot(self, bot_id: str):
        if bot_id not in self._bots:
            raise ValueError(f"Bot {bot_id} not found")
        return self._bots[bot_id]
