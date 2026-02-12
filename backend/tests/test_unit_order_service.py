import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.services.order_service import OrderService
from app.models.order import Order
from tests.factories.order_factory import build_order


@pytest.fixture
def mock_exchange():
    exchange = MagicMock()
    exchange.place_market_buy = AsyncMock()
    exchange.place_market_sell = AsyncMock()
    return exchange

@pytest.fixture
def mock_repository():
    repo = MagicMock()
    repo.create_order = MagicMock()
    repo.close = MagicMock()
    repo.commit = MagicMock()
    return repo

# -----------------------------------------
# Test BUY order execution
# -----------------------------------------

@pytest.mark.asyncio
async def test_create_order_buy_executes_market_buy(mock_exchange, mock_repository):
    buy_order = build_order(
        side="BUY",
        bot_id="bot_buy_test",
        symbol="BTC/EUR",
        amount=0.0002,
        stop_loss=0.02,
        take_profit=0.04,
    )

    service = OrderService(exchange=mock_exchange)
    service.repository = mock_repository

    await service.create_order(buy_order)
    mock_repository.create_order.assert_called_once_with(buy_order)
    mock_repository.close.assert_called_once()
    mock_exchange.place_market_buy.assert_awaited_once_with("BTC/EUR", 0.0002)

# -----------------------------------------
# Test SELL order execution
# -----------------------------------------

@pytest.mark.asyncio
async def test_create_order_sell_executes_market_sell(mock_exchange, mock_repository):

    sell_order = build_order(
        side="SELL",
        bot_id="bot_sell_test",
        amount=0.0003,
        symbol="BTC/EUR"
    )
    service = OrderService(exchange=mock_exchange)
    service.repository = mock_repository

    await service.create_order(sell_order)

    mock_exchange.place_market_sell.assert_awaited_once_with("BTC/EUR", 0.0003)

# -----------------------------------------
# Test exchange failure is handled
# -----------------------------------------

@pytest.mark.asyncio
async def test_create_order_exchange_failure_logs_error(mock_exchange, mock_repository):
    buy_order = build_order(
        side="BUY",
        bot_id="bot_buy_test",
        symbol="BTC/EUR",
        amount=0.0002,
        stop_loss=0.02,
        take_profit=0.04,
    )
    mock_exchange.place_market_buy.side_effect = Exception("API failure")

    service = OrderService(exchange=mock_exchange)
    service.repository = mock_repository

    await service.create_order(buy_order)

    mock_exchange.place_market_buy.assert_awaited_once()
    # Should not raise exception
