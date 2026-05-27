from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Integer, String, Boolean, DateTime, ForeignKey, Text, Enum as SAEnum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.database import Base


class GameMode(str, enum.Enum):
    no_czar = "no_czar"
    czar = "czar"
    arena = "arena"


class RoomStatus(str, enum.Enum):
    waiting = "waiting"
    playing = "playing"
    finished = "finished"


class SituationCategory(str, enum.Enum):
    work = "work"
    school = "school"
    relations = "relations"
    internet = "internet"
    all = "all"


class SpecialType(str, enum.Enum):
    steal = "steal"
    skip_penalty = "skip_penalty"
    double_play = "double_play"


class RoundStatus(str, enum.Enum):
    playing = "playing"
    voting = "voting"
    results = "results"
    finished = "finished"


class ReactionType(str, enum.Enum):
    laugh = "laugh"
    fire = "fire"
    trash = "trash"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    players: Mapped[list["Player"]] = relationship(back_populates="user")
    stats: Mapped[Optional["GameStats"]] = relationship(back_populates="user", uselist=False)
    unlocked_packs: Mapped[list["UnlockedPack"]] = relationship(back_populates="user")


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(6), unique=True, nullable=False, index=True)
    host_id: Mapped[Optional[int]] = mapped_column(ForeignKey("players.id"), nullable=True)
    status: Mapped[RoomStatus] = mapped_column(SAEnum(RoomStatus), default=RoomStatus.waiting)
    mode: Mapped[GameMode] = mapped_column(SAEnum(GameMode), default=GameMode.no_czar)
    timer_play: Mapped[int] = mapped_column(Integer, default=60)
    timer_vote: Mapped[int] = mapped_column(Integer, default=30)
    cards_count: Mapped[int] = mapped_column(Integer, default=7)
    penalty_count: Mapped[int] = mapped_column(Integer, default=1)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    category: Mapped[SituationCategory] = mapped_column(SAEnum(SituationCategory), default=SituationCategory.all)
    custom_situations: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rounds_count: Mapped[int] = mapped_column(Integer, default=10)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    players: Mapped[list["Player"]] = relationship(back_populates="room", foreign_keys="Player.room_id")
    rounds: Mapped[list["Round"]] = relationship(back_populates="room")


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"), nullable=False)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    nickname: Mapped[str] = mapped_column(String(50), nullable=False)
    is_connected: Mapped[bool] = mapped_column(Boolean, default=True)
    is_host: Mapped[bool] = mapped_column(Boolean, default=False)
    czar_order: Mapped[int] = mapped_column(Integer, default=0)

    room: Mapped["Room"] = relationship(back_populates="players", foreign_keys=[room_id])
    user: Mapped[Optional["User"]] = relationship(back_populates="players")
    cards: Mapped[list["PlayerCard"]] = relationship(back_populates="player", cascade="all, delete-orphan")
    plays: Mapped[list["Play"]] = relationship(back_populates="player", foreign_keys="Play.player_id")
    votes_cast: Mapped[list["Vote"]] = relationship(back_populates="voter", foreign_keys="Vote.voter_id")
    reactions: Mapped[list["Reaction"]] = relationship(back_populates="player")


class Meme(Base):
    __tablename__ = "memes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    url: Mapped[str] = mapped_column(String(512), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="starter")
    is_special: Mapped[bool] = mapped_column(Boolean, default=False)
    special_type: Mapped[Optional[SpecialType]] = mapped_column(SAEnum(SpecialType), nullable=True)

    player_cards: Mapped[list["PlayerCard"]] = relationship(back_populates="meme")


class Situation(Base):
    __tablename__ = "situations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[SituationCategory] = mapped_column(SAEnum(SituationCategory), nullable=False)

    rounds: Mapped[list["Round"]] = relationship(back_populates="situation")


class PlayerCard(Base):
    __tablename__ = "player_cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
    meme_id: Mapped[int] = mapped_column(ForeignKey("memes.id"), nullable=False)

    player: Mapped["Player"] = relationship(back_populates="cards")
    meme: Mapped["Meme"] = relationship(back_populates="player_cards")


class Round(Base):
    __tablename__ = "rounds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"), nullable=False)
    situation_id: Mapped[Optional[int]] = mapped_column(ForeignKey("situations.id"), nullable=True)
    czar_id: Mapped[Optional[int]] = mapped_column(ForeignKey("players.id"), nullable=True)
    status: Mapped[RoundStatus] = mapped_column(SAEnum(RoundStatus), default=RoundStatus.playing)
    round_number: Mapped[int] = mapped_column(Integer, default=1)
    situation_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    room: Mapped["Room"] = relationship(back_populates="rounds")
    situation: Mapped[Optional["Situation"]] = relationship(back_populates="rounds")
    plays: Mapped[list["Play"]] = relationship(back_populates="round", cascade="all, delete-orphan")
    votes: Mapped[list["Vote"]] = relationship(back_populates="round", cascade="all, delete-orphan")


class Play(Base):
    __tablename__ = "plays"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    round_id: Mapped[int] = mapped_column(ForeignKey("rounds.id"), nullable=False)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
    meme_id: Mapped[int] = mapped_column(ForeignKey("memes.id"), nullable=False)
    is_double: Mapped[bool] = mapped_column(Boolean, default=False)
    second_meme_id: Mapped[Optional[int]] = mapped_column(ForeignKey("memes.id"), nullable=True)

    round: Mapped["Round"] = relationship(back_populates="plays")
    player: Mapped["Player"] = relationship(back_populates="plays", foreign_keys=[player_id])
    meme: Mapped["Meme"] = relationship(foreign_keys=[meme_id])
    second_meme: Mapped[Optional["Meme"]] = relationship(foreign_keys=[second_meme_id])
    reactions: Mapped[list["Reaction"]] = relationship(back_populates="play", cascade="all, delete-orphan")
    votes_received: Mapped[list["Vote"]] = relationship(back_populates="target_play")


class Vote(Base):
    __tablename__ = "votes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    round_id: Mapped[int] = mapped_column(ForeignKey("rounds.id"), nullable=False)
    voter_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
    target_player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
    target_play_id: Mapped[int] = mapped_column(ForeignKey("plays.id"), nullable=False)

    round: Mapped["Round"] = relationship(back_populates="votes")
    voter: Mapped["Player"] = relationship(back_populates="votes_cast", foreign_keys=[voter_id])
    target_play: Mapped["Play"] = relationship(back_populates="votes_received")


class Reaction(Base):
    __tablename__ = "reactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    play_id: Mapped[int] = mapped_column(ForeignKey("plays.id"), nullable=False)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
    type: Mapped[ReactionType] = mapped_column(SAEnum(ReactionType), nullable=False)

    play: Mapped["Play"] = relationship(back_populates="reactions")
    player: Mapped["Player"] = relationship(back_populates="reactions")


class GameStats(Base):
    __tablename__ = "game_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    games_played: Mapped[int] = mapped_column(Integer, default=0)
    games_won: Mapped[int] = mapped_column(Integer, default=0)
    favorite_meme_id: Mapped[Optional[int]] = mapped_column(ForeignKey("memes.id"), nullable=True)

    user: Mapped["User"] = relationship(back_populates="stats")
    favorite_meme: Mapped[Optional["Meme"]] = relationship()


class UnlockedPack(Base):
    __tablename__ = "unlocked_packs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    pack_name: Mapped[str] = mapped_column(String(100), nullable=False)

    user: Mapped["User"] = relationship(back_populates="unlocked_packs")
