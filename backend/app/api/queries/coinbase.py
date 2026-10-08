from fastapi import APIRouter, HTTPException, Path, Request

router = APIRouter()

SUPPORTED_CURRENCIES = ["EUR", "USD", "USDC", "GBP"]


@router.get("/coinbase/btc/{currency}/price")
async def get_price(request: Request,
                    currency: str = Path(..., title="Fiat Currency", description="Fiat currency to compare BTC against",
                                         enum=SUPPORTED_CURRENCIES)):
    """
    Get last BTC price
    """
    exchange = request.app.state.exchange

    currency = currency.upper()
    supported_currencies = {
        "EUR": "BTC/EUR",
        "USD": "BTC/USD",
        "USDC": "BTC/USDC",
        "GBP": "BTC/GBP"
    }

    if currency not in supported_currencies:
        raise HTTPException(status_code=400, detail=f"Unsupported currency '{currency}'")

    price = await exchange.get_price(symbol=supported_currencies[currency])
    return {"symbol": supported_currencies[currency], "price": price}

@router.get("/coinbase/ohlcv")
async def get_ohlcv(request: Request):
    """
    Get OHLCV candels in EUR: [timestamp, open, high, low, close, volume]
    """
    exchange = request.app.state.exchange

    ohlcv = await exchange.fetch_ohlcv(symbol="BTC/EUR")
    return {"symbol": "BTC/EUR", "ohlcv": ohlcv}
