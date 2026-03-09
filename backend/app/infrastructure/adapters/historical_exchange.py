import pandas as pd
from .market_data_provider_interface import MarketDataProviderInterface


class HistoricalExchange(MarketDataProviderInterface):
    def __init__(self, dataframe: pd.DataFrame):
        self.df = dataframe.reset_index(drop=True)
        self.cursor = 0

    def tick(self) -> bool:
        if self.cursor < len(self.df):
            self.cursor += 1
            return True
        return False

    async def get_history(self, symbol: str, timeframe: str, limit=None) -> pd.DataFrame:
        # replace fetch_ohlcv(...) in binance adapter
        # Time simulated with cursor
        df = self.df.iloc[:self.cursor]

        if limit:
            return df.tail(limit).copy()

        return df.copy()

    def get_price(self, symbol: str) -> float:
        return float(self.df.iloc[self.cursor - 1]["close"])