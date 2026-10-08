from os import system

from fastapi import APIRouter
from . import commands, queries
from app.api.queries import binance, coinbase
from app.api.queries import bots, orders
from app.api.commands import bots
from app.config import applicationSettings

router = APIRouter()

# Include all routes
router.include_router(queries.bots.router, tags=["queries"])
router.include_router(commands.bots.router, tags=["commands"])
# Market data routes use app.state.exchange, so only expose the ones of the active exchange
# (otherwise /coinbase/... would silently return Binance prices when EXCHANGE=binance)
if applicationSettings.exchange == "binance":
    router.include_router(queries.binance.router, tags=["queries"])
else:
    router.include_router(queries.coinbase.router, tags=["queries"])
#router.include_router(adapters.router, prefix="/system", tags=["system"])

router.include_router(queries.orders.router, tags=["queries"])
