from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from colombia_markets.api.router import api_router

app = FastAPI(
    title="Colombia Local Markets API",
    description="API for Colombian TES, FX, and macro market analytics.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": "Colombia Local Markets API",
        "status": "running",
    }
