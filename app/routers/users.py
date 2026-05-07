from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.user import ContactsLookupIn, UserOut, UserUpdateIn
router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserOut)
async def update_me(
    body: UserUpdateIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.username:
        result = await db.execute(
            select(User).where(User.username == body.username, User.id != current_user.id)
        )
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Username уже занят")
        current_user.username = body.username

    if body.name:
        current_user.name = body.name

    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.get("/search", response_model=list[UserOut])
async def search_users(
    q: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Поиск по username или номеру телефона."""
    result = await db.execute(
        select(User).where(
            or_(
                User.username.ilike(f"%{q}%"),
                User.phone.ilike(f"%{q}%"),
            ),
            User.id != current_user.id,
            User.is_active == True,
        ).limit(20)
    )
    return result.scalars().all()


@router.post("/contacts", response_model=list[UserOut])
async def lookup_contacts(
    body: ContactsLookupIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Принимает список номеров телефона из контактов устройства,
    возвращает тех кто уже зарегистрирован в Lumio."""
    if not body.phones:
        return []
    result = await db.execute(
        select(User).where(
            User.phone.in_(body.phones),
            User.id != current_user.id,
            User.is_active == True,
        ).limit(500)
    )
    return result.scalars().all()


@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return user
