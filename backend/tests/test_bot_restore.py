"""
Redémarrage du serveur (ex. mise à jour Docker) : la position de chaque bot est sauvegardée en base
et les bots en cours sont relancés avec elle.
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.bots.base import BaseBot
from app.bots.bot_factory import build_bot_from_orm
from app.bots.strategies.moving_average_crossover import MovingAverageCrossoverStrategy
from app.infrastructure.adapters.historical_exchange import HistoricalExchange
from app.models.bot import Bot
from app.repositories.bot_repository import BotRepository
from tests.test_moving_average_strategy import CLOSES_WITH_UPWARD_CROSS, make_candles


def exchange_on_buy_candle() -> HistoricalExchange:
    """Historique arrêté sur la bougie du croisement haussier : la stratégie 2/3 achète à 100."""
    exchange = HistoricalExchange(make_candles(CLOSES_WITH_UPWARD_CROSS))
    exchange.cursor = len(CLOSES_WITH_UPWARD_CROSS)
    return exchange


def order_service_returning(status: str) -> MagicMock:
    order_service = MagicMock()
    order_service.create_order = AsyncMock(return_value=SimpleNamespace(id="order-1"))
    order_service.execute_order = AsyncMock(return_value=SimpleNamespace(status=status))
    return order_service


def ma_bot(save_state=None) -> BaseBot:
    strategy = MovingAverageCrossoverStrategy(short_window=2, long_window=3)
    return BaseBot(bot_id="test-bot", strategy=strategy, capital=1000, save_state=save_state)


# --- BaseBot.tick -----------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_executed_buy_is_saved():
    save_state = MagicMock()
    bot = ma_bot(save_state)

    await bot.tick(exchange_on_buy_candle(), order_service_returning("EXECUTED"))

    save_state.assert_called_once()
    bot_id, state = save_state.call_args.args
    assert bot_id == "test-bot"
    assert state["is_position_open"] is True
    assert state["entry_price"] == 100


@pytest.mark.asyncio
async def test_failed_buy_restores_position_state():
    # Ordre refusé par Coinbase (solde insuffisant...) : le bot ne doit pas croire qu'il a des BTC
    save_state = MagicMock()
    bot = ma_bot(save_state)

    await bot.tick(exchange_on_buy_candle(), order_service_returning("FAILED"))

    assert bot.strategy.get_state()["is_position_open"] is False
    save_state.assert_not_called()


# --- Base de données ----------------------------------------------------------------------------------

def test_bot_is_rebuilt_with_its_position_and_check_interval(test_db):
    repository = BotRepository(test_db)
    strategy = MovingAverageCrossoverStrategy(timeframe="1d", short_window=50, long_window=200, risk_per_trade=0.02)
    strategy.load_state({"is_position_open": True, "entry_price": 60000.0, "position_size": 0.001,
                         "stop_loss": 51000.0, "highest_price": 70000.0, "entry_candle_time": "2026-10-01T00:00:00"})
    repository.create_bot(BaseBot(bot_id="test-restore-bot", strategy=strategy, check_interval=3600))

    restored = build_bot_from_orm(repository.get_bot_by_id("test-restore-bot"))

    assert restored.check_interval == 3600
    assert restored.strategy.risk_per_trade == 0.02
    assert restored.strategy.get_state() == strategy.get_state()


def test_only_running_bots_with_saved_state_are_restored(test_db):
    repository = BotRepository(test_db)
    repository.create_bot(BaseBot(bot_id="test-running-bot", strategy=MovingAverageCrossoverStrategy()))
    repository.create_bot(BaseBot(bot_id="test-stopped-bot", strategy=MovingAverageCrossoverStrategy()))
    repository.update_status("test-stopped-bot", "S")
    # Ancien bot créé avant la colonne state
    test_db.add(Bot(id="test-legacy-bot", strategy="MovingAverageCrossoverStrategy", params={}, status="R"))
    test_db.commit()

    restored_ids = {bot.id for bot in repository.get_bots_to_restore()}

    assert "test-running-bot" in restored_ids
    assert "test-stopped-bot" not in restored_ids
    assert "test-legacy-bot" not in restored_ids


def test_state_update_is_stored(test_db):
    repository = BotRepository(test_db)
    repository.create_bot(BaseBot(bot_id="test-state-bot", strategy=MovingAverageCrossoverStrategy()))

    repository.update_state("test-state-bot", {"is_position_open": True, "stop_loss": 51000.0})

    assert repository.get_bot_by_id("test-state-bot").state == {"is_position_open": True, "stop_loss": 51000.0}
