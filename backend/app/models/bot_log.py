from sqlalchemy import String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class BotLog(Base):
    __tablename__ = "bot_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    bot_id: Mapped[str] = mapped_column(ForeignKey("bots.id", ondelete="CASCADE"))
    level: Mapped[str] = mapped_column(String)
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
