import asyncio
from typing import Dict
from app.bots.base import BaseBot, BotStatus
from app.bots.bot_factory import build_bot_from_orm
from app.infrastructure.adapters.database import SessionLocal
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
        bot.save_state = self._save_state
        bot_logger.info("Bot registered", extra={"bot_id": bot.bot_id})

    @staticmethod
    def _save_state(bot_id: str, state: dict):
        with SessionLocal() as db:
            BotRepository(db).update_state(bot_id, state)

    async def start_bot(self, bot_id: str):
        bot = self._get_bot(bot_id)
        bot.status = BotStatus.RUNNING
        bot._task = asyncio.create_task(bot.run(self.exchange, self.order_service))


    async def stop_bot(self, bot_id: str):
        """
        Arrête un bot et le marque "S" en base : il ne sera plus relancé au démarrage du serveur.
        Une position ouverte n'est pas vendue : les BTC restent sur le compte.
        """
        bot = self._bots.pop(bot_id, None)
        if bot:
            bot.status = BotStatus.STOPPED
            if bot._task:
                bot._task.cancel()
        with SessionLocal() as db:
            repository = BotRepository(db)
            repository.get_bot_by_id(bot_id)  # ValueError si le bot n'existe pas
            repository.update_status(bot_id, "S")
        bot_logger.info("Bot stopped", extra={"bot_id": bot_id})

    async def restart_db_bot(self, bot_id: str):

        # Todo Check if bot is already running (but already check by register_bot)

        with SessionLocal() as db: # the session is always closed when the with block exits
            repository = BotRepository(db)
            bot = repository.get_bot_by_id(bot_id)
            # Build a BaseBot instance from the DB model (with its saved position)
            base_bot = build_bot_from_orm(bot)
            # Statut "R" et état sauvegardé : le bot sera relancé automatiquement au prochain démarrage du serveur
            repository.update_status(bot_id, "R")
            repository.update_state(bot_id, base_bot.strategy.get_state())
        # Register and Start it
        self.register_bot(base_bot)
        await self.start_bot(base_bot.bot_id)

    async def restore_bots(self):
        """
        Au démarrage du serveur (ex. après une mise à jour Docker) : relance les bots en cours avec leur position.
        Un bot qui ne se recharge pas (stratégie inconnue...) est logué et ignoré, sans bloquer les autres.
        """
        with SessionLocal() as db:
            db_bots = BotRepository(db).get_bots_to_restore()
            base_bots = []
            for db_bot in db_bots:
                try:
                    base_bots.append(build_bot_from_orm(db_bot))
                except Exception as e:
                    bot_logger.error(f"Bot {db_bot.id} not restored: {e}", extra={"bot_id": db_bot.id})

        for base_bot in base_bots:
            self.register_bot(base_bot)
            await self.start_bot(base_bot.bot_id)
            bot_logger.info(
                f"Bot restored after restart | position open={base_bot.strategy.get_state()['is_position_open']}",
                extra={"bot_id": base_bot.bot_id},
            )
        return [base_bot.bot_id for base_bot in base_bots]


    def list_running_bots(self):
        return [
            {
                "bot_id": bot.bot_id,
                "status": bot.status,
                "strategy": bot.strategy.__class__.__name__,
                "params": bot.strategy.model_dump(),  # only public fields
            }
            for bot in self._bots.values()
        ]

    def _get_bot(self, bot_id: str):
        if bot_id not in self._bots:
            raise ValueError(f"Bot {bot_id} not found")
        return self._bots[bot_id]
