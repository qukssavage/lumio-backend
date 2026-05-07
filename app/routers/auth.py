import random
import string

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.security import create_access_token
from app.database import get_db
from app.models.user import User
from app.schemas.auth import FirebaseTokenIn, RequestOtpIn, SetupProfileIn, TokenOut, VerifyOtpIn
from app.schemas.user import UserOut
from app.services.firebase import verify_firebase_token
from app.services.redis_client import delete_otp, get_otp, store_otp

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
async def login(body: FirebaseTokenIn, db: AsyncSession = Depends(get_db)):
    """
    Клиент проходит Firebase Phone Auth → получает ID токен → отправляет сюда.
    Мы верифицируем токен, создаём/находим пользователя, возвращаем JWT.
    """
    try:
        decoded = verify_firebase_token(body.firebase_token)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

    firebase_uid = decoded["uid"]
    phone = decoded.get("phone_number", "")

    result = await db.execute(select(User).where(User.firebase_uid == firebase_uid))
    user = result.scalar_one_or_none()

    is_new = False
    if not user:
        user = User(firebase_uid=firebase_uid, phone=phone, name="")
        db.add(user)
        await db.commit()
        await db.refresh(user)
        is_new = True

    token = create_access_token(user.id)
    return TokenOut(access_token=token, is_new_user=is_new)


@router.post("/request-otp")
async def request_otp(body: RequestOtpIn):
    """
    Отправляем OTP на номер телефона.
    В режиме разработки — возвращаем код в ответе.
    В продакшене — отправляем SMS через Eskiz.uz (TODO).
    """
    code = "".join(random.choices(string.digits, k=6))
    await store_otp(body.phone, code)
    # TODO: в продакшене отправлять SMS через Eskiz.uz вместо return code
    return {"message": "Код отправлен", "dev_code": code}


@router.post("/verify-otp", response_model=TokenOut)
async def verify_otp(body: VerifyOtpIn, db: AsyncSession = Depends(get_db)):
    """Проверяем OTP, создаём/находим пользователя, возвращаем JWT."""
    stored = await get_otp(body.phone)
    if not stored or stored != body.code:
        raise HTTPException(status_code=400, detail="Неверный или истёкший код")

    await delete_otp(body.phone)

    result = await db.execute(select(User).where(User.phone == body.phone))
    user = result.scalar_one_or_none()

    is_new = False
    if not user:
        user = User(phone=body.phone, firebase_uid=f"otp:{body.phone}", name="")
        db.add(user)
        await db.commit()
        await db.refresh(user)
        is_new = True

    token = create_access_token(user.id)
    return TokenOut(access_token=token, is_new_user=is_new)


@router.post("/setup-profile", response_model=UserOut)
async def setup_profile(
    body: SetupProfileIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Заполнение профиля после первой регистрации (имя обязательно, username опционально)."""
    if body.username:
        result = await db.execute(
            select(User).where(User.username == body.username, User.id != current_user.id)
        )
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Username уже занят")
        current_user.username = body.username

    current_user.name = body.name
    await db.commit()
    await db.refresh(current_user)
    return current_user
