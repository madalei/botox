import asyncio
import pandas as pd  # convert OHLCV data (Open, High, Low, Close, Volume) into a pandas DataFrame
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from core.models.order import Order


class MovingAverageCrossoverStrategy:
    """
    A trading strategy based on moving average crossovers.
    Buy when the short moving average crosses above the long moving average.
    Sell when the short moving average crosses below the long moving average.
    """

    def __init__(
            self,
            symbol: str = "BTC/USDT",
            timeframe: str = "1h",
            short_window: int = 20,
            long_window: int = 50,
            risk_per_trade: float = 0.01,  # 1% of capital per trade
            stop_loss_pct: float = 0.02,  # 2% stop loss
            take_profit_pct: float = 0.04,  # 4% take profit
    ):
        self.symbol = symbol
        self.timeframe = timeframe
        self.short_window = short_window
        self.long_window = long_window
        self.risk_per_trade = risk_per_trade
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct

        # Internal state of the strategy
        self.is_position_open = False
        self.entry_price = 0.0
        self.position_size = 0.0
        self.last_signal = None
        self.last_check_time = None

    async def get_historical_data(self, exchange, limit: int = 100) -> pd.DataFrame:
        """Retrieves historical data needed for the strategy."""
        try:
            since = exchange.milliseconds() - (limit * exchange.parse_timeframe(self.timeframe) * 1000)
            ohlcv = await exchange.fetch_ohlcv(self.symbol, self.timeframe, since, limit)

            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            print(f"Error retrieving historical data: {e}")
            return pd.DataFrame()

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculates technical indicators for the strategy."""
        if len(df) < self.long_window:
            return df

        # Calculate moving averages
        df['short_ma'] = df['close'].rolling(window=self.short_window).mean()
        df['long_ma'] = df['close'].rolling(window=self.long_window).mean()

        # Calculate signal
        df['signal'] = 0
        df.loc[df['short_ma'] > df['long_ma'], 'signal'] = 1
        df.loc[df['short_ma'] < df['long_ma'], 'signal'] = -1

        # Detect crossovers (signal change)
        df['crossover'] = df['signal'].diff().fillna(0)

        return df

    def calculate_position_size(self, capital: float, current_price: float) -> float:
        """Calculates position size based on capital and risk."""
        amount_to_risk = capital * self.risk_per_trade
        position_size = amount_to_risk / (current_price * self.stop_loss_pct)
        return position_size

    async def generate_signals(self, exchange, capital: float = 1000.0) -> Optional[Dict]:
        """
        Analyzes data and generates trading signals.
        Returns an order to execute if a signal is detected.
        """
        # Get enough historical data
        history_df = await self.get_historical_data(exchange, limit=self.long_window + 10)
        if history_df.empty:
            return None

        # Calculate indicators
        df = self.calculate_indicators(history_df)

        # Check if there's enough data to generate a valid signal
        if df['short_ma'].isna().sum() > 0 or df['long_ma'].isna().sum() > 0:
            return None

        # Observe the last crossover
        last_row = df.iloc[-1]
        last_crossover = last_row['crossover']
        current_price = last_row['close']

        # Update state
        self.last_check_time = datetime.now()

        signal = None

        # Buy signal: short MA just crossed above long MA
        if last_crossover == 2:  # Upward crossing (from -1 to 1)
            if not self.is_position_open:
                self.position_size = self.calculate_position_size(capital, current_price)
                self.entry_price = current_price
                self.is_position_open = True

                signal = {
                    "type": "BUY",
                    "symbol": self.symbol,
                    "price": current_price,
                    "amount": self.position_size,
                    "stop_loss": current_price * (1 - self.stop_loss_pct),
                    "take_profit": current_price * (1 + self.take_profit_pct),
                    "timestamp": datetime.now().isoformat()
                }

                self.last_signal = "BUY"

        # Sell signal: short MA just crossed below long MA
        elif last_crossover == -2:  # Downward crossing (from 1 to -1)
            if self.is_position_open:
                self.is_position_open = False

                signal = {
                    "type": "SELL",
                    "symbol": self.symbol,
                    "price": current_price,
                    "amount": self.position_size,
                    "timestamp": datetime.now().isoformat()
                }

                self.last_signal = "SELL"

        # Create an order if a signal was generated
        if signal:
            order = Order(
                id=None,  # ID will be generated by the database
                symbol=signal["symbol"],
                side=signal["type"],
                amount=signal["amount"],
                price=signal["price"],
                status="NEW",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )

            # If it's a buy, add stop loss and take profit
            if signal["type"] == "BUY":
                order.stop_loss = signal["stop_loss"]
                order.take_profit = signal["take_profit"]

            return order

        return None

    async def run(self, exchange, capital: float = 1000.0, check_interval: int = 900):
        """
        Runs the strategy continuously with a specified check interval.
        By default, checks every 15 minutes (900 seconds).
        """
        print(f"Starting moving average crossover strategy for {self.symbol}...")
        print(f"Timeframe: {self.timeframe}, Short MA: {self.short_window}, Long MA: {self.long_window}")

        while True:
            try:
                # Generate signals
                order = await self.generate_signals(exchange, capital)

                # If an order is generated
                if order:
                    print(f"Signal detected: {order.side} {order.amount} {order.symbol} at {order.price}")
                    # Here you could call your order service or repository
                    # await order_service.create_order(order)
                else:
                    print(f"No signal generated at {datetime.now()}")

                # Wait for the specified interval before the next check
                await asyncio.sleep(check_interval)

            except Exception as e:
                print(f"Error in strategy execution: {e}")
                await asyncio.sleep(check_interval)