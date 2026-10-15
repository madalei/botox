from app.bots.base import BaseBot
from app.bots.strategies.moving_average_crossover import MovingAverageCrossoverStrategy
#from app.bots.strategies.rsi_strategy import RSIStrategy
from app.models.bot import Bot

STRATEGY_REGISTRY = {
  "MovingAverageCrossoverStrategy": MovingAverageCrossoverStrategy,
 # "RSIStrategy": RSIStrategy,
}

def build_bot_from_orm(db_bot: Bot) -> BaseBot:
  strategy_class = STRATEGY_REGISTRY.get(db_bot.strategy)
  if not strategy_class:
      raise ValueError(f"Unknown strategy: {db_bot.strategy}")
  strategy = strategy_class(**db_bot.params)
  # Position sauvegardée (achat en cours, stop suiveur...) : sans elle, les BTC achetés avant le redémarrage ne seraient jamais revendus
  strategy.load_state(db_bot.state)
  return BaseBot(bot_id=db_bot.id, strategy=strategy, check_interval=db_bot.params.get("check_interval", 900))