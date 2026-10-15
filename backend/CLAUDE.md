# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the FastAPI server
uvicorn app.main:app --reload

# Run all tests
pytest

# Run a single test file
pytest tests/backtests/coinbase/test_backtest_moving_avg_strategy.py

# Run a single test by name
pytest tests/backtests/coinbase/test_backtest_moving_avg_strategy.py::test_backtest_1h_2024

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

**`app/bots/strategies/moving_average_crossover.py` (`MovingAverageCrossoverStrategy`)** — A Pydantic `BaseModel` (not an ABC subclass, unlike `BaseStrategy` in `base.py`). Detects MA crossovers from OHLCV data and returns an `Order` object or `None`. Runtime state (position open, entry price) is stored in Pydantic `PrivateAttr`. Optional `trend_window` (0 = off) only allows BUYs above that moving average. Optional `trailing_stop_pct` (0 = off) raises the stop loss below the highest price since entry, from the next candle on; `take_profit_pct = 0` disables the take profit. `buy_while_trend=True` buys on any candle where short MA > long MA (not only on the crossover); `exit_on_crossover=False` leaves exits to the stops. Stop loss / take profit are checked against the candle low / high (exit at the level, or at the open on a gap; the entry candle only uses its close).

**`app/infrastructure/adapters/market_data_provider_interface.py` (`MarketDataProviderInterface`)** — Abstract interface implemented by both:
- `CoinbaseAdapter` — live exchange, async `get_history()` calls Coinbase API. Coinbase has no testnet: with `USE_SANDBOX=True` it runs in paper trading mode (live prices, orders simulated, never sent). Supported timeframes: 1m, 5m, 15m, 30m, 1h, 2h, 6h, 1d. `get_history()` caps `limit` at 300 (Coinbase max per request; above it, the candles after `since` would be old ones, not the latest).
- `BinanceAdapter` — live exchange via the Binance API. With `USE_SANDBOX=True` orders go to the Binance testnet (`BINANCE_API_KEY_SANDBOX` / `BINANCE_API_SECRET_SANDBOX`), otherwise production keys (`BINANCE_API_KEY_PRODUCTION` / `BINANCE_API_SECRET_PRODUCTION`).
- `HistoricalExchange` — uses a cursor over a DataFrame for backtesting

**`app/services/order_service.py` (`OrderService`)** — `create_order()` persists to DB; `execute_order()` dispatches to the active adapter's `place_market_buy/sell()`.

**`app/repositories/`** — SQLAlchemy repositories. `OrderRepository` accepts an optional `Session`; if none given, it creates its own via `SessionLocal()` and must be explicitly closed. When a `Session` is injected (FastAPI `Depends`), closing is skipped.

**`app/api/`** — Routes split into `commands/` (write operations: `POST /bots`) and `queries/` (read operations: `GET /bots`, `GET /bots/running`, market data endpoints of the active exchange only: `/coinbase/...` or `/binance/...`).

### Database

PostgreSQL with SQLAlchemy ORM (no Alembic migrations yet — raw SQL migration in `app/infrastructure/migrations/`). Tables: `bots`, `orders`, `bot_logs`.

### Testing Patterns

- `tests/conftest.py` — `test_db` fixture wraps each test in a transaction that is rolled back, keeping the DB clean.
- Backtests live in `tests/backtests/`: the exchange-agnostic engine (`engine.py`: `run_backtest()`, `compute_pnl(orders, fee_rate)` net of fees) plus one folder per exchange, `coinbase/` (used) and `binance/` (unused for now). Each has a `market.py` (CSV loader, `load_year()`, taker `FEE_RATE`), its `data/` CSVs and its tests. Historical candles only; live trading uses the exchange selected by `EXCHANGE`.
- Coinbase candles are downloaded into `tests/backtests/coinbase/data/` with `python scripts/download_coinbase_candles.py --symbol BTC/EUR --timeframe 1h --start 2022-01 --end 2026-09` (no 4h on Coinbase, use 6h) (public endpoint, no API key). They have a header row, unlike the Binance ones (from `data.binance.vision`).
- `tests/backtests/conftest.py` saves what each backtest prints into `tests/backtests/reports/<exchange>/<test name>_<date>_<time>.txt` (gitignored).
- The parameter sweeps (`tests/backtests/coinbase/test_*_params_sweep.py`, built on `coinbase/sweep.py`; Binance has older ones) are slow and excluded in `pytest.ini`; run them with `-o addopts=""`.
- `@pytest.mark.asyncio` is required for async test functions.

### Environment

- `.env` — production/dev secrets (`EXCHANGE`, Coinbase CDP API key: `COINBASE_API_KEY_NAME` + `COINBASE_API_PRIVATE_KEY` as an ECDSA PEM with `\n` separators, Binance keys, DB URL)
- `.env.test` — loaded automatically by `conftest.py` via `pytest_configure()`