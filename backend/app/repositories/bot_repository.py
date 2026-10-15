from sqlalchemy.orm import Session
from app.models.bot import Bot
from app.infrastructure.adapters.database import SessionLocal


class BotRepository:
    """
    Implémentation du repository utilisant SQLAlchemy.
    """

    def __init__(self, db: Session = None):
        # /!\ Using db None -> all instance using sessionLocal must be manually closed
        self.db = db or SessionLocal()

    def create_bot(self, bot):
        db_bot = Bot(
            id=bot.bot_id,
            strategy=bot.strategy.name,
            # check_interval est un paramètre du bot, pas de la stratégie : on le garde dans params pour le redémarrage
            params={**bot.strategy.model_dump(), "check_interval": bot.check_interval},
            status="R",
            state=bot.strategy.get_state(),
        )
        self.db.add(db_bot)
        self.db.commit()
        self.db.refresh(db_bot)
        return db_bot

    def get_all_bots(self):
        return self.db.query(Bot).all()


    def get_bot_by_id(self, bot_id: str) -> type[Bot]:
        """Retrieve a bot by its ID.
        :param bot_id: The string ID of the bot
        :return: a Bot object
        :raises ValueError: If bot not found."""

        bot = self.db.query(Bot).filter(Bot.id == bot_id).first()
        if not bot:
            raise ValueError(f"Bot {bot_id} not found")
        return bot


    def get_bots_to_restore(self) -> list[Bot]:
        """
        Bots à relancer au démarrage du serveur : en cours ("R") et avec un état sauvegardé.
        Les bots sans état ont été créés avant la sauvegarde de la position : ils ne sont pas relancés
        automatiquement, pour ne pas remettre en route d'anciens bots par surprise (POST /bots/{id}/restart).
        """
        return self.db.query(Bot).filter(Bot.status == "R", Bot.state.isnot(None)).all()

    def update_state(self, bot_id: str, state: dict):
        self.db.query(Bot).filter(Bot.id == bot_id).update({"state": state})
        self.db.commit()

    def update_status(self, bot_id: str, status: str):
        self.db.query(Bot).filter(Bot.id == bot_id).update({"status": status})
        self.db.commit()
