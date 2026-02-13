from dotenv import load_dotenv
from pathlib import Path


def pytest_configure():
    # Path to backend/.env.test
    env_path = Path(__file__).resolve().parents[1] / ".env.test"
    load_dotenv(env_path, override=True)