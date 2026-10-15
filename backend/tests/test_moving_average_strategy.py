import json

import pandas as pd
import pytest
from app.bots.strategies.moving_average_crossover import MovingAverageCrossoverStrategy
from app.infrastructure.adapters.historical_exchange import HistoricalExchange

# Falling then rising closes: with 2/3 windows the short MA crosses above the long MA on the last candle (index 7)
CLOSES_WITH_UPWARD_CROSS = [100, 100, 100, 99, 98, 97, 96, 100]
ENTRY_PRICE = 100


def make_candles(closes, overrides=None) -> pd.DataFrame:
    """Candles with open = high = low = close, except the {index: {column: value}} overrides."""
    candles = pd.DataFrame({
        "timestamp": range(len(closes)),
        "open": closes, "high": closes, "low": closes, "close": closes, "volume": 1.0,
    }).astype({"open": float, "high": float, "low": float, "close": float})
    for index, values in (overrides or {}).items():
        for column, value in values.items():
            candles.loc[index, column] = value
    return candles


async def replay(candles: pd.DataFrame, strategy: MovingAverageCrossoverStrategy) -> list:
    exchange = HistoricalExchange(candles)
    orders = []
    while exchange.tick():
        order = await strategy.generate_signals(exchange)
        if order:
            orders.append(order)
    return orders


def strategy(**params) -> MovingAverageCrossoverStrategy:
    # SL at 98, TP at 104 for an entry at 100
    params = {"stop_loss_pct": 0.02, "take_profit_pct": 0.04, **params}
    return MovingAverageCrossoverStrategy(short_window=2, long_window=3, **params)


@pytest.mark.asyncio
async def test_buys_on_upward_crossover():
    orders = await replay(make_candles(CLOSES_WITH_UPWARD_CROSS), strategy())

    assert [o.side for o in orders] == ["BUY"]
    assert orders[0].price == ENTRY_PRICE


@pytest.mark.asyncio
async def test_stop_loss_hit_by_candle_low_exits_at_stop_level():
    # Next candle dips to 97 but closes at 101: the old close-only check missed this stop
    candles = make_candles(CLOSES_WITH_UPWARD_CROSS + [101], {8: {"low": 97}})

    orders = await replay(candles, strategy())

    assert [o.side for o in orders] == ["BUY", "SELL"]
    assert orders[1].price == pytest.approx(98)


@pytest.mark.asyncio
async def test_stop_loss_gap_exits_at_open():
    # Next candle opens at 95, below the 98 stop: the stop can only fill at the open
    candles = make_candles(CLOSES_WITH_UPWARD_CROSS + [96], {8: {"open": 95, "high": 96, "low": 94}})

    orders = await replay(candles, strategy())

    assert orders[1].price == 95


@pytest.mark.asyncio
async def test_take_profit_hit_by_candle_high_exits_at_take_profit_level():
    candles = make_candles(CLOSES_WITH_UPWARD_CROSS + [101], {8: {"high": 105}})

    orders = await replay(candles, strategy())

    assert [o.side for o in orders] == ["BUY", "SELL"]
    assert orders[1].price == pytest.approx(104)


@pytest.mark.asyncio
async def test_stop_and_take_profit_in_same_candle_assumes_stop_loss():
    candles = make_candles(CLOSES_WITH_UPWARD_CROSS + [101], {8: {"low": 97, "high": 105}})

    orders = await replay(candles, strategy())

    assert orders[1].price == pytest.approx(98)


@pytest.mark.asyncio
async def test_entry_candle_low_is_ignored():
    # The entry candle's low happened before the BUY at its close: it must not trigger the stop
    candles = make_candles(CLOSES_WITH_UPWARD_CROSS, {7: {"low": 90}})

    orders = await replay(candles, strategy())

    assert [o.side for o in orders] == ["BUY"]


@pytest.mark.asyncio
async def test_trend_filter_skips_buy_below_trend_ma():
    # Long downtrend before the cross: the 100 entry is below the 12-candle average (~103.3)
    closes = [125, 120, 115, 110, 105] + CLOSES_WITH_UPWARD_CROSS
    orders = await replay(make_candles(closes), strategy(trend_window=12))

    assert orders == []


@pytest.mark.asyncio
async def test_trend_filter_allows_buy_above_trend_ma():
    # Uptrend before the dip: the 100 entry is above the 12-candle average (95)
    closes = [75, 80, 85, 90, 95] + CLOSES_WITH_UPWARD_CROSS
    orders = await replay(make_candles(closes), strategy(trend_window=12))

    assert [o.side for o in orders] == ["BUY"]


# --- Stop suiveur ---------------------------------------------------------------------------------
# Achat à 100, stop suiveur 5 %, pas de take profit : le stop initial est à 98 (stop_loss_pct 2 %)

def trailing_strategy() -> MovingAverageCrossoverStrategy:
    return strategy(take_profit_pct=0, trailing_stop_pct=0.05)


@pytest.mark.asyncio
async def test_trailing_stop_follows_highest_price():
    # Bougie 8 : le prix monte à 110 -> le stop remonte à 110 × 0.95 = 104.5
    # Bougie 9 : le prix redescend à 104 -> vente au stop suiveur, à 104.5 (gain malgré la baisse)
    candles = make_candles(CLOSES_WITH_UPWARD_CROSS + [109, 105], {8: {"high": 110}, 9: {"low": 104}})

    orders = await replay(candles, trailing_strategy())

    assert [o.side for o in orders] == ["BUY", "SELL"]
    assert orders[1].price == pytest.approx(104.5)


