from typing import List

from pydantic import BaseModel


class UserBase(BaseModel):
    email: str


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: int
    cameras: List[int] = []


class UserUpdate(BaseModel):
    email: str = None


class CameraCreate(BaseModel):
    connection_string: str
    description: str


class Camera(CameraCreate):
    id: int
    users: List[int] = []


class CameraUpdate(BaseModel):
    connection_string: str = None
    description: str = None
