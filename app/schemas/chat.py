from datetime import datetime

from pydantic import BaseModel


class ChatOut(BaseModel):
    id: int
    type: str
    display_name: str          # для приватного — имя собеседника; для группы — название
    display_avatar: str | None # для приватного — аватар собеседника; для группы — аватар группы
    last_message: str | None = None
    last_message_at: datetime | None = None
    unread_count: int = 0
    other_user_id: int | None = None  # только для приватных чатов


class CreatePrivateChatIn(BaseModel):
    user_id: int


class CreateGroupChatIn(BaseModel):
    name: str
    member_ids: list[int]
