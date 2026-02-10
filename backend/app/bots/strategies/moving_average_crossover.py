import asyncio
import pandas as pandas  # convert OHLCV data (Open, High, Low, Close, Volume) into a pandas DataFrame
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
    short_window: int = 20 # avg of last 20 hours
    long_window: int = 50  # avg of last 50 hours
    risk_per_trade: float = 0.01
    stop_loss_pct: float = 0.02
    take_profit_pct: float = 0.04

    # Example of other values:
    # -- Strategy --
    # More aggressive (more trades) (/!\ faux signaux)
    #   short_window = 9
    #   long_window = 21
    # Less trades
    #   short_window = 50
    #   long_window = 200
    #
    # -- Risk --
    # Prudent:
    #   risk_per_trade = 0.005   # 0.5%
    #   stop_loss_pct  = 0.015   # 1.5%
    #   take_profit_pct= 0.03    # 3%
    # Agressif:
    #   risk_per_trade = 0.02
    #   stop_loss_pct = 0.025
    #   take_profit_pct = 0.06


    # Internal runtime state (not stored in DB)
    _is_position_open: bool = PrivateAttr(default=False)
    _entry_price: float = PrivateAttr(default=0.0)
    _position_size: float = PrivateAttr(default=0.0)
    _last_signal: Optional[str] = PrivateAttr(default=None)
    _last_check_time: Optional[str] = PrivateAttr(default=None)


    async def get_historical_data(self, exchange: BinanceAdapter, limit: int = 250) -> pandas.DataFrame:
        """
        Return a DataFrame containing historical market data of OHLCV (Open, High, Low, Close, Volume) for the
        configured trading symbol and timeframe.

    limit : int, optional (default=100)
        The maximum number of OHLCV candles to retrieve. The actual historical
        coverage depends on the configured timeframe. For example, with a
        timeframe of "1h" and limit=100, approximately 100 hours of historical
        data (~4.2 days) will be fetched.
        but 100 is not enought to get good statistic indicators, so better to use approximativelly 5* the long window
        limit = max(200, self.long_window * 5)
        This will make indicator more "mature" and steady
    """
        try:
            since = exchange.milliseconds() - (limit * exchange.parse_timeframe(self.timeframe) * 1000) # if timeframe = 1h, limit * timeframe = 100 * 1h = 100h = 4.2days
            ohlcv = await exchange.fetch_ohlcv(self.symbol, self.timeframe, since, limit)

            dataframe = pandas.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            dataframe['timestamp'] = pandas.to_datetime(dataframe['timestamp'], unit='ms')
            return dataframe
        except Exception as e:
            print(f"Error retrieving historical data: {e}")
            return pandas.DataFrame()

    def calculate_indicators(self, dataframe: pandas.DataFrame) -> pandas.DataFrame:
        """Calculates technical indicators for the strategy."""
        if len(dataframe) < self.long_window:
            return dataframe

        # Calculate moving averages
        # note: .rolling(n) -> Crée une fenetre glissante de n bougies
        # À chaque ligne t, on regarde les N dernières valeurs de `close`
        # On calcule ensuite la moyenne de ces N valeurs
        dataframe['short_ma'] = dataframe['close'].rolling(window=self.short_window).mean()
        dataframe['long_ma'] = dataframe['close'].rolling(window=self.long_window).mean()

        # Calculate signal
        dataframe['signal'] = 0
        # if short avg > long avg => price is increasing
        # dataframe.loc[condition_lines, column] = x => assign value x to line that validate the condition
        dataframe.loc[dataframe['short_ma'] > dataframe['long_ma'], 'signal'] = 1
        dataframe.loc[dataframe['short_ma'] < dataframe['long_ma'], 'signal'] = -1

        # Detect crossovers (signal change)
        # .diff: calc difference between 2 consecutive lines
        # signal = [-1  -1   1   1]
        # diff() = [ 0   0   2   0]
        # +2 => buy signal
        # -2 => sell signal
        dataframe['crossover'] = dataframe['signal'].diff().fillna(0)

        return dataframe

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
        history_df = await self.get_historical_data(exchange, limit=self.long_window * 5)
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
