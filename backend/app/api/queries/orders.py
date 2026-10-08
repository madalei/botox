from fastapi import APIRouter, Depends, FastAPI, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.infrastructure.adapters.database import get_db
from app.repositories.order_repository import OrderRepository

# Create a FastAPI router for order-related endpoints
router = APIRouter()

# Create a singleton dependency for the OrderRepository
def order_repository_singleton(db: Session = Depends(get_db)) -> OrderRepository:
    return OrderRepository(db)


@router.get("/orders")
def get_orders(order_repository: OrderRepository = Depends(order_repository_singleton)):
    """
    Returns all orders from DB
    """
    return order_repository.get_all_orders()



@router.get("/orders/{order_id}")
def get_order(order_id: str, order_repository: OrderRepository = Depends(order_repository_singleton
)):
    """
    Returns a specific order by ID from DB
    """
    return order_repository.get_order_by_id(order_id)

