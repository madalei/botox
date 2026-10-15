import pandas as pandas
from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel, PrivateAttr

from app.infrastructure.adapters.market_data_provider_interface import MarketDataProviderInterface
from app.models.order import Order
from app.services.logging import bot_logger


class RsiStrategy(BaseModel):
    """
    A mean-reversion strategy based on the RSI (Relative Strength Index).

    Buy when RSI drops below the oversold threshold  (default 30) — market is oversold, price likely to bounce up.
    Sell when RSI rises above the overbought threshold (default 70) — market is overbought, price likely to drop.

    This is the opposite philosophy to MA crossover:
    - MA crossover = trend following  (buy when already going up)
    - RSI           = mean reversion  (buy when everyone is selling)
    """

    # Parameters stored in DB
    name: str = "RSI"
    symbol: str = "BTC/EUR"
    timeframe: str = "1h"
    rsi_period: int = 14        # number of candles used to compute RSI (standard = 14)
    rsi_oversold: float = 30.0  # BUY  when RSI drops below this level
    rsi_overbought: float = 70.0  # SELL when RSI rises above this level
    risk_per_trade: float = 0.01
    stop_loss_pct: float = 0.02
    take_profit_pct: float = 0.04

    # | rsi_period | meaning                        |
    # | ---------- | ------------------------------ |
    # | 7          | fast, more signals, more noise |
    # | 14         | standard                       |
    # | 21         | slow, fewer but cleaner signals|
    #
    # | oversold / overbought | meaning                             |
    # | --------------------- | ----------------------------------- |
    # | 30 / 70               | standard                            |
    # | 25 / 75               | stricter — only extreme reversals   |
    # | 35 / 65               | more permissive — more trades       |

    # Internal runtime state (not stored in DB)
    _is_position_open: bool = PrivateAttr(default=False)
    _entry_price: float = PrivateAttr(default=0.0)
    _position_size: float = PrivateAttr(default=0.0)
    _last_signal: Optional[str] = PrivateAttr(default=None)
    _last_check_time: Optional[datetime] = PrivateAttr(default=None)

    def calculate_indicators(self, dataframe: pandas.DataFrame) -> pandas.DataFrame:
        """Compute RSI and add it as a column to the dataframe."""
        if len(dataframe) < self.rsi_period + 1:
            return dataframe

        # Price change between consecutive candles
        delta = dataframe['close'].diff()

        # Separate gains (positive changes) and losses (negative changes)
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        # Smooth averages over rsi_period using a rolling mean (Wilder's method)
        avg_gain = gain.rolling(window=self.rsi_period).mean()
        avg_loss = loss.rolling(window=self.rsi_period).mean()

        # RSI formula: 100 - (100 / (1 + RS)) where RS = avg_gain / avg_loss
        rs = avg_gain / avg_loss.replace(0, 1e-10)  # avoid division by zero
        dataframe['rsi'] = 100 - (100 / (1 + rs))

        return dataframe

    def calculate_position_size(self, capital: float, current_price: float) -> float:
        """
        position_size = amount of BTC to buy/sell
        amount_to_risk = capital × risk_per_trade  (e.g. 1000 × 0.01 = 10 EUR)
        position_size  = amount_to_risk / (price × stop_loss_pct)
        """
        amount_to_risk = capital * self.risk_per_trade
        return amount_to_risk / (current_price * self.stop_loss_pct)

    async def generate_signals(self, market_data: MarketDataProviderInterface, capital: float = 1000.0) -> Optional[Order]:
        """
        Fetch recent candles, compute RSI, and emit a BUY or SELL order if a signal is detected.
        """
        # Fetch enough candles for RSI to warm up (rsi_period × 3 gives a stable value)
        history_df = await market_data.get_history(self.symbol, self.timeframe, limit=self.rsi_period * 3)
        if history_df.empty:
            return None

        df = self.calculate_indicators(history_df)

        # Drop warmup rows where RSI is not yet computable (NaN)
        df = df.iloc[self.rsi_period:]
        if df.empty:
            return None

        last_row = df.iloc[-1]
        current_price = last_row['close']
        rsi = last_row['rsi']

        if pandas.isna(rsi):
            return None

        self._last_check_time = datetime.now()
        signal = None

        # BUY signal: RSI is oversold — market likely to bounce up
        if rsi < self.rsi_oversold:
            if not self._is_position_open:
                self._position_size = self.calculate_position_size(capital, current_price)
                self._entry_price = current_price
                self._is_position_open = True

                stop_loss = current_price * (1 - self.stop_loss_pct)
                take_profit = current_price * (1 + self.take_profit_pct)

                bot_logger.info(
                    f"BUY  | {self.symbol} | price={current_price:.2f}"
                    f" | amount={self._position_size:.6f}"
                    f" | sl={stop_loss:.2f} tp={take_profit:.2f}"
                    f" | RSI={rsi:.1f} < {self.rsi_oversold}"
                )

                signal = {
                    "type": "BUY",
                    "symbol": self.symbol,
                    "price": current_price,
                    "amount": self._position_size,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "timestamp": datetime.now().isoformat(),
                }
                self._last_signal = "BUY"
            else:
                bot_logger.info(
                    f"BUY signal skipped — position already open | {self.symbol} | RSI={rsi:.1f} | price={current_price:.2f}"
                )

        # SELL signal: RSI is overbought — market likely to drop
        elif rsi > self.rsi_overbought:
            if self._is_position_open:
                self._is_position_open = False
                pnl = (current_price - self._entry_price) * self._position_size

                bot_logger.info(
                    f"SELL | {self.symbol} | price={current_price:.2f}"
                    f" | amount={self._position_size:.6f}"
                    f" | entry={self._entry_price:.2f}"
                    f" | pnl={pnl:+.2f} {self.symbol.split('/')[1]}"
                    f" | RSI={rsi:.1f} > {self.rsi_overbought}"
                )

                signal = {
                    "type": "SELL",
                    "symbol": self.symbol,
                    "price": current_price,
                    "amount": self._position_size,
                    "timestamp": datetime.now().isoformat(),
                }
                self._last_signal = "SELL"
            else:
                bot_logger.info(
                    f"SELL signal skipped — no open position | {self.symbol} | RSI={rsi:.1f} | price={current_price:.2f}"
                )

        if signal:
            order = Order(
                bot_id="",
                symbol=signal["symbol"],
                side=signal["type"],
                amount=signal["amount"],
                price=signal["price"],
                created_at=datetime.now(),
            )
            if signal["type"] == "BUY":
                order.stop_loss = signal.get("stop_loss")
                order.take_profit = signal.get("take_profit")
            return order

        return None