from datetime import datetime

from app.models.bot import Bot


def create_bot_in_db(db_session, bot_id="test-bot"):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bot = Bot(
        id=f"test-bot-{timestamp}",
        strategy="test-strategy",
        params={"param1": "value1", "param2": 42},
        status="CREATED"
    )
    db_session.add(bot)
    db_session.commit()
    return bot