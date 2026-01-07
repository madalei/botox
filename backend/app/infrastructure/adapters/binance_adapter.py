import ccxt

class BinanceAdapter:
    def __init__(self, api_key: str, secret: str, sandbox: bool = True):
        self.client = ccxt.binance({
            'apiKey': api_key,
            'secret': secret,
        })
        self.client.set_sandbox_mode(sandbox)

    # @param symbol
    #   "BTC/USDT" → trading Bitcoin against Tether
    #   "ETH/EUR" → trading Ethereum against euros
    #   "DOGE/BTC" → trading Dogecoin against Bitcoin
    def get_price(self, symbol: str) -> float:
        ticker = self.client.fetch_ticker(symbol)
        return ticker['last']

    def get_ohlcv(self, symbol: str, timeframe: str = '1m', limit: int = 30):
        """
        Récupère les chandeliers OHLCV : [timestamp, open, high, low, close, volume]
        """
        return self.client.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)

    def place_limit_buy(self, symbol: str, amount: float, price: float):
        return self.client.create_limit_buy_order(symbol, amount, price)

