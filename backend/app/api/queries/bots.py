from fastapi import APIRouter, Depends, FastAPI, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.bots.bot_manager import BotManager
from app.infrastructure.adapters.database import get_db
from app.repositories.bot_repository import BotRepository
from typing import List, Dict, Any

router = APIRouter()

class RunningBot(BaseModel):
    bot_id: str
    status: str
    strategy: str
    params: Dict[str, Any]

# Create a singleton dependency for the OrderRepository
def bot_repository_singleton(db: Session = Depends(get_db)) -> BotRepository:
    return BotRepository(db)

def get_bot_manager(request: Request):
    return request.app.state.bot_manager

@router.get("/bots")
def get_bots(bot_repository: BotRepository = Depends(bot_repository_singleton)):
    """
    Returns all bots from DB
    """
    return bot_repository.get_all_bots()


@router.get("/bots/running", response_model=List[RunningBot])
def get_running_bots(bot_manager: BotManager = Depends(get_bot_manager)):
    """
    Returns all currently running bots.
    """
    return bot_manager.list_running_bots()