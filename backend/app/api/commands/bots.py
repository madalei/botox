from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.infrastructure.adapters.database import get_db
from app.repositories.bot_repository import BotRepository

router = APIRouter()

# Create a singleton dependency for the BotRepository
def bot_repository_singleton(db: Session = Depends(get_db)) -> BotRepository:
    return BotRepository(db)

@router.post("/bots")
def post_bots(bot_repository: BotRepository = Depends(bot_repository_singleton)):
    """
    Add an bot to the database.
    """
    return bot_repository.create_bot()
