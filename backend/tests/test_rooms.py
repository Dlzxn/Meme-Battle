"""Tests for /api/rooms/* endpoints."""
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models import Room, Player, RoomStatus


async def _create_room(client: AsyncClient, headers=None, **overrides) -> dict:
    payload = {
        "nickname": "TestHost",
        "mode": "no_czar",
        "category": "all",
        "timer_play": 60,
        "timer_vote": 30,
        "cards_count": 7,
        "penalty_count": 1,
        "is_public": False,
        **overrides,
    }
    resp = await client.post("/api/rooms", json=payload, headers=headers or {})
    return resp


# ── Create room ───────────────────────────────────────────────


async def test_create_room_anonymous(client: AsyncClient):
    resp = await _create_room(client)
    assert resp.status_code == 201
    body = resp.json()
    assert "room_code" in body
    assert "player_id" in body
    assert len(body["room_code"]) == 6


async def test_create_room_authenticated(client: AsyncClient, user1, headers1):
    resp = await _create_room(client, headers=headers1)
    assert resp.status_code == 201


async def test_create_room_invalid_timer_play(client: AsyncClient):
    resp = await _create_room(client, timer_play=17)
    assert resp.status_code == 422


async def test_create_room_invalid_timer_vote(client: AsyncClient):
    resp = await _create_room(client, timer_vote=20)
    assert resp.status_code == 422


async def test_create_room_invalid_cards_count(client: AsyncClient):
    resp = await _create_room(client, cards_count=4)
    assert resp.status_code == 422


async def test_create_room_invalid_penalty_count(client: AsyncClient):
    resp = await _create_room(client, penalty_count=3)
    assert resp.status_code == 422


async def test_create_room_public(client: AsyncClient):
    resp = await _create_room(client, is_public=True)
    assert resp.status_code == 201


async def test_create_room_czar_mode(client: AsyncClient):
    resp = await _create_room(client, mode="czar")
    assert resp.status_code == 201


async def test_create_room_custom_situations(client: AsyncClient):
    resp = await _create_room(client, custom_situations="Situation 1\nSituation 2")
    assert resp.status_code == 201


# ── Join room ─────────────────────────────────────────────────


async def test_join_room_success(client: AsyncClient):
    create_resp = await _create_room(client)
    code = create_resp.json()["room_code"]

    join_resp = await client.post(f"/api/rooms/{code}/join", params={"nickname": "Guest"})
    assert join_resp.status_code == 200
    body = join_resp.json()
    assert body["room_code"] == code
    assert "player_id" in body


async def test_join_room_case_insensitive(client: AsyncClient):
    create_resp = await _create_room(client)
    code = create_resp.json()["room_code"]
    join_resp = await client.post(f"/api/rooms/{code.lower()}/join", params={"nickname": "Guest"})
    assert join_resp.status_code == 200


async def test_join_room_not_found(client: AsyncClient):
    resp = await client.post("/api/rooms/XXXXXX/join", params={"nickname": "Guest"})
    assert resp.status_code == 404


async def test_join_room_reconnect_by_nickname(client: AsyncClient, db, room_with_players):
    room, p1, p2 = room_with_players
    # Simulate p2 disconnected
    p2.is_connected = False
    await db.commit()

    join_resp = await client.post(
        f"/api/rooms/{room.code}/join", params={"nickname": p2.nickname}
    )
    assert join_resp.status_code == 200
    assert join_resp.json()["player_id"] == p2.id


async def test_join_room_reconnect_by_user_id(client: AsyncClient, db, room_with_players, user1, headers1):
    room, p1, p2 = room_with_players
    # Make p1 a registered user and simulate disconnect
    p1.user_id = user1.id
    p1.is_connected = False
    await db.commit()

    join_resp = await client.post(
        f"/api/rooms/{room.code}/join",
        params={"nickname": "SomeOtherNick"},
        headers=headers1,
    )
    assert join_resp.status_code == 200
    assert join_resp.json()["player_id"] == p1.id


async def test_join_room_full(client: AsyncClient, db, room_with_players):
    room, p1, p2 = room_with_players
    # Fill room to 8
    for i in range(6):
        p = Player(room_id=room.id, nickname=f"extra{i}", is_connected=True, czar_order=i + 2)
        db.add(p)
    await db.commit()

    resp = await client.post(f"/api/rooms/{room.code}/join", params={"nickname": "overflow"})
    assert resp.status_code == 400
    assert "full" in resp.json()["detail"].lower()


async def test_join_room_already_started(client: AsyncClient, db, room_with_players):
    room, p1, p2 = room_with_players
    room.status = RoomStatus.playing
    await db.commit()

    resp = await client.post(f"/api/rooms/{room.code}/join", params={"nickname": "Late"})
    assert resp.status_code == 400
    assert "started" in resp.json()["detail"].lower()


# ── Public rooms ──────────────────────────────────────────────


async def test_list_public_rooms_empty(client: AsyncClient):
    resp = await client.get("/api/rooms/public")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_public_rooms(client: AsyncClient):
    await _create_room(client, is_public=True, nickname="H1")
    await _create_room(client, is_public=True, nickname="H2")
    await _create_room(client, is_public=False, nickname="H3")

    resp = await client.get("/api/rooms/public")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    for r in data:
        assert r["is_public"] is True


async def test_list_public_rooms_excludes_started(client: AsyncClient, db, room_with_players):
    room, _, _ = room_with_players
    room.is_public = True
    room.status = RoomStatus.playing
    await db.commit()

    resp = await client.get("/api/rooms/public")
    assert resp.status_code == 200
    codes = [r["code"] for r in resp.json()]
    assert room.code not in codes


# ── Kick player ───────────────────────────────────────────────


async def test_kick_player_success(client: AsyncClient, db, room_with_players, user1, headers1):
    room, p1, p2 = room_with_players
    p1.user_id = user1.id
    await db.commit()

    resp = await client.delete(
        f"/api/rooms/{room.code}/kick/{p2.id}", headers=headers1
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    await db.refresh(p2)
    assert p2.is_connected is False


async def test_kick_player_not_host(client: AsyncClient, db, room_with_players, user2, headers2):
    room, p1, p2 = room_with_players
    p2.user_id = user2.id
    await db.commit()

    resp = await client.delete(
        f"/api/rooms/{room.code}/kick/{p1.id}", headers=headers2
    )
    assert resp.status_code == 403


async def test_kick_player_unauthenticated(client: AsyncClient, room_with_players):
    room, p1, p2 = room_with_players
    resp = await client.delete(f"/api/rooms/{room.code}/kick/{p2.id}")
    assert resp.status_code == 401


async def test_kick_player_room_not_found(client: AsyncClient, user1, headers1):
    resp = await client.delete("/api/rooms/ZZZZZZ/kick/999", headers=headers1)
    assert resp.status_code == 404


async def test_kick_player_target_not_found(client: AsyncClient, db, room_with_players, user1, headers1):
    room, p1, _ = room_with_players
    p1.user_id = user1.id
    await db.commit()

    resp = await client.delete(f"/api/rooms/{room.code}/kick/99999", headers=headers1)
    assert resp.status_code == 404
