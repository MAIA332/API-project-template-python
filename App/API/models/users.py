from pydantic import BaseModel, EmailStr
from typing import Optional

class UserCreateInput(BaseModel):
    email: EmailStr
    name: str
    password: str
    description: Optional[str] = None
    profileImage: Optional[str] = None
    phoneNumber: Optional[str] = None
    role_identifier: str 