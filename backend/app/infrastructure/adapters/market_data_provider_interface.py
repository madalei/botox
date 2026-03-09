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