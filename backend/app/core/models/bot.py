from sqlalchemy import String, JSON, DateTime, func
from sqlalchemy import Column, Integer, String, Float, DateTime
from app.infrastructure.adapters.database import Base

class Bot(Base):
    __tablename__ = "bots"

    id = Column(String, primary_key=True)
    strategy = Column(String, index=True)
    params = Column(JSON)
    status = Column(String, index=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )