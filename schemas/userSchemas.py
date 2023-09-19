from datetime import datetime
from pydantic import BaseModel, EmailStr, constr


class UserBaseSchema(BaseModel):
    name: str
    email: str
    mobile: str
    role: str = "marketeer"
    tiktok: list[str] = []
    youtube: list[str] = []
    twitter: list[str] = []
    views: int = 0
    likes: int = 0
    facebook: list[str] = []
    instagram: list[str] = []
    hashtag: str | None = None
    verified: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        orm_mode = True


class CreateUserSchema(UserBaseSchema):
    password: constr(min_length=8)
    passwordConfirm: str | None = None
    verified: bool = False


class LoginUserSchema(BaseModel):
    email: EmailStr
    password: constr(min_length=8)


class UserResponseSchema(UserBaseSchema):
    id: str
    pass


class UserResponse(BaseModel):
    status: str
    user: UserResponseSchema


class ContactSchema(BaseModel):
    name: str
    email: EmailStr
    message: str
    role: str