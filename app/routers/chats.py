from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database import get_db
from app.models.chat import Chat, ChatMember
from app.models.message import Message
from app.models.user import User
from app.schemas.chat import ChatOut, CreateGroupChatIn, CreatePrivateChatIn
from app.schemas.message import MessageOut

router = APIRouter(prefix="/chats", tags=["chats"])


async def _build_chat_out(chat: Chat, current_user_id: int, db: AsyncSession) -> ChatOut:
    """Собирает полный ChatOut с именем, последним сообщением и непрочитанными."""
    members_res = await db.execute(
        select(ChatMember).where(ChatMember.chat_id == chat.id)
    )
    members = members_res.scalars().all()

    display_name = chat.name or "Группа"
    display_avatar = chat.avatar_url
    other_user_id = None

    if chat.type == "private":
        other_id = next((m.user_id for m in members if m.user_id != current_user_id), None)
        if other_id:
            user_res = await db.execute(select(User).where(User.id == other_id))
            other = user_res.scalar_one_or_none()
            if other:
                display_name = other.name or other.phone
                display_avatar = other.avatar_url
                other_user_id = other.id

    last_msg_res = await db.execute(
        select(Message)
        .where(Message.chat_id == chat.id, Message.is_deleted == False)
        .order_by(Message.id.desc())
        .limit(1)
    )
    last_msg = last_msg_res.scalar_one_or_none()

    last_message_text = None
    if last_msg:
        if last_msg.type == "image":
            last_message_text = f"📷 {last_msg.content}" if last_msg.content else "📷 Фото"
        else:
            last_message_text = last_msg.content

    return ChatOut(
        id=chat.id,
        type=chat.type,
        display_name=display_name,
        display_avatar=display_avatar,
        last_message=last_message_text,
        last_message_at=last_msg.created_at if last_msg else None,
        unread_count=0,
        other_user_id=other_user_id,
    )


@router.get("", response_model=list[ChatOut])
async def get_my_chats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Chat)
        .join(ChatMember, ChatMember.chat_id == Chat.id)
        .where(ChatMember.user_id == current_user.id)
        .order_by(Chat.id.desc())
    )
    chats = result.scalars().all()
    return [await _build_chat_out(c, current_user.id, db) for c in chats]


@router.post("/private", response_model=ChatOut)
async def create_private_chat(
    body: CreatePrivateChatIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Chat)
        .join(ChatMember, ChatMember.chat_id == Chat.id)
        .where(Chat.type == "private", ChatMember.user_id == current_user.id)
    )
    for chat in result.scalars().all():
        members = await db.execute(select(ChatMember).where(ChatMember.chat_id == chat.id))
        ids = {m.user_id for m in members.scalars().all()}
        if body.user_id in ids and len(ids) == 2:
            return await _build_chat_out(chat, current_user.id, db)

    chat = Chat(type="private")
    db.add(chat)
    await db.flush()
    db.add(ChatMember(chat_id=chat.id, user_id=current_user.id, role="admin"))
    db.add(ChatMember(chat_id=chat.id, user_id=body.user_id, role="member"))
    await db.commit()
    await db.refresh(chat)
    return await _build_chat_out(chat, current_user.id, db)


@router.post("/group", response_model=ChatOut)
async def create_group_chat(
    body: CreateGroupChatIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    GROUP_MEMBER_LIMIT = 40
    unique_ids = [uid for uid in body.member_ids if uid != current_user.id]
    if len(unique_ids) >= GROUP_MEMBER_LIMIT:
        raise HTTPException(status_code=400, detail=f"Максимум {GROUP_MEMBER_LIMIT} участников")

    chat = Chat(type="group", name=body.name)
    db.add(chat)
    await db.flush()
    db.add(ChatMember(chat_id=chat.id, user_id=current_user.id, role="admin"))
    for uid in unique_ids:
        db.add(ChatMember(chat_id=chat.id, user_id=uid, role="member"))
    await db.commit()
    await db.refresh(chat)
    return await _build_chat_out(chat, current_user.id, db)


@router.get("/{chat_id}/messages", response_model=list[MessageOut])
async def get_messages(
    chat_id: int,
    before_id: int | None = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    member = await db.execute(
        select(ChatMember).where(
            and_(ChatMember.chat_id == chat_id, ChatMember.user_id == current_user.id)
        )
    )
    if not member.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Нет доступа к этому чату")

    query = (
        select(Message)
        .where(Message.chat_id == chat_id, Message.is_deleted == False)
        .order_by(Message.id.desc())
        .limit(limit)
    )
    if before_id:
        query = query.where(Message.id < before_id)

    result = await db.execute(query)
    return list(reversed(result.scalars().all()))
