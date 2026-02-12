import ccxt
import ccxt.async_support as ccxt_async

from app.models.order import Order
from app.services.logging import bot_logger


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

    async def close(self):
        await self.client.close()

    async def place_market_buy(self, symbol: str, amount: float):
        """Place a market buy order for the given symbol and amount.
        :param symbol: The trading pair symbol, e.g., "BTC/USDT"
        :param amount: The amount of BTC to buy, e.g., 0.0001 for 0.0001 BTC"""

        try:
            bot_logger.info(
                f"Placing MARKET BUY | symbol={symbol} | raw_amount={amount}"
            )
            # Ensure markets are loaded
            await self.client.load_markets()

            # Adjust precision
            amount = self.client.amount_to_precision(symbol, amount)

            bot_logger.info(
                f"Adjusted amount to precision: {amount}"
            )
            order = await self.client.create_market_buy_order(symbol, amount)

            bot_logger.info(
                f"MARKET BUY SUCCESS | id={order.get('id')} "
                f"| filled={order.get('filled')} "
                f"| avg_price={order.get('average')} "
                f"| status={order.get('status')}"
            )
            return order

        except ccxt.InsufficientFunds as e:
            bot_logger.error(
                f"MARKET BUY FAILED - Insufficient Funds | "
                f"symbol={symbol} | amount={amount} | error={str(e)}"
            )
            raise
        except ccxt.InvalidOrder as e:
            bot_logger.error(
                f"MARKET BUY FAILED - Invalid Order | "
                f"symbol={symbol} | amount={amount} | error={str(e)}"
            )
            raise
        except ccxt.ExchangeError as e:
            bot_logger.error(
                f"MARKET BUY FAILED - Exchange Error | "
                f"symbol={symbol} | error={str(e)}"
            )
            raise
        except Exception as e:
            bot_logger.exception(
                f"MARKET BUY FAILED - Unexpected Error | "
                f"symbol={symbol} | error={str(e)}"
            )
            raise


    async def place_market_sell(self, symbol: str, amount: float):
        try:
            bot_logger.info(f"Placing MARKET SELL | symbol={symbol} | raw_amount={amount}")

            # Ensure markets are loaded
            await self.client.load_markets()

            # Adjust precision
            amount = self.client.amount_to_precision(symbol, amount)

            bot_logger.info(f"Adjusted amount to precision: {amount}")

            order = await self.client.create_market_sell_order(symbol, amount)

            bot_logger.info(
                f"MARKET SELL SUCCESS | id={order.get('id')} "
                f"| filled={order.get('filled')} "
                f"| avg_price={order.get('average')} "
                f"| status={order.get('status')}"
            )

            return order

        except ccxt.InsufficientFunds as e:
            bot_logger.error(f"MARKET SELL FAILED - Insufficient Funds | "f"symbol={symbol} | amount={amount} | error={str(e)}")
            raise
        except ccxt.InvalidOrder as e:
            bot_logger.error(
                f"MARKET SELL FAILED - Invalid Order | "
                f"symbol={symbol} | amount={amount} | error={str(e)}"
            )
            raise
        except ccxt.ExchangeError as e:
            bot_logger.error(
                f"MARKET SELL FAILED - Exchange Error | "
                f"symbol={symbol} | error={str(e)}"
            )
            raise
        except Exception as e:
            bot_logger.exception(
                f"MARKET SELL FAILED - Unexpected Error | "
                f"symbol={symbol} | error={str(e)}"
            )
            raise

    async def place_limit_buy(self, symbol: str, amount: float, price: float):
        return await self.client.create_limit_buy_order(symbol, amount, price)

    async def place_limit_sell(self, symbol: str, amount: float, price: float):
        return await self.client.create_limit_sell_order(symbol, amount, price)
