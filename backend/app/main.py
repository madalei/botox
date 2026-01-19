from contextlib import asynccontextmanager

from fastapi import FastAPI
from app.api.router import router
from app.config import applicationSettings
from app.services.order_service import OrderService
from app.bots.bot_manager import BotManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    exchange = None  # your CCXT client
    order_service = OrderService()
    bot_manager = BotManager(exchange=exchange, order_service=order_service)

    # Store in app.state
    app.state.bot_manager = bot_manager

    yield  # Application runs here

    # Shutdown (cleanup)
    # e.g., close connections, stop bots gracefully
    # await bot_manager.shutdown()


app = FastAPI(title="Botox API", lifespan=lifespan)

# Importer toutes les routes définies dans router.py
app.include_router(router)



#
# app = FastAPI(title="Botox API")
#
# # Importer toutes les routes définies dans router.py
# app.include_router(router)
#
# @app.on_event("startup")
# async def startup_event():
#     """
#     Code executed once when the app starts.
#     Initialize singleton services like BotManager.
#     """
#     # Binance client (async)
#     #exchange = ...  # your CCXT client
#     exchange = None
#     #binance_service = BinanceService()
#
#     # OrderService internally manages repository/sessions
#     order_service = OrderService()
#
#     # BotManager singleton, holds all running bots in memory
#     bot_manager = BotManager(exchange=exchange, order_service=order_service)
#
#     # Store singleton in app.state
#     app.state.bot_manager = bot_manager