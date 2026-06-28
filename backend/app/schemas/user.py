from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, Union
from uuid import UUID


class UserOut(BaseModel):
    id: int
    email: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    google_id: Optional[str] = None
    supabase_uid: Optional[Union[str, UUID]] = None
    preferences: dict = {}
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class UserPreferencesUpdate(BaseModel):
    preferences: dict
