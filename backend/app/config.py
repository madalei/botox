from dotenv import load_dotenv
import os
from pydantic_settings import BaseSettings
from pydantic import BaseModel

load_dotenv()  # Charge .env


class APIKeyPair(BaseModel):
    api_key: str
    secret: str


SUPPORTED_EXCHANGES = ("coinbase", "binance")


class Settings(BaseSettings):
    # Exchange used by all bots, picked at startup: "coinbase" or "binance"
    exchange: str = os.getenv("EXCHANGE", "coinbase").lower()
    sandbox_mode: bool = os.getenv("USE_SANDBOX", "False") == "True"
    environment: str = os.getenv("ENVIRONMENT", "development")
    root_path: str = os.getenv("ROOT_PATH", "")
    # Comma-separated list of frontend origins allowed to call the API (default: Vite dev server)
    cors_origins: list[str] = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
        if origin.strip()
    ]

    @property
    def coinbase_keys(self) -> APIKeyPair:
        """
        Coinbase Developer Platform (CDP) API key, created at https://portal.cdp.coinbase.com/access/api
        (choose the ECDSA signature algorithm, Ed25519 is not supported by Advanced Trade).
        Coinbase has no testnet: in sandbox mode the same key is used, but orders are only simulated (paper trading).
        The private key is multi-line, in .env store it on one line with "\\n" separators.
        """
        return APIKeyPair(
            api_key=os.getenv("COINBASE_API_KEY_NAME", ""),
            secret=os.getenv("COINBASE_API_PRIVATE_KEY", "").replace("\\n", "\n")
        )

    @property
    def binance_keys(self) -> APIKeyPair:
        """
        Binance has a real testnet (https://testnet.binance.vision): in sandbox mode, testnet keys are used
        and orders are sent to the testnet.
        """
        if self.sandbox_mode:
            return APIKeyPair(
                api_key=os.getenv("BINANCE_API_KEY_SANDBOX", ""),
                secret=os.getenv("BINANCE_API_SECRET_SANDBOX", "")
            )
        else:
            return APIKeyPair(
                api_key=os.getenv("BINANCE_API_KEY_PRODUCTION", ""),
                secret=os.getenv("BINANCE_API_SECRET_PRODUCTION", "")
            )

    class Config:
        env_file = ".env"
        extra = "allow"  # or "ignore" to silently drop undeclared variables

applicationSettings = Settings()
