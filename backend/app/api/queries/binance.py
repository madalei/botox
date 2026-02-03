from fastapi import APIRouter, HTTPException, Path
from app.infrastructure.adapters.binance_adapter import BinanceAdapter
from app.config import applicationSettings

router = APIRouter()

SUPPORTED_CURRENCIES = ["USD", "EUR", "GBP", "JPY"]


@router.get("/binance/btc/{currency}/price")
async def get_price(currency: str = Path(..., title="Fiat Currency", description="Fiat currency to compare BTC against",
                                   enum=SUPPORTED_CURRENCIES)):
    """
    Get last BTC price
    """
    binance_adapter = BinanceAdapter(
        api_key=applicationSettings.binance_keys.api_key,
        secret=applicationSettings.binance_keys.secret,
        sandbox=True
    )

    currency = currency.upper()
    supported_currencies = {
        "USD": "BTC/USDT",
        "EUR": "BTC/EUR",
        "GBP": "BTC/GBP",
        "JPY": "BTC/JPY"
    }

    if currency not in supported_currencies:
        raise HTTPException(status_code=400, detail=f"Unsupported currency '{currency}'")

    price = await binance_adapter.get_price(symbol=supported_currencies[currency])
    return {"symbol": supported_currencies[currency], "price": price}

@router.get("/binance/ohlcv")
async def get_ohlcv():
    """
    Get OHLCV candels in USDT: [timestamp, open, high, low, close, volume]
    """
    binance_adapter = BinanceAdapter(
        api_key=applicationSettings.binance_keys.api_key,
        secret=applicationSettings.binance_keys.secret,
        sandbox=True
    )

    ohlcv = await binance_adapter.get_ohlcv(symbol="BTC/USDT")
    return {"symbol": "BTC/USDT", "ohlcv": ohlcv}

