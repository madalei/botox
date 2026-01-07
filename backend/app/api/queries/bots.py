from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.infrastructure.adapters.database import get_db
from app.core.repositories.bot_repository import BotRepository

# from application.queries.get_orders import get_all_orders

router = APIRouter()

# Create a singleton dependency for the OrderRepository
def bot_repository_singleton(db: Session = Depends(get_db)) -> BotRepository:
    return BotRepository(db)

@router.get("/bots")
def get_bots(bot_repository: BotRepository = Depends(bot_repository_singleton)):
    """
    Récupère la liste des bots en base de données.
    """
    return bot_repository.get_all_bots()