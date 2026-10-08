from app.config import SUPPORTED_EXCHANGES, Settings
from app.infrastructure.adapters.binance_adapter import BinanceAdapter
from app.infrastructure.adapters.coinbase_adapter import CoinbaseAdapter


def create_exchange(settings: Settings) -> BinanceAdapter | CoinbaseAdapter:
    """
    Build the live exchange adapter selected by the EXCHANGE env var.
    - coinbase: sandbox=True → paper trading (live prices, simulated orders)
    - binance:  sandbox=True → orders sent to the Binance testnet
    """
    if settings.exchange == "coinbase":
        return CoinbaseAdapter(
            api_key=settings.coinbase_keys.api_key,
            secret=settings.coinbase_keys.secret,
            sandbox=settings.sandbox_mode
        )
    if settings.exchange == "binance":
        return BinanceAdapter(
            api_key=settings.binance_keys.api_key,
            secret=settings.binance_keys.secret,
            sandbox=settings.sandbox_mode
        )
    raise ValueError(f"Unsupported EXCHANGE '{settings.exchange}', expected one of {SUPPORTED_EXCHANGES}")
