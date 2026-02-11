import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.order import Base, Order
from app.repositories.order_repository import OrderRepository
from tests.factories.bot_factory import create_bot_in_db
from tests.factories.order_factory import build_order

# PostgreSQL connection string
DATABASE_URL = "postgresql://botox_user:botoxine@localhost:5432/botox_test"

# Todo: move this to a common test utils file
@pytest.fixture(scope="function")
def test_db():
    """Create a fresh test database session for each test"""
    engine = create_engine(DATABASE_URL)

    # Create all tables
    Base.metadata.create_all(engine)

    # Create session
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()

    yield session

    # Cleanup: rollback any changes and close session
    session.rollback()
    session.close()

    # Clean up tables after test (optional - removes all data)
    # uncomment to drop tables after each test
    # Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def order_repository(test_db):
    """Create repository with test database session"""
    repo = OrderRepository(db=test_db)
    yield repo
    # No need to close since we passed external db


def test_create_order_inserts_to_database(order_repository, test_db):
    """Test that create_order successfully inserts an order into the database"""

    # Create parent row first
    bot = create_bot_in_db(test_db)

    buy_order = build_order(
        side="BUY",
        bot_id=bot.id,
        symbol="BTC/EUR",
        stop_loss=0.02,
        take_profit=0.04,
    )

    sell_order = build_order(
        side="SELL",
        bot_id=bot.id,
        symbol="BTC/EUR"
    )

    # Act
    saved_buy_order = order_repository.create_order(buy_order)
    saved_sell_order = order_repository.create_order(sell_order)

    # Assert
    assert saved_buy_order.id is not None
    assert saved_sell_order.id is not None
    assert saved_buy_order.symbol == "BTC/EUR"
    assert saved_sell_order.symbol == "BTC/EUR"
    assert saved_buy_order.side == "BUY"
    assert saved_sell_order.side == "SELL"

    # Verify it's actually in the database
    same_order_fetched_from_db = test_db.query(Order).filter(Order.id == saved_buy_order.id).first()
    assert same_order_fetched_from_db is not None
    assert same_order_fetched_from_db.bot_id == bot.id
