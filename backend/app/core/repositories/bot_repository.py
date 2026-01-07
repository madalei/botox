from sqlalchemy.orm import Session
from app.core.models.bot import Bot


class BotRepository:
    """
    Implémentation du repository utilisant SQLAlchemy.
    """

    def __init__(self, db: Session):
        self.db = db

    def create_bot(self, bot):
        db_bot = Bot(
            id=bot.id,
            strategy=bot.strategy,
            params=bot.params
        )
        self.db.add(db_bot)
        self.db.commit()
        self.db.refresh(db_bot)
        return db_bot

    def get_all_bots(self):
        return self.db.query(Bot).all()
