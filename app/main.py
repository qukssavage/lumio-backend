import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import create_tables
from app.routers import auth, chats, upload, users, websocket
from app.services.firebase import init_firebase

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        logger.info("Initializing Firebase...")
        init_firebase()
        logger.info("Firebase OK")
        logger.info("Creating tables...")
        await create_tables()
        logger.info("Tables OK — startup complete")
    except Exception as e:
        logger.exception(f"Startup failed: {e}")
        raise
    yield


app = FastAPI(title="Lumio API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(chats.router)
app.include_router(upload.router)
app.include_router(websocket.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
