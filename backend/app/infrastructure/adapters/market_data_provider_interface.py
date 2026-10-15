from abc import ABC, abstractmethod
import pandas as pd


class MarketDataProviderInterface(ABC):
    """
    Abstract interface for market data.
    Can be backed by live exchange data or historical data.
    """

    @abstractmethod
    async def get_history(self, symbol: str, timeframe: str, limit) -> pd.DataFrame:
        """
        Return historical OHLCV data as a DataFrame.
        """
        pass

    @abstractmethod
    def get_price(self, symbol: str) -> float:
        """
        Return the latest price.
        """
        pass

    @abstractmethod
    def tick(self) -> bool:
        """
        Advance to the next candle.
        Returns False when no more data is available.
        """
        pass

    async def get_free_balance(self, currency: str) -> float | None:
        """
        Solde disponible (non bloqué dans un ordre) de la devise, ex. "EUR".
        None = pas de solde réel (paper trading, backtest) : le bot utilise alors son capital fixe.
        """
        return None
