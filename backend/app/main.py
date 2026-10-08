from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import router
from app.config import applicationSettings
from app.infrastructure.adapters.exchange_factory import create_exchange
from app.services.order_service import OrderService
from app.bots.bot_manager import BotManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    # Exchange (Coinbase or Binance) is selected by the EXCHANGE env var
    exchange = create_exchange(applicationSettings)
    order_service = OrderService(exchange=exchange)
    bot_manager = BotManager(exchange=exchange, order_service=order_service)

    # Store in app.state
    app.state.bot_manager = bot_manager
    app.state.exchange = exchange

    yield  # Application runs here

    # Shutdown (cleanup)
    # e.g., close connections, stop bots gracefully
    # await bot_manager.shutdown()
    await exchange.close()


app = FastAPI(title="Botox API", lifespan=lifespan, root_path=applicationSettings.root_path)

# Allow the React frontend (different origin/port) to call the API from the browser
app.add_middleware(
    CORSMiddleware,
    allow_origins=applicationSettings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Importer toutes les routes définies dans router.py
app.include_router(router)

