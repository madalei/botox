from datetime import datetime

from aiohttp import payload
from fastapi import APIRouter, Depends, FastAPI, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.bots.base import BaseBot
from app.bots.strategies.moving_average_crossover import MovingAverageCrossoverStrategy
from app.infrastructure.adapters.database import get_db
from app.repositories.bot_repository import BotRepository

from app.bots.bot_manager import BotManager
from app.services.logging import bot_logger

router = APIRouter()

# Create a singleton dependency for the BotRepository
def bot_repository_singleton(db: Session = Depends(get_db)) -> BotRepository:
    return BotRepository(db)

class StrategyParams(BaseModel):
    symbol: str = Field( default="BTC/USDT", description="Trading pair symbol")
    timeframe: str = Field( default="1h", description="Candlestick timeframe")
    short_window: int = Field( default=20,ge=1,description="Short moving average window")
    long_window: int = Field(default=50,ge=1,description="Long moving average window")
    check_interval: int = Field(default=900,description="Time Interval in second, between strategy execute")
    stop_loss_pct: float = Field(default=0.02,gt=0,le=1,description="Stop loss percentage (0–1)")

@router.post("/bots")
async def create_bots( strategy_params: StrategyParams,
                       request: Request,
                       bot_repository: BotRepository = Depends(bot_repository_singleton)):
    """
    Create a bot, write it in the DB, register it to a pool of bots and run it
    """

    bot_logger.info(f"Entering POST /bots with params")


    bot_manager: BotManager = request.app.state.bot_manager # singleton BotManager

    # Create strategy instance
    # Todo: make the strategy customisable from input param
    strategy = MovingAverageCrossoverStrategy(**strategy_params.model_dump())

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    bot_id = f"BOT_{timestamp}"

    # Create a bot
    bot = BaseBot(bot_id=bot_id, strategy=strategy, check_interval=strategy_params.check_interval)

    # Save to DB (sync operation)
    db_bot = bot_repository.create_bot(bot)

    # Register and Start it (async)
    bot_manager.register_bot(bot)
    await bot_manager.start_bot(bot.bot_id)

    return {
        "bot_id": db_bot.id,
        "status": bot.status,
        "created_at": db_bot.created_at
    }

