"""Tests for /api/auth/* endpoints."""
import pytest
from httpx import AsyncClient

from app.auth import create_access_token
from app.models import User
from app.auth import hash_password


async def test_register_success(client: AsyncClient):
    resp = await client.post("/api/auth/register", json={"username": "newuser", "password": "secret"})
    assert resp.status_code == 201
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


async def test_register_duplicate_username(client: AsyncClient, user1):
    resp = await client.post("/api/auth/register", json={"username": "player1", "password": "anything"})
    assert resp.status_code == 400
    assert "taken" in resp.json()["detail"].lower()


async def test_register_username_too_short(client: AsyncClient):
    resp = await client.post("/api/auth/register", json={"username": "a", "password": "secret"})
    assert resp.status_code == 422


async def test_register_username_too_long(client: AsyncClient):
    resp = await client.post("/api/auth/register", json={"username": "x" * 51, "password": "secret"})
    assert resp.status_code == 422


async def test_register_username_strip_whitespace(client: AsyncClient):
    # Leading/trailing whitespace stripped — valid after strip
    resp = await client.post("/api/auth/register", json={"username": "  ok  ", "password": "secret"})
    assert resp.status_code == 201


async def test_login_success(client: AsyncClient, user1):
    resp = await client.post("/api/auth/login", json={"username": "player1", "password": "pass1"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


async def test_login_wrong_password(client: AsyncClient, user1):
    resp = await client.post("/api/auth/login", json={"username": "player1", "password": "wrong"})
    assert resp.status_code == 401


async def test_login_unknown_user(client: AsyncClient):
    resp = await client.post("/api/auth/login", json={"username": "nobody", "password": "pass"})
    assert resp.status_code == 401


async def test_me_authenticated(client: AsyncClient, user1, headers1):
    resp = await client.get("/api/auth/me", headers=headers1)
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "player1"
    assert body["id"] == user1.id


async def test_me_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401


async def test_me_invalid_token(client: AsyncClient):
    resp = await client.get("/api/auth/me", headers={"Authorization": "Bearer bogus.token.here"})
    assert resp.status_code == 401


async def test_me_expired_token(client: AsyncClient, user1):
    from datetime import datetime, timedelta
    from jose import jwt
    from app.config import settings
    payload = {"sub": str(user1.id), "exp": datetime.utcnow() - timedelta(seconds=1)}
    expired_token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    resp = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert resp.status_code == 401
