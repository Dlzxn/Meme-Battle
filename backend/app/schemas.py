from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator

from app.models import GameMode, SituationCategory, ReactionType, SpecialType


# Auth
class UserCreate(BaseModel):
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2 or len(v) > 50:
            raise ValueError("Username must be 2-50 characters")
        return v


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    username: str
    created_at: datetime

    model_config = {"from_attributes": True}


# Room
class RoomCreate(BaseModel):
    mode: GameMode = GameMode.no_czar
    category: SituationCategory = SituationCategory.all
    timer_play: int = 60
    timer_vote: int = 30
    cards_count: int = 7
    penalty_count: int = 1
    rounds_count: int = 10
    is_public: bool = False
    nickname: str
    custom_situations: Optional[str] = None

    @field_validator("timer_play")
    @classmethod
    def timer_play_valid(cls, v: int) -> int:
        if v not in range(15, 121, 15):
            raise ValueError("timer_play must be 15-120 in steps of 15")
        return v

    @field_validator("timer_vote")
    @classmethod
    def timer_vote_valid(cls, v: int) -> int:
        if v not in range(15, 61, 15):
            raise ValueError("timer_vote must be 15-60 in steps of 15")
        return v

    @field_validator("cards_count")
    @classmethod
    def cards_count_valid(cls, v: int) -> int:
        if not (5 <= v <= 10):
            raise ValueError("cards_count must be 5-10")
        return v

    @field_validator("penalty_count")
    @classmethod
    def penalty_count_valid(cls, v: int) -> int:
        if v not in (1, 2):
            raise ValueError("penalty_count must be 1 or 2")
        return v


class RoomOut(BaseModel):
    id: int
    code: str
    status: str
    mode: str
    timer_play: int
    timer_vote: int
    cards_count: int
    penalty_count: int
    rounds_count: int
    is_public: bool
    category: str
    player_count: int

    model_config = {"from_attributes": True}


class PlayerOut(BaseModel):
    id: int
    nickname: str
    is_host: bool
    is_connected: bool
    card_count: int

    model_config = {"from_attributes": True}


class MemeOut(BaseModel):
    id: int
    url: str
    name: str
    is_special: bool
    special_type: Optional[str] = None

    model_config = {"from_attributes": True}


# WebSocket messages
class WSMessage(BaseModel):
    type: str
    payload: dict = {}


# Game actions
class PlayCardAction(BaseModel):
    card_id: int
    second_card_id: Optional[int] = None


class VoteAction(BaseModel):
    target_player_id: int


class ReactionAction(BaseModel):
    play_id: int
    reaction_type: ReactionType


class CzarPickAction(BaseModel):
    winner_player_id: int


class UseSpecialAction(BaseModel):
    card_id: int
    target_player_id: Optional[int] = None


# Stats
class StatsOut(BaseModel):
    games_played: int
    games_won: int
    win_rate: float
    favorite_meme: Optional[MemeOut] = None
    unlocked_packs: list[str] = []

    model_config = {"from_attributes": True}


class LeaderboardEntry(BaseModel):
    rank: int
    username: str
    games_played: int
    games_won: int
    win_rate: float
