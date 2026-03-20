from pydantic import BaseModel, EmailStr
from typing import List, Optional

class LoginInput(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    name: str
    description: Optional[str]
    email: str
    phone_number: Optional[str]
    role: str
    sector: str
    permited_routes: List[str]
    access_token: str
    refresh_token: str