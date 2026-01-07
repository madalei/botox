from dotenv import load_dotenv
import os

load_dotenv()  # load env variables (from .env)

binance_api_key = os.getenv("API_KEY")
binance_api_secret = os.getenv("API_SECRET")