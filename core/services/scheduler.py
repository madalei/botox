from apscheduler.schedulers.background import BackgroundScheduler

from config import applicationSettings
from core.strategies.moving_average_crossover import MovingAverageCrossoverStrategy
from infrastructure.adapters.binance_adapter import BinanceAdapter


def run_strategy_job():
    print("⏱️ Launch strategy MovingAverageCrossoverStrategy ...")
    binance_adapter = BinanceAdapter(
        api_key=applicationSettings.binance_keys.api_key,
        secret=applicationSettings.binance_keys.secret,
        sandbox=applicationSettings.sandbox_mode
    )

    strategy = MovingAverageCrossoverStrategy(binance_adapter)
    result = strategy.run()
    print("Result:", result)


scheduler = BackgroundScheduler()
scheduler.add_job(run_strategy_job, 'interval', hours=4)
scheduler.start()
