from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from infrastructure.adapters.database import get_db
from infrastructure.repositories.order_repository import OrderRepository

router = APIRouter()

# Create a singleton dependency for the OrderRepository
def order_repository_singleton(db: Session = Depends(get_db)) -> OrderRepository:
    return OrderRepository(db)

@router.post("/orders")
def post_orders(order_repository: OrderRepository = Depends(order_repository_singleton)):
    """
    Add an order to the database.
    """
    return order_repository.create_order()