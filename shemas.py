from pydantic import BaseModel
from typing import Optional
from enum import Enum

class UserVkData(BaseModel):
    vk_id: int
    tg_name: str
    access_token: str
    init_data: str


class VkUser(BaseModel):
    first_name: str
    last_name: str
    sex: int

class ProfileRequest(BaseModel):
    tg_id: int

class UserProfile(BaseModel):
    tg_id: int
    photo: str
    info: str
    form: str

class Post(BaseModel):
    post_id: int
    text: str
    content: str
    likes: int
    dislikes: int
    creator_id: int
    describe: str
    type: str
    toxicity: Optional[str]


class PostCreate(BaseModel):
    text: str
    content: str
    describe: str
    type: str


class PostStat(BaseModel):
    post_id: int
    describe: str
    likes: int
    dislikes: int
    type: str


class Balance(BaseModel):
    init_data: str
    balance: int


class Likers(BaseModel):
    likers: list[int]


class EditProfile(BaseModel):
    data: str

class TokenRequest(BaseModel):
    user_id: int

class IphoneUser(BaseModel):
    tg_id: int
    vk_id: int
    tg_name: str

class UserID(BaseModel):
    tg_id: int

class UserPromotion(Enum):
    DOWNGRADE = "downgrade"
    UPGRADE = "upgrade"