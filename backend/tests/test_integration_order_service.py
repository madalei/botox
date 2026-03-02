import os
import pytest
from dotenv import load_dotenv

from app.repositories.order_repository import OrderRepository
from app.services.order_service import OrderService
from app.infrastructure.adapters.binance_adapter import BinanceAdapter
from app.models.order import Order
from tests.factories.bot_factory import create_bot_in_db
from tests.factories.order_factory import build_order


@pytest.mark.asyncio
@pytest.mark.integration
async def test_full_order_execution(test_db):

    # Simulate BaseBot.run() flow where an order is created and executed after a signal is generated

    exchange = BinanceAdapter(
        os.getenv("TESTNET_API_KEY"),
        os.getenv("TESTNET_SECRET"),
        sandbox=True
    )

    # Create Bot row first
    bot = create_bot_in_db(test_db)

    # init order repo
    order_repo = OrderRepository(test_db)

    # init orderService (should be injected to run())
    order_service = OrderService(exchange=exchange, repository=order_repo)

    # Like bot.run() flow
    # aka
    # 1. generates a signal
    # 2. creates an order in the database with status "PENDING"
    # 3. executes the order, which updates the status to "EXECUTED"

    # TODO: 1. mock signal generated, so we create an order

    buy_order = build_order(
        side="BUY",
        bot_id=bot.id,
        symbol="BTC/EUR",
        stop_loss=0.02,
        take_profit=0.04,
    )

    # 2. create order in DB
    db_order = await order_service.create_order(buy_order)

    assert db_order.symbol == "BTC/EUR"
    assert db_order.side == "BUY"
    assert db_order.status == "PENDING"

    # 3. execute order, which should call BinanceAdapter
    executed_order = await order_service.execute_order(db_order.id)
    assert db_order.status == "EXECUTED"

    await exchange.close()