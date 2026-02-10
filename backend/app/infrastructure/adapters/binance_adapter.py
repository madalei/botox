import ccxt.async_support as ccxt_async

class BinanceAdapter:
    def __init__(self, api_key: str, secret: str, sandbox: bool = True):
        self.client = ccxt_async.binance({
            "apiKey": api_key,
            "secret": secret,
            "enableRateLimit": True,
        })
        self.client.set_sandbox_mode(sandbox)

    def milliseconds(self) -> int:
        return self.client.milliseconds() # cctx.milliseconds

    def parse_timeframe(self, timeframe: str) -> int:
        return self.client.parse_timeframe(timeframe)

    # @param symbol
    #   "BTC/USDT" → trading Bitcoin against Tether
    #   "ETH/EUR" → trading Ethereum against euros
    #   "DOGE/BTC" → trading Dogecoin against Bitcoin
    async def get_price(self, symbol: str) -> float:
        ticker = await self.client.fetch_ticker(symbol)
        return ticker["last"]

    async def fetch_ohlcv(self, symbol: str, timeframe: str = "1m", since: int | None = None, limit: int = 30):
        """
        Fetch OHLCV candels and return: [timestamp, open, high, low, close, volume]
        - since: timestamp in milliseconds, optional
        - limit: number of candles
        """
        return await self.client.fetch_ohlcv(
            symbol, timeframe=timeframe,since=since, limit=limit
        )

    async def place_limit_buy(self, symbol: str, amount: float, price: float):
        return await self.client.create_limit_buy_order(symbol, amount, price)

    async def close(self):
        await self.client.close()
