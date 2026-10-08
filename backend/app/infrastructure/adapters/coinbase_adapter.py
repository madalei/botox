import uuid

import ccxt
import ccxt.async_support as ccxt_async
import pandas as pd

from app.infrastructure.adapters.market_data_provider_interface import MarketDataProviderInterface
from app.services.logging import bot_logger


class CoinbaseAdapter(MarketDataProviderInterface):
    """
    Coinbase Advanced Trade adapter (via ccxt).

    Coinbase has no testnet. When `sandbox=True`, the adapter runs in paper trading mode:
    market data comes from the live Coinbase API, but orders are only simulated and logged,
    never sent to the exchange.

    Credentials are a Coinbase Developer Platform (CDP) API key:
    - api_key: the key name, e.g. "organizations/{org_id}/apiKeys/{key_id}"
    - secret:  the ECDSA private key, e.g. "-----BEGIN EC PRIVATE KEY-----\n...\n-----END EC PRIVATE KEY-----\n"
    """

    def __init__(self, api_key: str | None, secret: str | None, sandbox: bool = True):
        self.client = ccxt_async.coinbase({
            "apiKey": api_key,
            "secret": secret,
            "enableRateLimit": True,
        })
        self.paper_trading = sandbox

    def milliseconds(self) -> int:
        return self.client.milliseconds() # cctx.milliseconds

    def parse_timeframe(self, timeframe: str) -> int:
        return self.client.parse_timeframe(timeframe)

    def tick(self) -> bool:
        # Live data always advances
        return True

    async def get_history(self, symbol: str, timeframe: str, limit: int = 250) -> pd.DataFrame:
        """
            Return a DataFrame containing historical market data of OHLCV (Open, High, Low, Close, Volume) for the
            configured trading symbol and timeframe.
            - Calls Coinbase API
            - Downloads candles
            - Converts to a dataframe

            limit : int, optional (default=250)
                The maximum number of OHLCV candles to retrieve. The actual historical
                coverage depends on the configured timeframe. For example, with a
                timeframe of "1h" and limit=100, approximately 100 hours of historical
                data (~4.2 days) will be fetched.
                but 100 is not enought to get good statistic indicators, so better to use approximativelly 5* the long window
                limit = max(200, self.long_window * 5)
                This will make indicator more "mature" and steady
                /!\\ Coinbase returns at most 300 candles per request.
            timeframe : str
                Coinbase supports: 1m, 5m, 15m, 30m, 1h, 2h, 6h, 1d (no 4h)
        """
        try:
            since = self.milliseconds() - (limit * self.parse_timeframe(timeframe) * 1000)  # if timeframe = 1h, limit * timeframe = 100 * 1h = 100h = 4.2days

            ohlcv = await self.fetch_ohlcv(symbol=symbol, timeframe=timeframe, since=since, limit=limit)

            dataframe = pd.DataFrame(
                ohlcv,
                columns=["timestamp", "open", "high", "low", "close", "volume"],
            )
            dataframe["timestamp"] = pd.to_datetime(dataframe["timestamp"], unit="ms")
            return dataframe

        except Exception as e:
            print(f"Error retrieving historical data: {e}")
            return pd.DataFrame()

    # @param symbol
    #   "BTC/EUR"  → trading Bitcoin against euros
    #   "BTC/USDC" → trading Bitcoin against USD Coin (MiCA compliant stablecoin, USDT is not available in the EEA)
    #   "ETH/BTC"  → trading Ethereum against Bitcoin
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

    async def _simulate_market_order(self, side: str, symbol: str, amount: float) -> dict:
        """Paper trading: build a fake filled order at the current market price, nothing is sent to Coinbase."""
        price = await self.get_price(symbol)
        order = {
            "id": f"paper-{uuid.uuid4()}",
            "symbol": symbol,
            "type": "market",
            "side": side,
            "amount": amount,
            "filled": amount,
            "average": price,
            "cost": amount * price,
            "status": "closed",
        }
        bot_logger.info(
            f"PAPER MARKET {side.upper()} | id={order['id']} | symbol={symbol} "
            f"| amount={amount} | price={price}"
        )
        return order

    async def place_market_buy(self, symbol: str, amount: float):
        """Place a market buy order for the given symbol and amount.
        :param symbol: The trading pair symbol, e.g., "BTC/EUR"
        :param amount: The amount of BTC to buy, e.g., 0.0001 for 0.0001 BTC"""

        try:
            bot_logger.info(f"Placing MARKET BUY | symbol={symbol} | raw_amount={amount}"
                            )
            # Ensure markets are loaded
            await self.client.load_markets()

            # Adjust precision
            amount = self.client.amount_to_precision(symbol, amount)

            bot_logger.info(f"Adjusted amount to precision: {amount}")

            if self.paper_trading:
                return await self._simulate_market_order("buy", symbol, float(amount))

            # Coinbase market buys are expressed in quote currency (cost to spend),
            # so ccxt needs the current price to convert the BTC amount into a cost
            price = await self.get_price(symbol)
            order = await self.client.create_market_buy_order(symbol, amount, params={"price": price})

            bot_logger.info(
                f"MARKET BUY SUCCESS | id={order.get('id')} "
                f"| filled={order.get('filled')} "
                f"| avg_price={order.get('average')} "
                f"| status={order.get('status')}"
            )
            return order

        except ccxt.InsufficientFunds as e:
            bot_logger.error(f"MARKET BUY FAILED - Insufficient Funds | "f"symbol={symbol} | amount={amount} | error={str(e)}")
            raise
        except ccxt.InvalidOrder as e:
            bot_logger.error(f"MARKET BUY FAILED - Invalid Order | "f"symbol={symbol} | amount={amount} | error={str(e)}")
            raise
        except ccxt.ExchangeError as e:
            bot_logger.error(f"MARKET BUY FAILED - Exchange Error | "f"symbol={symbol} | error={str(e)}")
            raise
        except Exception as e:
            bot_logger.exception(f"MARKET BUY FAILED - Unexpected Error | "f"symbol={symbol} | error={str(e)}")
            raise


    async def place_market_sell(self, symbol: str, amount: float):
        try:
            bot_logger.info(f"Placing MARKET SELL | symbol={symbol} | raw_amount={amount}")

            # Ensure markets are loaded
            await self.client.load_markets()

            # Adjust precision
            amount = self.client.amount_to_precision(symbol, amount)

            bot_logger.info(f"Adjusted amount to precision: {amount}")

            if self.paper_trading:
                return await self._simulate_market_order("sell", symbol, float(amount))

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
            bot_logger.error(f"MARKET SELL FAILED - Invalid Order | "f"symbol={symbol} | amount={amount} | error={str(e)}")
            raise
        except ccxt.ExchangeError as e:
            bot_logger.error(f"MARKET SELL FAILED - Exchange Error | "f"symbol={symbol} | error={str(e)}")
            raise
        except Exception as e:
            bot_logger.exception(f"MARKET SELL FAILED - Unexpected Error | "f"symbol={symbol} | error={str(e)}")
            raise

    async def place_limit_buy(self, symbol: str, amount: float, price: float):
        if self.paper_trading:
            raise NotImplementedError("Limit orders are not simulated in paper trading mode")
        return await self.client.create_limit_buy_order(symbol, amount, price)

    async def place_limit_sell(self, symbol: str, amount: float, price: float):
        if self.paper_trading:
            raise NotImplementedError("Limit orders are not simulated in paper trading mode")
        return await self.client.create_limit_sell_order(symbol, amount, price)
