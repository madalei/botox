from abc import ABC, abstractmethod

class BaseStrategy(ABC):
    def __init__(self, params: dict):
        self.params = params

    @abstractmethod
    async def compute_signal(self, market_data: dict) -> dict:
        """
        Returns dict with action info, e.g.,
        {"side": "buy", "amount": 1.2}
        """
        pass
