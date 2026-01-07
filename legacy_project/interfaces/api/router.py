from os import system

from fastapi import APIRouter
from interfaces.api import commands, queries
from interfaces.api.queries import orders
from interfaces.api.queries import binance
from interfaces.api.system import adapters

router = APIRouter()

# Include all routes
router.include_router(queries.orders.router, tags=["queries"])
router.include_router(queries.binance.router, tags=["queries"])
router.include_router(adapters.router, prefix="/system", tags=["system"])
