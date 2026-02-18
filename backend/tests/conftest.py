import os

from dotenv import load_dotenv
from pathlib import Path
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.order import Base


def pytest_configure():
    # Path to backend/.env.test
    env_path = Path(__file__).resolve().parents[1] / ".env.test"
    load_dotenv(env_path, override=True)



@pytest.fixture(scope="session")
def engine():
    engine = create_engine(os.getenv("DATABASE_URL"))
    Base.metadata.create_all(engine)
    yield engine
    # Clean up tables after test (optional - removes all data)
    # Uncomment to drop tables after each test
    # Base.metadata.drop_all(engine)
    engine.dispose()

@pytest.fixture(scope="function")
def test_db(engine):
    connection = engine.connect()
    transaction = connection.begin()

    TestingSessionLocal = sessionmaker(bind=connection)
    session = TestingSessionLocal()

    yield session

    session.close()
    transaction.rollback()
    connection.close()