import json

import redis.asyncio as aioredis

from app.config import settings

redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global redis
    if redis is None:
        redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return redis


async def publish(channel: str, data: dict):
    """Публикуем событие в Redis канал (для передачи между серверами)."""
    r = await get_redis()
    await r.publish(channel, json.dumps(data))


async def set_user_online(user_id: int, ttl: int = 60):
    """Отмечаем пользователя онлайн на ttl секунд."""
    r = await get_redis()
    await r.setex(f"online:{user_id}", ttl, "1")


async def is_user_online(user_id: int) -> bool:
    r = await get_redis()
    return await r.exists(f"online:{user_id}") == 1


async def store_otp(phone: str, code: str, ttl: int = 300):
    """Сохраняем OTP код на 5 минут."""
    r = await get_redis()
    await r.setex(f"otp:{phone}", ttl, code)


async def get_otp(phone: str) -> str | None:
    r = await get_redis()
    return await r.get(f"otp:{phone}")


async def delete_otp(phone: str):
    r = await get_redis()
    await r.delete(f"otp:{phone}")
