from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from infrastructure.adapters.database import get_db
from infrastructure.repositories.order_repository import OrderRepository

# from application.queries.get_orders import get_all_orders

router = APIRouter()

# Create a singleton dependency for the OrderRepository
def order_repository_singleton(db: Session = Depends(get_db)) -> OrderRepository:
    return OrderRepository(db)

@router.get("/orders")
def get_orders(order_repository: OrderRepository = Depends(order_repository_singleton)):
# def get_orders(db: Session = Depends(get_db)):
    """
    Récupère la liste des ordres en base de données.
    """
    # return {"message": "Please return all orders"}
    return order_repository.get_all_orders()