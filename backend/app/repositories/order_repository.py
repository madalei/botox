from typing import Optional, Dict, Any

from pydantic import UUID4
from pydantic.v1 import UUID1
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
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        return order

    def get_all_orders(self):
        return self.db.query(Order).all()

    def close(self):
        # Only close if we created it (when not handled by FastApi)
        if not self._external_db:
            self.db.close()

    def update_order(self, id: UUID4, updates: Dict[str, Any]) -> Optional[Order]:
        """
        Update an order with given fields.

        :param id: ID of the order to update
        :param updates: Dictionary of fields to update
        :return: Updated Order or None if not found
        """
        order = self.db.query(Order).filter(Order.id == id).first()

        if not order:
            return None

        for field, value in updates.items():
            if hasattr(order, field):
                setattr(order, field, value)

        self.db.commit()
        self.db.refresh(order)

        return order
