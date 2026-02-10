import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.bots.base import BaseBot, BotStatus
from tests.factories.order_factory import build_order

@pytest.mark.asyncio
async def test_bot_creates_order_when_signal_detected():
    # Arrange
    strategy = MagicMock()
    fake_order = build_order(
        side="BUY",
        stop_loss=0.02,
        take_profit=0.04,
    )

    strategy.generate_signals = AsyncMock(return_value=fake_order)

    order_service = MagicMock()

    bot = BaseBot(
        bot_id="test-bot",
        strategy=strategy,
        capital=1000,
        check_interval=0,  # important: no waiting
    )

    exchange = MagicMock()

    bot.status = BotStatus.RUNNING

    # Stop the loop after one iteration
    async def stop_after_one_iteration(*args, **kwargs):
        bot.status = BotStatus.STOPPED

    # Patch asyncio.sleep so it doesn't actually sleep
    with patch("asyncio.sleep", new=AsyncMock(side_effect=stop_after_one_iteration)):
        await bot.run(exchange, order_service)

    # Assert
    strategy.generate_signals.assert_called_once_with(exchange, bot.capital)
    order_service.create_order.assert_called_once_with(fake_order)
