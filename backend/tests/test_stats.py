"""Tests for /api/stats/* endpoints."""
import pytest
from httpx import AsyncClient

from app.models import GameStats, UnlockedPack, Meme


async def test_my_stats_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/stats/me")
    assert resp.status_code == 401


async def test_my_stats_no_games(client: AsyncClient, user1, headers1):
    resp = await client.get("/api/stats/me", headers=headers1)
    assert resp.status_code == 200
    body = resp.json()
    assert body["games_played"] == 0
    assert body["games_won"] == 0
    assert body["win_rate"] == 0.0
    assert body["favorite_meme"] is None
    assert body["unlocked_packs"] == []


async def test_my_stats_with_games(client: AsyncClient, db, user1, headers1):
    stats = await db.get(GameStats, 1)  # created in user1 fixture
    # Find the stats by user_id
    from sqlalchemy import select
    st_q = await db.execute(select(GameStats).where(GameStats.user_id == user1.id))
    stats = st_q.scalar_one()
    stats.games_played = 10
    stats.games_won = 4
    await db.commit()

    resp = await client.get("/api/stats/me", headers=headers1)
    assert resp.status_code == 200
    body = resp.json()
    assert body["games_played"] == 10
    assert body["games_won"] == 4
    assert body["win_rate"] == 40.0


async def test_my_stats_with_favorite_meme(client: AsyncClient, db, user1, headers1, memes):
    from sqlalchemy import select
    st_q = await db.execute(select(GameStats).where(GameStats.user_id == user1.id))
    stats = st_q.scalar_one()
    stats.games_played = 5
    stats.games_won = 5
    stats.favorite_meme_id = memes[0].id
    await db.commit()

    resp = await client.get("/api/stats/me", headers=headers1)
    assert resp.status_code == 200
    body = resp.json()
    assert body["favorite_meme"] is not None
    assert body["favorite_meme"]["id"] == memes[0].id


async def test_my_stats_with_unlocked_packs(client: AsyncClient, db, user1, headers1):
    db.add(UnlockedPack(user_id=user1.id, pack_name="classic_internet"))
    db.add(UnlockedPack(user_id=user1.id, pack_name="gaming"))
    await db.commit()

    resp = await client.get("/api/stats/me", headers=headers1)
    assert resp.status_code == 200
    packs = resp.json()["unlocked_packs"]
    assert "classic_internet" in packs
    assert "gaming" in packs


async def test_leaderboard_empty(client: AsyncClient):
    resp = await client.get("/api/stats/leaderboard")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_leaderboard_requires_10_games(client: AsyncClient, db, user1):
    from sqlalchemy import select
    st_q = await db.execute(select(GameStats).where(GameStats.user_id == user1.id))
    stats = st_q.scalar_one()
    stats.games_played = 9  # below threshold
    stats.games_won = 9
    await db.commit()

    resp = await client.get("/api/stats/leaderboard")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_leaderboard_with_qualified_player(client: AsyncClient, db, user1):
    from sqlalchemy import select
    st_q = await db.execute(select(GameStats).where(GameStats.user_id == user1.id))
    stats = st_q.scalar_one()
    stats.games_played = 10
    stats.games_won = 8
    await db.commit()

    resp = await client.get("/api/stats/leaderboard")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["username"] == "player1"
    assert data[0]["rank"] == 1
    assert data[0]["win_rate"] == 80.0


async def test_leaderboard_sorted_by_win_rate(client: AsyncClient, db, user1, user2):
    from sqlalchemy import select
    for user, played, won in [(user1, 10, 3), (user2, 10, 9)]:
        st_q = await db.execute(select(GameStats).where(GameStats.user_id == user.id))
        stats = st_q.scalar_one()
        stats.games_played = played
        stats.games_won = won
    await db.commit()

    resp = await client.get("/api/stats/leaderboard")
    data = resp.json()
    assert len(data) == 2
    assert data[0]["win_rate"] > data[1]["win_rate"]
    assert data[0]["username"] == "player2"


async def test_leaderboard_period_param(client: AsyncClient):
    # period param is accepted; filtering by period not yet implemented but should not 500
    resp = await client.get("/api/stats/leaderboard", params={"period": "week"})
    assert resp.status_code == 200

    resp = await client.get("/api/stats/leaderboard", params={"period": "month"})
    assert resp.status_code == 200


async def test_leaderboard_invalid_period(client: AsyncClient):
    resp = await client.get("/api/stats/leaderboard", params={"period": "bad"})
    assert resp.status_code == 422
