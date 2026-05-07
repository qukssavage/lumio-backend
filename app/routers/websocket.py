import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import and_, select

from app.core.security import decode_access_token
from app.database import AsyncSessionLocal
from app.models.chat import ChatMember
from app.models.message import Message
from app.services.redis_client import get_redis, publish, set_user_online

router = APIRouter(tags=["websocket"])

# локальный реестр подключений: user_id → WebSocket
_connections: dict[int, WebSocket] = {}


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str):
    """
    Единый WebSocket для всех чатов пользователя.
    Подключение: ws://host/ws?token=<JWT>
    """
    # аутентификация через токен в query-параметре
    try:
        user_id = decode_access_token(token)
    except ValueError:
        await websocket.close(code=4001)
        return

    await websocket.accept()
    _connections[user_id] = websocket
    await set_user_online(user_id)

    # подписываемся на Redis канал этого пользователя
    redis = await get_redis()
    pubsub = redis.pubsub()
    await pubsub.subscribe(f"user:{user_id}")

    async def redis_listener():
        """Слушаем Redis и пересылаем события в WebSocket."""
        async for msg in pubsub.listen():
            if msg["type"] == "message":
                await websocket.send_text(msg["data"])

    listener_task = asyncio.create_task(redis_listener())

    try:
        while True:
            raw = await websocket.receive_text()
            await set_user_online(user_id)  # обновляем TTL онлайн-статуса

            data = json.loads(raw)
            event_type = data.get("type")

            if event_type == "message":
                await _handle_message(user_id, data)

            elif event_type == "typing":
                await _handle_typing(user_id, data)

    except WebSocketDisconnect:
        pass
    finally:
        listener_task.cancel()
        await pubsub.unsubscribe(f"user:{user_id}")
        _connections.pop(user_id, None)


async def _handle_message(sender_id: int, data: dict):
    chat_id = data.get("chat_id")
    content = data.get("content")
    message_type = data.get("message_type", "text")
    file_url = data.get("file_url")

    async with AsyncSessionLocal() as db:
        # проверяем что отправитель — участник чата
        result = await db.execute(
            select(ChatMember).where(
                and_(ChatMember.chat_id == chat_id, ChatMember.user_id == sender_id)
            )
        )
        if not result.scalar_one_or_none():
            return

        # сохраняем сообщение в БД
        msg = Message(
            chat_id=chat_id,
            sender_id=sender_id,
            type=message_type,
            content=content,
            file_url=file_url,
        )
        db.add(msg)
        await db.commit()
        await db.refresh(msg)

        # получаем всех участников чата
        members = await db.execute(
            select(ChatMember).where(ChatMember.chat_id == chat_id)
        )
        member_ids = [m.user_id for m in members.scalars().all()]

    event = json.dumps({
        "type": "new_message",
        "payload": {
            "id": msg.id,
            "chat_id": chat_id,
            "sender_id": sender_id,
            "type": message_type,
            "content": content,
            "file_url": file_url,
            "created_at": msg.created_at.isoformat(),
        },
    })

    # рассылаем всем участникам через Redis pub/sub
    for uid in member_ids:
        await publish(f"user:{uid}", json.loads(event))


async def _handle_typing(sender_id: int, data: dict):
    chat_id = data.get("chat_id")
    async with AsyncSessionLocal() as db:
        members = await db.execute(
            select(ChatMember).where(ChatMember.chat_id == chat_id)
        )
        member_ids = [m.user_id for m in members.scalars().all()]

    event = {"type": "typing", "payload": {"chat_id": chat_id, "user_id": sender_id}}
    for uid in member_ids:
        if uid != sender_id:
            await publish(f"user:{uid}", event)
