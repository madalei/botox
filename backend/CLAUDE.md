# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the FastAPI server
uvicorn app.main:app --reload

# Run all tests
pytest

# Run a single test file
pytest tests/test_backtest_moving_avg_strategy.py

# Run a single test by name
pytest tests/test_backtest_moving_avg_strategy.py::test_bot_backtest

# Run tests with coverage
pytest --cov
```

Tests require a running PostgreSQL instance. The test DB config is in `.env.test` (`postgresql://botox_user:botoxine@localhost:5432/botox_test`).

## Architecture

This is a **FastAPI-based algorithmic trading backend** that runs trading bots using the Binance exchange (via `ccxt`).

### Core Flow

```
POST /bots → BotManager.start_bot() → BaseBot.run() [loop]
                                          └→ Strategy.generate_signals(exchange, capital)
                                          └→ OrderService.create_order() → DB
                                          └→ OrderService.execute_order() → BinanceAdapter
```

### Key Components

**`app/main.py`** — FastAPI lifespan initializes a `BinanceAdapter`, `OrderService`, and `BotManager` stored in `app.state`. All bots share these singletons.

**`app/bots/base.py` (`BaseBot`)** — The trading loop. Each bot runs `tick()` every `check_interval` seconds (default 900s / 15min). `tick()` calls strategy → persists order → executes order.

**`app/bots/bot_manager.py` (`BotManager`)** — In-memory registry of running bots. Bots are started as asyncio tasks and are lost on restart (not re-hydrated from DB).

**`app/bots/strategies/moving_average_crossover.py` (`MovingAverageCrossoverStrategy`)** — A Pydantic `BaseModel` (not an ABC subclass, unlike `BaseStrategy` in `base.py`). Detects MA crossovers from OHLCV data and returns an `Order` object or `None`. Runtime state (position open, entry price) is stored in Pydantic `PrivateAttr`.

**`app/infrastructure/adapters/market_data_provider_interface.py` (`MarketDataProviderInterface`)** — Abstract interface implemented by both:
- `BinanceAdapter` — live exchange, async `get_history()` calls Binance API
- `HistoricalExchange` — uses a cursor over a DataFrame for backtesting

**`app/services/order_service.py` (`OrderService`)** — `create_order()` persists to DB; `execute_order()` dispatches to `BinanceAdapter.place_market_buy/sell()`.

**`app/repositories/`** — SQLAlchemy repositories. `OrderRepository` accepts an optional `Session`; if none given, it creates its own via `SessionLocal()` and must be explicitly closed. When a `Session` is injected (FastAPI `Depends`), closing is skipped.

**`app/api/`** — Routes split into `commands/` (write operations: `POST /bots`) and `queries/` (read operations: `GET /bots`, `GET /bots/running`, Binance data endpoints).

### Database

PostgreSQL with SQLAlchemy ORM (no Alembic migrations yet — raw SQL migration in `app/infrastructure/migrations/`). Tables: `bots`, `orders`, `bot_logs`.

### Testing Patterns

- `tests/conftest.py` — `test_db` fixture wraps each test in a transaction that is rolled back, keeping the DB clean.
- Backtesting tests use `HistoricalExchange` with CSV candle data from `tests/data/` (sourced from `data.binance.vision`).
- `@pytest.mark.asyncio` is required for async test functions.

### Environment

- `.env` — production/dev secrets (Binance API keys, DB URL)
- `.env.test` — loaded automatically by `conftest.py` via `pytest_configure()`