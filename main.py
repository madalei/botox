from fastapi import FastAPI
from interfaces.api.router import router
import uvicorn

app = FastAPI(title="Botox API")

# Importer toutes les routes définies dans router.py
app.include_router(router)

# if __name__ == "__main__":
#     uvicorn.run(app, host="0.0.0.0", port=8000)


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}
