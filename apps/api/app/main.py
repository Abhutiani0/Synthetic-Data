from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database import init_db
from .routers import datasets, projects, runs

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="VeriSynth API",
    description="Synthetic Data Engine — generate useful fake data, remove the people, document the risk.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(datasets.router)
app.include_router(runs.router)


@app.get("/api/health")
def health() -> dict[str, object]:
    return {"status": "ok", "ai_enabled": settings.ai_enabled}
