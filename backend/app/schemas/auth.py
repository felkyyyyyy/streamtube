import re
from pydantic import BaseModel, EmailStr, Field, field_validator


USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.-]{3,32}$")


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=32, examples=["alex_dev"])
    email: EmailStr = Field(..., examples=["alex@example.com"])
    password: str = Field(..., min_length=8, max_length=128, examples=["StrongPass123!"])
    channel_name: str | None = Field(default=None, max_length=80)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        v = v.strip().lower()
        if not USERNAME_RE.match(v):
            raise ValueError("Username may contain only letters, digits, _, ., and -")
        return v


class LoginRequest(BaseModel):
    identifier: str = Field(..., description="Username or email", examples=["alex_dev"])
    password: str = Field(..., min_length=1, max_length=128)


class UserPublic(BaseModel):
    id: str
    username: str
    email: str | None = None
    role: str
    channel_name: str
    channel_description: str
    avatar_color: str
    banner_color: str
    is_active: bool

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic
