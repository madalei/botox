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




I want to create an app that build bots workers that trade cryptos currencies.
I would like to be able to instantiate, pause, stop or restart bots with differents values regarding their trading stategy.
Example, I want to have 2 bots running "moving average stategy" but with different parameters.
I want to have a dash board for it (front end) and another dash board (or just a sub part/tab of my dash board) showing logs. Maybe using loki or grafana, I don't know.
Can you propose an architecture for my project (React + python) and a code starter?
