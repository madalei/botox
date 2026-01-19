import logging
import sys

class BotLoggerAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        # Ensure 'bot_id' exists in extra to avoid KeyError
        extra = kwargs.get("extra", {})
        if "bot_id" not in extra:
            extra["bot_id"] = "-"
        kwargs["extra"] = extra
        return msg, kwargs

def setup_logger(name="botox_app"):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)

    formatter = logging.Formatter(
        '{"time": "%(asctime)s", "level": "%(levelname)s", "module": "%(module)s", '
        '"bot_id": "%(bot_id)s", "message": "%(message)s"}'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Wrap logger in adapter to safely handle 'bot_id'
    return BotLoggerAdapter(logger, extra={})

# central logger instance
bot_logger = setup_logger()