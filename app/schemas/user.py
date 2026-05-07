from datetime import datetime

from pydantic import BaseModel


class UserOut(BaseModel):
    id: int
    phone: str
    username: str | None
    name: str
    avatar_url: str | None
    last_seen: datetime

    model_config = {"from_attributes": True}


class UserUpdateIn(BaseModel):
    name: str | None = None
    username: str | None = None


class ContactsLookupIn(BaseModel):
    phones: list[str]  # список номеров из контактов устройства
