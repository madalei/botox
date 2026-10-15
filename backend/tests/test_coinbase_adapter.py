import pytest
from unittest.mock import AsyncMock, MagicMock

from app.infrastructure.adapters.coinbase_adapter import CoinbaseAdapter


def build_adapter(sandbox: bool) -> CoinbaseAdapter:
    """CoinbaseAdapter with a mocked ccxt client, so no network call is made."""
    exchange = CoinbaseAdapter(api_key=None, secret=None, sandbox=sandbox)
    exchange.client = MagicMock()
    exchange.client.load_markets = AsyncMock()
    exchange.client.amount_to_precision = MagicMock(side_effect=lambda symbol, amount: str(amount))
    exchange.client.fetch_ticker = AsyncMock(return_value={"last": 60000.0})
    exchange.client.create_market_buy_order = AsyncMock(return_value={"id": "real-buy", "status": "closed"})
    exchange.client.create_market_sell_order = AsyncMock(return_value={"id": "real-sell", "status": "closed"})
    return exchange


@pytest.mark.asyncio
async def test_paper_trading_market_buy_is_not_sent_to_coinbase():
    exchange = build_adapter(sandbox=True)

    order = await exchange.place_market_buy("BTC/EUR", 0.0002)

    exchange.client.create_market_buy_order.assert_not_called()
    assert order["id"].startswith("paper-")
    assert order["side"] == "buy"
    assert order["filled"] == 0.0002
    assert order["average"] == 60000.0
    assert order["status"] == "closed"


@pytest.mark.asyncio
async def test_paper_trading_market_sell_is_not_sent_to_coinbase():
    exchange = build_adapter(sandbox=True)

    order = await exchange.place_market_sell("BTC/EUR", 0.0002)

    exchange.client.create_market_sell_order.assert_not_called()
    assert order["side"] == "sell"
    assert order["status"] == "closed"


@pytest.mark.asyncio
async def test_live_market_buy_passes_price_to_compute_cost():
    # Coinbase market buys are expressed in quote currency, ccxt needs the price to compute the cost
    exchange = build_adapter(sandbox=False)

    order = await exchange.place_market_buy("BTC/EUR", 0.0002)

    exchange.client.create_market_buy_order.assert_awaited_once_with("BTC/EUR", "0.0002", params={"price": 60000.0})
    assert order["id"] == "real-buy"


@pytest.mark.asyncio
async def test_live_market_sell_is_sent_to_coinbase():
    exchange = build_adapter(sandbox=False)

    order = await exchange.place_market_sell("BTC/EUR", 0.0002)

    exchange.client.create_market_sell_order.assert_awaited_once_with("BTC/EUR", "0.0002")
    assert order["id"] == "real-sell"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_paper_market_buy_with_live_coinbase_prices():
    # Uses the public Coinbase API (network needed), no API key required in paper trading mode
    exchange = CoinbaseAdapter(api_key=None, secret=None, sandbox=True)

    try:
        order = await exchange.place_market_buy(
            "BTC/EUR",
            0.0002
        )

        assert order is not None
        assert order["status"] in ["open", "closed"]
        assert order["average"] > 0

        history = await exchange.get_history("BTC/EUR", "1h", limit=250)
        assert len(history) > 0

    finally:
        await exchange.close()


# --- Solde réel et limite de 300 bougies ----------------------------------------------------------

@pytest.mark.asyncio
async def test_paper_trading_has_no_real_balance():
    # En paper trading, None : le bot utilise son capital fixe
    exchange = build_adapter(sandbox=True)
    exchange.client.fetch_balance = AsyncMock()

    assert await exchange.get_free_balance("EUR") is None
    exchange.client.fetch_balance.assert_not_called()


@pytest.mark.asyncio
async def test_live_free_balance_reads_coinbase_account():
    exchange = build_adapter(sandbox=False)
    exchange.client.fetch_balance = AsyncMock(return_value={"free": {"EUR": 1234.5, "BTC": 0.01}})

    assert await exchange.get_free_balance("EUR") == 1234.5


@pytest.mark.asyncio
async def test_get_history_asks_at_most_300_latest_candles():
    # 1d 50/200 demande 1000 bougies : au-delà de 300, Coinbase renverrait de vieilles bougies (depuis `since`)
    exchange = build_adapter(sandbox=True)
    exchange.client.milliseconds = MagicMock(return_value=1_000_000_000_000)
    exchange.client.parse_timeframe = MagicMock(return_value=86400)
    exchange.client.fetch_ohlcv = AsyncMock(return_value=[])

    await exchange.get_history("BTC/EUR", "1d", limit=1000)

    exchange.client.fetch_ohlcv.assert_awaited_once_with(
        "BTC/EUR", timeframe="1d", since=1_000_000_000_000 - 300 * 86400 * 1000, limit=300
    )
