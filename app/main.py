from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import create_tables
from app.routers import auth, chats, users, websocket
from app.services.firebase import init_firebase


@asynccontextmanager
async def lifespan(app: FastAPI):
    # при старте
    init_firebase()
    await create_tables()
    yield
    # при остановке — ничего не нужно


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
app.include_router(websocket.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
