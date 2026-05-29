from pydantic import BaseModel, EmailStr
from typing import Optional


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    rol: str
    nombre: str
    user_id: int


class RegisterResponse(BaseModel):
    message: str
    user_id: int
    status: str