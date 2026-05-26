"""Shared pytest fixtures for all test modules."""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.models import (
    User, Room, Player, Meme, Situation, GameStats, PlayerCard,
    SituationCategory, GameMode, RoomStatus, SpecialType,
)
from app.auth import hash_password, create_access_token

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


# ── Engine & Session ──────────────────────────────────────────


@pytest_asyncio.fixture
async def engine():
    """In-memory SQLite engine, tables created once per test."""
    _engine = create_async_engine(
        TEST_DB_URL,
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield _engine
    try:
        await _engine.dispose()
    except Exception:
        pass


@pytest_asyncio.fixture
async def db(engine):
    """Direct async DB session for setting up test data."""
    TestSession = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with TestSession() as session:
        yield session


@pytest_asyncio.fixture
async def client(engine):
    """Async HTTP test client with DB and game-engine session overrides."""
    TestSession = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with TestSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    with (
        patch("app.main.engine", engine),
        patch("app.game_engine.AsyncSessionLocal", TestSession),
        patch("app.routers.websocket.AsyncSessionLocal", TestSession),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac

    app.dependency_overrides.clear()


# ── Manager mock ──────────────────────────────────────────────


class _MockManagers:
    """Both manager mocks bundled together for assertions."""
    def __init__(self, ge, ws):
        self.ge = ge
        self.ws = ws

    # Proxy to ge so game-engine-level assertions work naturally
    @property
    def broadcast(self):
        return self.ge.broadcast

    @property
    def send_personal(self):
        return self.ge.send_personal


@pytest.fixture
def mock_manager():
    """Patch connection manager in game_engine and websocket router."""
    with (
        patch("app.game_engine.manager") as ge_mgr,
        patch("app.routers.websocket.manager") as ws_mgr,
    ):
        for m in (ge_mgr, ws_mgr):
            m.broadcast = AsyncMock()
            m.send_personal = AsyncMock()
            m.connect = AsyncMock()
            m.disconnect = MagicMock()
        yield _MockManagers(ge_mgr, ws_mgr)


@pytest.fixture
def mock_create_task():
    """Prevent background timer coroutines from running in tests."""
    with patch("asyncio.create_task") as mock:
        def _close(coro, **kw):
            try:
                coro.close()
            except Exception:
                pass
            return MagicMock()
        mock.side_effect = _close
        yield mock


# ── User & auth fixtures ──────────────────────────────────────


@pytest_asyncio.fixture
async def user1(db):
    u = User(username="player1", password_hash=hash_password("pass1"))
    db.add(u)
    await db.flush()
    db.add(GameStats(user_id=u.id))
    await db.commit()
    return u


@pytest_asyncio.fixture
async def user2(db):
    u = User(username="player2", password_hash=hash_password("pass2"))
    db.add(u)
    await db.flush()
    db.add(GameStats(user_id=u.id))
    await db.commit()
    return u


@pytest_asyncio.fixture
async def headers1(user1):
    return {"Authorization": f"Bearer {create_access_token(user1.id)}"}


@pytest_asyncio.fixture
async def headers2(user2):
    return {"Authorization": f"Bearer {create_access_token(user2.id)}"}


# ── Game data fixtures ────────────────────────────────────────


@pytest_asyncio.fixture
async def memes(db):
    """20 regular memes + 3 special cards."""
    items = [
        Meme(url=f"http://img/{i}.jpg", name=f"Meme{i}", category="starter", is_special=False)
        for i in range(20)
    ]
    items += [
        Meme(url="http://img/steal.jpg",  name="Steal",  category="special",
             is_special=True, special_type=SpecialType.steal),
        Meme(url="http://img/skip.jpg",   name="Skip",   category="special",
             is_special=True, special_type=SpecialType.skip_penalty),
        Meme(url="http://img/double.jpg", name="Double", category="special",
             is_special=True, special_type=SpecialType.double_play),
    ]
    db.add_all(items)
    await db.commit()
    return items


@pytest_asyncio.fixture
async def situations(db):
    items = [
        Situation(text=f"Situation {i}", category=SituationCategory.all)
        for i in range(10)
    ]
    db.add_all(items)
    await db.commit()
    return items


@pytest_asyncio.fixture
async def room_with_players(db, memes, situations):
    """Room in waiting state with 2 connected players (p1 = host)."""
    room = Room(
        code="TSTM01",
        mode=GameMode.no_czar,
        timer_play=60,
        timer_vote=30,
        cards_count=5,
        penalty_count=1,
        is_public=False,
        category=SituationCategory.all,
        status=RoomStatus.waiting,
    )
    db.add(room)
    await db.flush()

    p1 = Player(room_id=room.id, nickname="Host",  is_host=True,  is_connected=True, czar_order=0)
    p2 = Player(room_id=room.id, nickname="Guest", is_host=False, is_connected=True, czar_order=1)
    db.add_all([p1, p2])
    await db.flush()
    room.host_id = p1.id
    await db.commit()
    return room, p1, p2


@pytest_asyncio.fixture
async def playing_room(db, room_with_players):
    """Room in playing state with cards dealt (5 each)."""
    room, p1, p2 = room_with_players
    room.status = RoomStatus.playing

    # Fetch memes to deal
    from sqlalchemy import select
    meme_q = await db.execute(
        select(Meme).where(Meme.is_special == False).limit(10)  # noqa: E712
    )
    all_memes = list(meme_q.scalars().all())

    for idx, player in enumerate([p1, p2]):
        for m in all_memes[idx * 5: idx * 5 + 5]:
            db.add(PlayerCard(player_id=player.id, meme_id=m.id))

    await db.commit()
    return room, p1, p2
