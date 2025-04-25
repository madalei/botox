from fastapi import FastAPI
from interfaces.api.router import router
from config import applicationSettings

app = FastAPI(title="Botox API")

# Importer toutes les routes définies dans router.py
app.include_router(router)


@app.get("/")
async def root():
    return {
        "message": "Hello World",
        "settings": {
            "environment": applicationSettings.environment,
            "binance_keys": applicationSettings.binance_keys
        }
    }

