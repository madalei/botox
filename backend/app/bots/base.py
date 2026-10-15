from app.repositories.order_repository import OrderRepository
from app.services.logging import bot_logger
from enum import Enum
import asyncio

class BotStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"

class BaseBot:
    def __init__(self, bot_id: str, strategy, capital: float = 1000.0, check_interval: int = 900, save_state=None):
        self.bot_id = bot_id
        self.strategy = strategy
        # Capital de secours : utilisé seulement quand le solde réel n'est pas disponible (paper trading, erreur API)
        self.capital = capital
        # save_state(bot_id, state) : sauvegarde l'état de la position en base (branché par BotManager)
        self.save_state = save_state
        # Todo here maybe some other customisable params
        self.check_interval = check_interval  # seconds, by default, checks every 15 minutes (900 seconds).
        self.status = BotStatus.CREATED
        self._task: asyncio.Task | None = None

    async def get_capital(self, exchange) -> float:
        """
        Solde disponible dans la devise de cotation (EUR pour BTC/EUR) sur l'exchange.
        Repli sur self.capital en paper trading ou si l'appel échoue : une vente (stop) ne doit jamais être bloquée
        par une erreur de solde, et un achat trop gros pour le solde réel échoue simplement côté exchange.
        """
        quote_currency = self.strategy.symbol.split("/")[1]
        try:
            balance = await exchange.get_free_balance(quote_currency)
        except Exception as e:
            bot_logger.warning(f"Balance unavailable, using fixed capital {self.capital}: {e}", extra={"bot_id": self.bot_id})
            return self.capital
        return self.capital if balance is None else balance

    async def tick(self, exchange, order_service):
        """
        Execute a single strategy evaluation cycle.
        """
        capital = await self.get_capital(exchange)
        # État avant la bougie : si l'ordre échoue sur l'exchange, on y revient (sinon le bot croirait
        # avoir acheté des BTC qu'il n'a pas, ou avoir vendu des BTC qu'il a encore)
        state_before = self.strategy.get_state()

        # Generate signal/order from strategy
        order_signal = await self.strategy.generate_signals(exchange, capital)

        executed_order = None
        if not order_signal:
            bot_logger.info("No signal generated", extra={"bot_id": self.bot_id})
        else:
            # Log the generated signal
            bot_logger.info(
                f"Signal detected: {order_signal.side} "
                f"{order_signal.amount} {order_signal.symbol} "
                f"at {order_signal.price}",
                extra={"bot_id": self.bot_id},
            )

            order_signal.bot_id = self.bot_id

            # Persist order to DB
            db_order = await order_service.create_order(order_signal)

            # Execute order via exchange
            executed_order = await order_service.execute_order(db_order.id)

            if executed_order is None or executed_order.status == "FAILED":
                bot_logger.error(
                    f"{order_signal.side} failed on the exchange, position state restored", extra={"bot_id": self.bot_id}
                )
                self.strategy.load_state(state_before)

        # Sauvegarde à chaque changement (achat, vente, stop suiveur remonté), pour la retrouver après un redémarrage
        state_after = self.strategy.get_state()
        if self.save_state and state_after != state_before:
            self.save_state(self.bot_id, state_after)

        return executed_order

    async def run(self, exchange, order_service=None):
        """
        Live trading loop: run the strategy each "check_interval" times and execute trades if signals appear.
        """
        bot_logger.info("Bot started", extra={"bot_id": self.bot_id})
        while self.status == BotStatus.RUNNING:
            try:
                await self.tick(exchange, order_service)
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                bot_logger.error(f"Error in bot loop: {e}", extra={"bot_id": self.bot_id})
                await asyncio.sleep(self.check_interval)

        bot_logger.info(f"Bot {self.bot_id} stopped", extra={"bot_id": self.bot_id})


    # async def start(self, exchange, order_service=None):
    #     self.status = BotStatus.RUNNING
    #     self._task = asyncio.create_task(self.run(exchange, order_service))

    async def stop(self):
        self.status = BotStatus.STOPPED
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                bot_logger.info("Bot stopped", extra={"bot_id": self.bot_id})

    def get_strategy_params(self):
        pass