# Backtests

Backtests replay historical candles through a strategy (via `HistoricalExchange`) and print the signals and the P&L net of trading fees.

## Layout

```
backtests/
├── engine.py      # shared: run_backtest(), compute_pnl(orders, fee_rate), assert_alternating_sides()
├── coinbase/      # exchange used by the bots
│   ├── market.py  # FEE_RATE (0.60%), load_candles(), load_year() for Coinbase CSVs
│   ├── data/      # BTC-EUR-1h-2024-01.csv ... (downloaded, see below)
│   ├── sweep.py   # shared runner + ranked tables for the parameter sweeps
│   ├── test_backtest_*.py
│   └── test_*_params_sweep.py   # parameter sweeps, excluded from a plain `pytest` (slow)
└── binance/       # not used for now (not MiCA compliant)
    ├── market.py  # FEE_RATE (0.10%), load_candles(), load_year() for Binance klines CSVs
    ├── data/      # BTCUSDT-1h-2024-01.csv ... (from data.binance.vision)
    ├── test_backtest_*.py
    └── test_*_params_sweep.py
```

## How to run backtests (Coinbase)

From `backend/`:

1. Download the candles (Coinbase public endpoint, no API key needed). It writes one CSV per month into `tests/backtests/coinbase/data/`. Coinbase has no 4h candles, 6h is the closest slower timeframe:

   ```bash
   python scripts/download_coinbase_candles.py --symbol BTC/EUR --timeframe 1h --start 2022-01 --end 2026-09
   python scripts/download_coinbase_candles.py --symbol BTC/EUR --timeframe 6h --start 2022-01 --end 2026-09
   ```

2. Run the backtests (`-s` shows the printed results):

   ```bash
   pytest tests/backtests/coinbase -s
   pytest tests/backtests/coinbase/test_backtest_moving_avg_strategy.py::test_backtest_1h_2024 -s
   ```

## Parameter sweeps

They run every config on each year of BTC-EUR (1h and 6h), then print one table per year and a summary of the net P&L of every config over all years. They take a few minutes, so `pytest.ini` excludes them; run them by clearing `addopts`:

```bash
pytest tests/backtests/coinbase/test_moving_avg_params_sweep.py -s -o addopts=""
pytest tests/backtests/coinbase/test_rsi_params_sweep.py -s -o addopts=""
```

To try other settings, edit `STRATEGY_CONFIGS` / `RSI_CONFIGS` in those files (names must be unique).
