from fastapi import FastAPI
from app.api.router import router
from app.config import applicationSettings

app = FastAPI(title="Botox API")

# Importer toutes les routes définies dans router.py
app.include_router(router)