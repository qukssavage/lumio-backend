from datetime import datetime

from pydantic import BaseModel


class MessageOut(BaseModel):
    id: int
    chat_id: int
    sender_id: int | None
    type: str
    content: str | None
    file_url: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# Формат WebSocket-событий
class WSMessageIn(BaseModel):
    type: str        # "message" | "typing" | "read"
    chat_id: int
    content: str | None = None
    message_type: str = "text"  # "text" | "image"
    file_url: str | None = None


class WSEventOut(BaseModel):
    type: str        # "new_message" | "typing" | "user_online" | "message_read"
    payload: dict
