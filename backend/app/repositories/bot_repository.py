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
            params=bot.strategy.model_dump(),
            status="R"
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
