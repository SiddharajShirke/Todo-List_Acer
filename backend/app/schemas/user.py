from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

class UserOut(BaseModel):
    id: int
    email: str
    name: Optional[str]
    avatar_url: Optional[str]
    preferences: dict = {}
    class Config: from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

class UserPreferencesUpdate(BaseModel):
    preferences: dict