@pytest.mark.asyncio
async def test_trailing_stop_never_goes_down():
    # Le plus haut (110) est atteint en bougie 8, puis le prix reste plus bas :
    # le stop reste à 104.5, il ne redescend pas avec les plus hauts suivants (106, 105)
    # Bougie 10 : ouvre à 106 puis descend à 104.4 -> vente à 104.5
    candles = make_candles(CLOSES_WITH_UPWARD_CROSS + [109, 106, 104.4], {8: {"high": 110}, 10: {"open": 106, "high": 106}})

    orders = await replay(candles, trailing_strategy())

    assert [o.side for o in orders] == ["BUY", "SELL"]
    assert orders[1].price == pytest.approx(104.5)


@pytest.mark.asyncio
async def test_trailing_stop_applies_from_next_candle():
    # Bougie 8 : plus haut 110 et plus bas 103 dans la même bougie. On ne sait pas lequel est arrivé en premier,
    # donc le nouveau stop (104.5) ne s'applique pas à cette bougie : seul le stop initial (98) compte -> pas de vente
    candles = make_candles(CLOSES_WITH_UPWARD_CROSS + [108], {8: {"high": 110, "low": 103}})

    orders = await replay(candles, trailing_strategy())

    assert [o.side for o in orders] == ["BUY"]


@pytest.mark.asyncio
async def test_no_take_profit_when_take_profit_pct_is_zero():
    # +20 % sans vente : sans take profit, la position reste ouverte tant que le stop n'est pas touché
    candles = make_candles(CLOSES_WITH_UPWARD_CROSS + [110, 120])

    orders = await replay(candles, trailing_strategy())

    assert [o.side for o in orders] == ["BUY"]
    assert orders[0].take_profit is None


# --- Achat tant que la tendance est haussière (buy_while_trend) -----------------------------------

@pytest.mark.asyncio
async def test_buy_while_trend_rebuys_after_stop_loss():
    # Bougie 8 : touche le stop à 98 (plus bas 97) puis clôture à 101
    # Bougie 9 : la courte est toujours au-dessus de la longue -> rachat à 102, sans attendre un nouveau croisement
    candles = make_candles(CLOSES_WITH_UPWARD_CROSS + [101, 102], {8: {"low": 97}})

    default_orders = await replay(candles, strategy())
    trend_orders = await replay(candles, strategy(buy_while_trend=True))

    assert [o.side for o in default_orders] == ["BUY", "SELL"]
    assert [o.side for o in trend_orders] == ["BUY", "SELL", "BUY"]
    assert trend_orders[2].price == 102


# --- Pas de vente au croisement baissier (exit_on_crossover=False) --------------------------------

@pytest.mark.asyncio
async def test_exit_on_crossover_false_keeps_position_on_downward_cross():
    # Bougie 9 : la courte repasse sous la longue (croisement baissier) sans toucher le stop à 98
    candles = make_candles(CLOSES_WITH_UPWARD_CROSS + [99, 98.5])

    default_orders = await replay(candles, strategy())
    hold_orders = await replay(candles, strategy(exit_on_crossover=False))

    assert [o.side for o in default_orders] == ["BUY", "SELL"]
    assert [o.side for o in hold_orders] == ["BUY"]


# --- Sauvegarde / rechargement de la position (redémarrage du serveur) ---------------------------

def reload_through_json(strategy_before: MovingAverageCrossoverStrategy, **params) -> MovingAverageCrossoverStrategy:
    """Nouvelle instance rechargée depuis l'état sauvegardé, en passant par du JSON comme la colonne bots.state."""
    restarted = strategy(**params)
    restarted.load_state(json.loads(json.dumps(strategy_before.get_state())))
    return restarted


@pytest.mark.asyncio
async def test_trailing_stop_survives_restart():
    # Même scénario que test_trailing_stop_follows_highest_price, avec un redémarrage entre les bougies 8 et 9 :
    # le stop suiveur remonté à 104.5 doit être retrouvé, sinon la vente se ferait au stop initial (98)
    candles = make_candles(CLOSES_WITH_UPWARD_CROSS + [109, 105], {8: {"high": 110}, 9: {"low": 104}})
    before_restart = trailing_strategy()
    await replay(candles.iloc[:9], before_restart)

    restarted = reload_through_json(before_restart, take_profit_pct=0, trailing_stop_pct=0.05)
    exchange = HistoricalExchange(candles)
    exchange.cursor = len(candles)
    order = await restarted.generate_signals(exchange)

    assert order.side == "SELL"
    assert order.price == pytest.approx(104.5)
    assert order.amount == pytest.approx(before_restart.get_state()["position_size"])


@pytest.mark.asyncio
async def test_restart_on_entry_candle_keeps_ignoring_its_low():
    # En live les bougies ont des dates pandas : après rechargement, la bougie d'achat doit toujours être reconnue
    candles = make_candles(CLOSES_WITH_UPWARD_CROSS, {7: {"low": 90}})
    candles["timestamp"] = pd.date_range("2026-01-01", periods=len(candles), freq="D")
    before_restart = strategy()
    await replay(candles, before_restart)

    restarted = reload_through_json(before_restart)
    exchange = HistoricalExchange(candles)
    exchange.cursor = len(candles)

    assert await restarted.generate_signals(exchange) is None
    assert restarted.get_state()["is_position_open"]


def test_load_state_none_means_no_position():
    # Bot créé avant la sauvegarde de l'état (colonne bots.state vide)
    restarted = strategy()
    restarted.load_state(None)

    assert restarted.get_state()["is_position_open"] is False
