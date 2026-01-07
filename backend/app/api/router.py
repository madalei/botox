from os import system

from fastapi import APIRouter
from app.api import commands, queries
from app.api.queries import binance
from app.api.queries import bots

router = APIRouter()

# Include all routes
router.include_router(queries.bots.router, tags=["queries"])
router.include_router(queries.binance.router, tags=["queries"])
#router.include_router(adapters.router, prefix="/system", tags=["system"])
