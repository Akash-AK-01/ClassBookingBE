from pydantic import BaseModel, EmailStr
from typing import Optional

class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str
    role: Optional[str] = "STUDENT"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    role: str
    is_active: bool
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse
