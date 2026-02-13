import os
import pytest
from dotenv import load_dotenv
from app.infrastructure.adapters.binance_adapter import BinanceAdapter


@pytest.mark.asyncio
@pytest.mark.integration
async def test_market_buy_on_testnet():

    load_dotenv(".env.test")
    api_key = os.getenv("BINANCE_API_KEY")
    secret = os.getenv("BINANCE_SECRET")

    exchange = BinanceAdapter(api_key, secret, sandbox=True)

    try:
        order = await exchange.place_market_buy(
            "BTC/USDT",
            0.0002
        )

        assert order is not None
        assert order["status"] in ["open", "closed"]

    finally:
        await exchange.close()