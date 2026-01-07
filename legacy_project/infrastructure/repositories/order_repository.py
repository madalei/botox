from sqlalchemy.orm import Session
from core.models.order import Order


class OrderRepository:
    """
    Implémentation du repository utilisant SQLAlchemy.
    """

    def __init__(self, db: Session):
        self.db = db

    def create_order(self, order):
        db_order = Order(
            operation=order.operation,
            price=order.price,
            quantity=order.quantity
        )
        self.db.add(db_order)
        self.db.commit()
        self.db.refresh(db_order)
        return db_order

    def get_all_orders(self):
        return self.db.query(Order).all()
