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

This is a **FastAPI-based algorithmic trading backend** that runs trading bots on Coinbase (Advanced Trade API) or Binance, via `ccxt`. The exchange is picked at startup by the `EXCHANGE` env var (`coinbase` by default, since Binance is not MiCA compliant in France); all bots use the same one.

### Core Flow

```
POST /bots → BotManager.start_bot() → BaseBot.run() [loop]
                                          └→ Strategy.generate_signals(exchange, capital)
                                          └→ OrderService.create_order() → DB
                                          └→ OrderService.execute_order() → CoinbaseAdapter | BinanceAdapter
```

### Key Components

**`app/main.py`** — FastAPI lifespan builds the exchange adapter with `create_exchange()` (`app/infrastructure/adapters/exchange_factory.py`, driven by `EXCHANGE`), then `OrderService`, and `BotManager` stored in `app.state`. All bots share these singletons.

**`app/bots/base.py` (`BaseBot`)** — The trading loop. Each bot runs `tick()` every `check_interval` seconds (default 900s / 15min). `tick()` calls strategy → persists order → executes order.

**`app/bots/bot_manager.py` (`BotManager`)** — In-memory registry of running bots. Bots are started as asyncio tasks and are lost on restart (not re-hydrated from DB).

**`app/bots/strategies/moving_average_crossover.py` (`MovingAverageCrossoverStrategy`)** — A Pydantic `BaseModel` (not an ABC subclass, unlike `BaseStrategy` in `base.py`). Detects MA crossovers from OHLCV data and returns an `Order` object or `None`. Runtime state (position open, entry price) is stored in Pydantic `PrivateAttr`.

**`app/infrastructure/adapters/market_data_provider_interface.py` (`MarketDataProviderInterface`)** — Abstract interface implemented by both:
- `CoinbaseAdapter` — live exchange, async `get_history()` calls Coinbase API. Coinbase has no testnet: with `USE_SANDBOX=True` it runs in paper trading mode (live prices, orders simulated, never sent). Supported timeframes: 1m, 5m, 15m, 30m, 1h, 2h, 6h, 1d (max 300 candles per request).
- `BinanceAdapter` — live exchange via the Binance API. With `USE_SANDBOX=True` orders go to the Binance testnet (`BINANCE_API_KEY_SANDBOX` / `BINANCE_API_SECRET_SANDBOX`), otherwise production keys (`BINANCE_API_KEY_PRODUCTION` / `BINANCE_API_SECRET_PRODUCTION`).
- `HistoricalExchange` — uses a cursor over a DataFrame for backtesting

**`app/services/order_service.py` (`OrderService`)** — `create_order()` persists to DB; `execute_order()` dispatches to the active adapter's `place_market_buy/sell()`.

**`app/repositories/`** — SQLAlchemy repositories. `OrderRepository` accepts an optional `Session`; if none given, it creates its own via `SessionLocal()` and must be explicitly closed. When a `Session` is injected (FastAPI `Depends`), closing is skipped.

**`app/api/`** — Routes split into `commands/` (write operations: `POST /bots`) and `queries/` (read operations: `GET /bots`, `GET /bots/running`, market data endpoints of the active exchange only: `/coinbase/...` or `/binance/...`).

### Database

PostgreSQL with SQLAlchemy ORM (no Alembic migrations yet — raw SQL migration in `app/infrastructure/migrations/`). Tables: `bots`, `orders`, `bot_logs`.

### Testing Patterns

- `tests/conftest.py` — `test_db` fixture wraps each test in a transaction that is rolled back, keeping the DB clean.
- Backtesting tests use `HistoricalExchange` with CSV candle data from `tests/data/` (sourced from `data.binance.vision`, historical candles only, live trading uses the exchange selected by `EXCHANGE`).
- `@pytest.mark.asyncio` is required for async test functions.

### Environment

- `.env` — production/dev secrets (`EXCHANGE`, Coinbase CDP API key: `COINBASE_API_KEY_NAME` + `COINBASE_API_PRIVATE_KEY` as an ECDSA PEM with `\n` separators, Binance keys, DB URL)
- `.env.test` — loaded automatically by `conftest.py` via `pytest_configure()`