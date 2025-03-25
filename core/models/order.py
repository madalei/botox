from sqlalchemy import Column, Integer, String, Float
from infrastructure.adapters.database import Base

class Order(Base):
    """
    Modèle de base de données pour stocker les ordres de trading.
    """
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    operation = Column(String)  # "B" for buy ou "S" for sell
    price = Column(Float)
    quantity = Column(Float)
    total = Column(Float)
    currency = Column(String)
