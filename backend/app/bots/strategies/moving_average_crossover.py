import asyncio
import pandas as pd  # convert OHLCV data (Open, High, Low, Close, Volume) into a pandas DataFrame
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, PrivateAttr

from app.infrastructure.adapters.binance_adapter import BinanceAdapter
from app.models.order import Order


class MovingAverageCrossoverStrategy(BaseModel):
    """
    A trading strategy based on moving average crossovers.
    Buy when the short moving average crosses above the long moving average.
    Sell when the short moving average crosses below the long moving average.
    """

    # Parameters you want to store in JSONB
    name: str = "MovingAVG-crossOver"
    symbol: str = "BTC/USDT"
    timeframe: str = "1h"
    short_window: int = 20
    long_window: int = 50
    risk_per_trade: float = 0.01
    stop_loss_pct: float = 0.02
    take_profit_pct: float = 0.04

    # Internal runtime state (not stored in DB)
    _is_position_open: bool = PrivateAttr(default=False)
    _entry_price: float = PrivateAttr(default=0.0)
    _position_size: float = PrivateAttr(default=0.0)
    _last_signal: Optional[str] = PrivateAttr(default=None)
    _last_check_time: Optional[str] = PrivateAttr(default=None)


    async def get_historical_data(self, exchange: BinanceAdapter, limit: int = 100) -> pd.DataFrame:
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

    async def generate_signals(self, exchange: BinanceAdapter, capital: float = 1000.0) -> Optional[Dict]:
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
        # todo replace "order" by "trade"
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
