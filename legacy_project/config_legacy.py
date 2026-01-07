from dotenv import load_dotenv
import os
from pydantic_settings import BaseSettings
from pydantic import BaseModel

load_dotenv()  # Charge .env


class APIKeyPair(BaseModel):
    api_key: str
    secret: str


class Settings(BaseSettings):
    sandbox_mode: bool = os.getenv("USE_SANDBOX", "False") == "True"
    environment: str = os.getenv("ENVIRONMENT", "development")

    @property
    def binance_keys(self) -> APIKeyPair:
        if self.sandbox_mode:
            return APIKeyPair(
                api_key=os.getenv("BINANCE_API_KEY_SANDBOX"),
                secret=os.getenv("BINANCE_API_SECRET_SANDBOX")
            )
        else:
            return APIKeyPair(
                api_key=os.getenv("BINANCE_API_KEY_PRODUCTION"),
                secret=os.getenv("BINANCE_API_SECRET_PRODUCTION")
            )

    class Config:
        env_file = ".env"
        extra = "allow"  # or "ignore" to silently drop undeclared variables

applicationSettings = Settings()
