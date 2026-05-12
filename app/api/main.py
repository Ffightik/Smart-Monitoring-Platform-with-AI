from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.core.database import init_db
from app.api.routes import upload, analysis, predict, chat
from app.api.routes.auth import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate()
    init_db()                          # creates users.db + tables
    print("✅ Database initialised")
    from app.models.hybrid_model import load_resources
    load_resources()
    print("✅ ML models loaded")
    yield
    print("👋 Shutting down")


app = FastAPI(
    title="HealthPlatform API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001",
                   "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router,         prefix="/api/v1")
app.include_router(upload.router,       prefix="/api/v1")
app.include_router(analysis.router,     prefix="/api/v1")
app.include_router(predict.router,      prefix="/api/v1")
app.include_router(chat.router,         prefix="/api/v1")


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "env": settings.APP_ENV}
