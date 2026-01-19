from typing import Optional
from sqlalchemy.orm import Session
from app.models.order import Order
from app.infrastructure.adapters.database import get_db, SessionLocal


class OrderRepository:
    """
    Implémentation du repository utilisant SQLAlchemy.
    """

    def __init__(self, db: Optional[Session] = None):
        self._external_db = db
        # db: when coming from a FastApi session, where db has been injected with Depends(get_db())
        # SessionLocal(): when called from a service such as OrderService, this one needs to be explicitely closed
        self.db = db or SessionLocal()

    def create_order(self, order):
        db_order = Order(
            id=order.id
        )
        self.db.add(db_order)
        self.db.commit()
        self.db.refresh(db_order)
        return db_order

    def get_all_orders(self):
        return self.db.query(Order).all()

    def close(self):
        # Only close if we created it (when not handled by FastApi)
        if not self._external_db:
            self.db.close()
