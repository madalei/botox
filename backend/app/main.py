from contextlib import asynccontextmanager

from fastapi import FastAPI
from app.api.router import router
from app.config import applicationSettings
from app.infrastructure.adapters.binance_adapter import BinanceAdapter
from app.services.order_service import OrderService
from app.bots.bot_manager import BotManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    exchange = BinanceAdapter(
        api_key=applicationSettings.binance_keys.api_key,
        secret=applicationSettings.binance_keys.secret,
        sandbox=True
    )
    order_service = OrderService()
    bot_manager = BotManager(exchange=exchange, order_service=order_service)

    # Store in app.state
    app.state.bot_manager = bot_manager
    app.state.exchange = exchange

    yield  # Application runs here

    # Shutdown (cleanup)
    # e.g., close connections, stop bots gracefully
    # await bot_manager.shutdown()
    await exchange.close()


app = FastAPI(title="Botox API", lifespan=lifespan)

# Importer toutes les routes définies dans router.py
app.include_router(router)

