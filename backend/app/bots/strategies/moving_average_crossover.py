import asyncio
import pandas as pandas  # convert OHLCV data (Open, High, Low, Close, Volume) into a pandas DataFrame
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, PrivateAttr

from app.infrastructure.adapters.market_data_provider_interface import MarketDataProviderInterface
from app.models.order import Order
from app.services.logging import bot_logger


class MovingAverageCrossoverStrategy(BaseModel):
    """
    A trading strategy based on moving average crossovers.
    Buy when the short moving average crosses above the long moving average.
    Sell when the short moving average crosses below the long moving average.
    """

    # TODO: the exchange platform (e.g. Coinbase) should be initialized in the strategy constructor
    #   and stored as an attribute, instead of being passed as a parameter to the generate_signals method.
    #   This way, the strategy is more self-contained and can be reused across different bots without needing to pass the exchange each time.

    # Parameters you want to store in JSONB
    name: str = "MovingAverageCrossoverStrategy"
    designation: str = "Default"
    symbol: str = "BTC/EUR"
    timeframe: str = "1h"
    short_window: int = 20 # avg of last 20 hours
    long_window: int = 50  # avg of last 50 hours
    risk_per_trade: float = 0.01
    stop_loss_pct: float = 0.02
    # 0 = pas de take profit : on laisse courir les gains (sortie par stop suiveur ou croisement baissier)
    take_profit_pct: float = 0.04
    # Trend filter: only BUY when the price is above the moving average of the last trend_window candles,
    # to skip the crossovers of a sideways or falling market. 0 = disabled.
    trend_window: int = 0
    # Stop suiveur : le stop loss remonte avec le prix, à trailing_stop_pct sous le plus haut atteint
    # depuis l'achat (ex. 0.05 = on vend si le prix redescend de 5 % depuis son plus haut). Il ne redescend jamais.
    # 0 = désactivé (stop loss fixe uniquement).
    trailing_stop_pct: float = 0.0
    # Mode d'achat :
    # - False (défaut) : achat uniquement sur la bougie du croisement haussier (la courte passe au-dessus de la longue).
    #   Après une vente, on attend le croisement suivant, même si la hausse continue.
    # - True : achat à n'importe quelle bougie où la courte est au-dessus de la longue (et au-dessus de la MA de
    #   tendance si trend_window), donc on rachète après un stop si la tendance est toujours haussière.
    buy_while_trend: bool = False
    # Vendre au croisement baissier (la courte repasse sous la longue). False = seuls le stop loss / stop suiveur
    # et le take profit ferment la position : utile avec un stop suiveur, pour laisser courir les gains.
    exit_on_crossover: bool = True

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

    # | timeframe | short MA | long MA | meaning           |
    # | --------- | -------- | ------- | ----------------- |
    # | `1h`      | 20       | 50      | 20h vs 50h trend  |
    # | `15m`     | 20       | 50      | 5h vs 12.5h trend |
    # | `4h`      | 20       | 50      | 80h vs 200h trend |

    # Internal runtime state (not stored in DB)
    _is_position_open: bool = PrivateAttr(default=False)
    _entry_price: float = PrivateAttr(default=0.0)
    _position_size: float = PrivateAttr(default=0.0)
    _last_signal: Optional[str] = PrivateAttr(default=None)
    _last_check_time: Optional[str] = PrivateAttr(default=None)

    _stop_loss: float = PrivateAttr(default=0.0)
    _take_profit: float = PrivateAttr(default=0.0)
    # Candle the position was opened on: its high/low happened (partly) before the entry
    _entry_candle_time: Optional[object] = PrivateAttr(default=None)
    # Plus haut prix atteint depuis l'achat, référence du stop suiveur
    _highest_price: float = PrivateAttr(default=0.0)

    # async def get_historical_data(self, exchange: CoinbaseAdapter, limit: int = 250) -> pandas.DataFrame:
    #     """
    #     Return a DataFrame containing historical market data of OHLCV (Open, High, Low, Close, Volume) for the
    #     configured trading symbol and timeframe.
    #
    # limit : int, optional (default=100)
    #     The maximum number of OHLCV candles to retrieve. The actual historical
    #     coverage depends on the configured timeframe. For example, with a
    #     timeframe of "1h" and limit=100, approximately 100 hours of historical
    #     data (~4.2 days) will be fetched.
    #     but 100 is not enought to get good statistic indicators, so better to use approximativelly 5* the long window
    #     limit = max(200, self.long_window * 5)
    #     This will make indicator more "mature" and steady
    # """
    #     try:
    #         since = exchange.milliseconds() - (limit * exchange.parse_timeframe(self.timeframe) * 1000) # if timeframe = 1h, limit * timeframe = 100 * 1h = 100h = 4.2days
    #         ohlcv = await exchange.fetch_ohlcv(self.symbol, self.timeframe, since, limit)
    #
    #         dataframe = pandas.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    #         dataframe['timestamp'] = pandas.to_datetime(dataframe['timestamp'], unit='ms')
    #         return dataframe
    #     except Exception as e:
    #         print(f"Error retrieving historical data: {e}")
    #         return pandas.DataFrame()

    @property
    def warmup_window(self) -> int:
        """Number of candles needed before every moving average is computable."""
        return max(self.long_window, self.trend_window)

    def calculate_indicators(self, dataframe: pandas.DataFrame) -> pandas.DataFrame:
        """Calculates technical indicators for the strategy."""
        if len(dataframe) < self.warmup_window:
            return dataframe

        if self.trend_window:
            dataframe['trend_ma'] = dataframe['close'].rolling(window=self.trend_window).mean()

        # Calculate moving averages
        # note: .rolling(n) -> Crée une fenetre glissante de n bougies
        # À chaque ligne t, on regarde les N dernières valeurs de `close`
        # On calcule ensuite la moyenne de ces N valeurs
        dataframe['short_ma'] = dataframe['close'].rolling(window=self.short_window).mean()
        dataframe['long_ma'] = dataframe['close'].rolling(window=self.long_window).mean()

        # Crossover signal: +1 when short > long (uptrend), -1 when short < long (downtrend)
        # diff() produces +2 on upward cross, -2 on downward cross
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

    def _stop_loss_exit_price(self, last_row) -> Optional[float]:
        """
        Price at which the stop loss is hit during the last candle, or None.
        Uses the candle low, not only the close, so a drop through the stop within the candle is caught.
        Exits at the stop level, or at the open if the candle opened below it (price gap).
        On the entry candle the low may predate the entry: only the current price is used.
        """
        if last_row.get('timestamp') == self._entry_candle_time:
            return last_row['close'] if last_row['close'] <= self._stop_loss else None
        if last_row['low'] <= self._stop_loss:
            return min(last_row['open'], self._stop_loss)
        return None

    def _take_profit_exit_price(self, last_row) -> Optional[float]:
        """Same as _stop_loss_exit_price with the candle high: exits at the take profit, or at the open if above."""
        if not self._take_profit:  # take_profit_pct = 0 : pas de take profit
            return None
        if last_row.get('timestamp') == self._entry_candle_time:
            return last_row['close'] if last_row['close'] >= self._take_profit else None
        if last_row['high'] >= self._take_profit:
            return max(last_row['open'], self._take_profit)
        return None

    def _update_trailing_stop(self, last_row):
        """
        Remonte le stop loss sous le plus haut prix atteint depuis l'achat.
        Appelé après la vérification des sorties : dans une même bougie on ne sait pas si le plus haut
        est arrivé avant ou après le plus bas, donc le nouveau stop ne s'applique qu'à partir de la bougie suivante.
        """
        # Sur la bougie d'achat, le plus haut a pu avoir lieu avant l'achat : on ne prend que la clôture
        if last_row.get('timestamp') == self._entry_candle_time:
            candle_high = last_row['close']
        else:
            candle_high = last_row['high']
        self._highest_price = max(self._highest_price, candle_high)
        # Le stop ne fait que monter : jamais en dessous du stop loss initial ni du stop précédent
        self._stop_loss = max(self._stop_loss, self._highest_price * (1 - self.trailing_stop_pct))

    def _close_position(self, current_price: float, reason: str, extra_log: str = "") -> Dict:
        self._is_position_open = False
        pnl = (current_price - self._entry_price) * self._position_size
        bot_logger.info(
            f"SELL ({reason}) | {self.symbol} | price={current_price:.2f}"
            f" | amount={self._position_size:.6f}"
            f" | pnl={pnl:+.2f} {self.symbol.split('/')[1]}"
            + extra_log
        )
        self._last_signal = "SELL"
        return {
            "type": "SELL",
            "symbol": self.symbol,
            "price": current_price,
            "amount": self._position_size,
            "timestamp": datetime.now().isoformat()
        }

    def calculate_position_size(self, capital: float, current_price: float) -> float:
        """Calculates position size based on capital and risk
        amount_to_spend = capital × risk_per_trade  (ex: 1000 × 0.01 = 10 EUR)
        position_size   = amount_to_spend / price   (ex: 10 / 70000 = 0.000142 BTC)
        """
        amount_to_spend = capital * self.risk_per_trade
        return amount_to_spend / current_price

    async def generate_signals(self, market_data: MarketDataProviderInterface, capital: float = 1000.0) -> Optional[Dict]:
        """
        Analyzes data and generates trading signals.
        Returns an order to execute if a signal is detected.
        """
        # ~5× the long window lets the indicators settle; the trend MA needs at least trend_window candles.
        # Coinbase returns at most 300 candles per request: long_window=50 + trend_window=200 fits.
        limit = max(self.long_window * 5, self.trend_window + self.long_window)
        history_df = await market_data.get_history(self.symbol, self.timeframe, limit=limit)
        if history_df.empty:
            return None

        # Calculate indicators
        df = self.calculate_indicators(history_df)

        # Drop warmup rows where the long MA is not yet computable (NaN)
        df = df.iloc[self.warmup_window:] # supprime les premières lignes où long_ma (ou trend_ma) est NaN sinon la prochaine ligne ne passe pas

        if df.empty:
            return None

        # Read the latest candle
        last_row = df.iloc[-1]
        last_crossover = last_row['crossover']
        current_price = last_row['close']
        short_ma = last_row['short_ma']
        long_ma = last_row['long_ma']

        self._last_check_time = datetime.now()
        signal = None

        # Priority: check SL/TP before crossover signals.
        # If both were touched in the same candle we can't know which came first: assume the stop loss (worst case).
        stop_loss_price = self._stop_loss_exit_price(last_row) if self._is_position_open else None
        take_profit_price = self._take_profit_exit_price(last_row) if self._is_position_open else None

        if stop_loss_price is not None:
            # Stop au-dessus du stop initial = il a été remonté par le stop suiveur
            initial_stop = self._entry_price * (1 - self.stop_loss_pct)
            reason = "trailing-stop" if self._stop_loss > initial_stop else "stop-loss"
            signal = self._close_position(
                stop_loss_price, reason, f" | sl={self._stop_loss:.2f} | highest={self._highest_price:.2f}"
            )

        elif take_profit_price is not None:
            signal = self._close_position(take_profit_price, "take-profit", f" | tp={self._take_profit:.2f}")

        # Buy signal: short MA just crossed above long MA (Upward crossing, from -1 to 1),
        # ou, avec buy_while_trend, n'importe quelle bougie où la courte est au-dessus de la longue sans position ouverte
        elif last_crossover == 2 or (self.buy_while_trend and last_row['signal'] == 1 and not self._is_position_open):
            if self.trend_window and current_price <= last_row['trend_ma']:
                # En mode buy_while_trend, ne loguer que les croisements pour ne pas loguer à chaque bougie
                if last_crossover == 2:
                    bot_logger.info(
                        f"BUY signal skipped — price below trend MA | {self.symbol} | price={current_price:.2f}"
                        f" | trend_ma={last_row['trend_ma']:.2f}"
                    )
            elif not self._is_position_open:
                self._position_size = self.calculate_position_size(capital, current_price)
                self._entry_price = current_price
                self._entry_candle_time = last_row.get('timestamp')
                self._highest_price = current_price
                self._is_position_open = True

                stop_loss = current_price * (1 - self.stop_loss_pct)
                # Pas de take profit si take_profit_pct = 0 : on laisse courir les gains
                take_profit = current_price * (1 + self.take_profit_pct) if self.take_profit_pct else None

                self._stop_loss = stop_loss
                self._take_profit = take_profit

                bot_logger.info(
                    f"BUY  | {self.symbol} | price={current_price:.2f}"
                    f" | amount={self._position_size:.6f}"
                    f" | sl={stop_loss:.2f} tp={f'{take_profit:.2f}' if take_profit else 'none'}"
                    f" | trailing={self.trailing_stop_pct:.1%}"
                    f" | short_ma={short_ma:.2f} long_ma={long_ma:.2f}"
                )

                signal = {
                    "type": "BUY",
                    "symbol": self.symbol,
                    "price": current_price,
                    "amount": self._position_size,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "timestamp": datetime.now().isoformat()
                }

                self._last_signal = "BUY"
            else:
                bot_logger.info(
                    f"BUY signal skipped — position already open | {self.symbol} | price={current_price:.2f}"
                )

        # Sell signal: short MA just crossed below long MA (only if SL/TP didn't already fire)
        elif last_crossover == -2 and self.exit_on_crossover:  # Downward crossing (from 1 to -1)
            if self._is_position_open:
                signal = self._close_position(
                    current_price, "MA crossover",
                    f" | entry={self._entry_price:.2f} | short_ma={short_ma:.2f} long_ma={long_ma:.2f}"
                )
            else:
                bot_logger.info(
                    f"SELL signal skipped — no open position | {self.symbol} | price={current_price:.2f}"
                )

        # Position toujours ouverte après cette bougie : on remonte le stop suiveur
        if self._is_position_open and self.trailing_stop_pct:
            self._update_trailing_stop(last_row)

        # Create an order if a signal was generated
        if signal:
            order = Order(
                bot_id="",
                symbol=signal["symbol"],
                side=signal["type"],
                amount=signal["amount"],
                price=signal["price"],
                created_at=datetime.now()
            )

            # If it's a buy, add stop loss and take profit
            if signal["type"] == "BUY":
                order.stop_loss = signal.get("stop_loss")
                order.take_profit = signal.get("take_profit")

            return order

        return None
