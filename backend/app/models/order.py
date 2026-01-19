from sqlalchemy import String, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.infrastructure.adapters.database import Base
from datetime import datetime
import uuid

class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    bot_id: Mapped[str] = mapped_column(ForeignKey("bots.id", ondelete="CASCADE"))
    symbol: Mapped[str] = mapped_column(String)
    side: Mapped[str] = mapped_column(String)
    price: Mapped[float] = mapped_column(Numeric)
    quantity: Mapped[float] = mapped_column(Numeric)
    executed_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
