import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler

LOG_DIR = os.getenv("LOG_DIR", "logs")

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

    formatter = logging.Formatter(
        '{"time": "%(asctime)s", "level": "%(levelname)s", "module": "%(module)s", '
        '"bot_id": "%(bot_id)s", "message": "%(message)s"}'
    )

    # Stdout handler (always on)
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    logger.addHandler(stdout_handler)

    # Daily rotating file handler
    os.makedirs(LOG_DIR, exist_ok=True)
    file_handler = TimedRotatingFileHandler(
        filename=os.path.join(LOG_DIR, "botox.log"),
        when="midnight",
        interval=1,
        backupCount=30,  # keep 30 days
        utc=True,
    )
    file_handler.suffix = "%Y-%m-%d"
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Wrap logger in adapter to safely handle 'bot_id'
    return BotLoggerAdapter(logger, extra={})

# central logger instance
bot_logger = setup_logger()