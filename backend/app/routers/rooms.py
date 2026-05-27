import random
import string

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Room, Player, User, RoomStatus
from app.schemas import RoomCreate, RoomOut
from app.auth import get_current_user, require_user

router = APIRouter(prefix="/api/rooms", tags=["rooms"])


def gen_code() -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=6))


@router.post("", status_code=201)
async def create_room(data: RoomCreate, db: AsyncSession = Depends(get_db), user: User | None = Depends(get_current_user)):
    code = gen_code()
    while (await db.execute(select(Room).where(Room.code == code))).scalar_one_or_none():
        code = gen_code()

    room = Room(
        code=code,
        mode=data.mode,
        category=data.category,
        timer_play=data.timer_play,
        timer_vote=data.timer_vote,
        cards_count=data.cards_count,
        penalty_count=data.penalty_count,
        rounds_count=data.rounds_count,
        is_public=data.is_public,
        custom_situations=data.custom_situations,
    )
    db.add(room)
    await db.flush()

    player = Player(
        room_id=room.id,
        user_id=user.id if user else None,
        nickname=data.nickname if not user else user.username,
        is_host=True,
        czar_order=0,
    )
    db.add(player)
    await db.flush()
    room.host_id = player.id
    await db.commit()

    return {"room_code": code, "player_id": player.id}


@router.post("/{code}/join")
async def join_room(
    code: str,
    nickname: str,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    result = await db.execute(
        select(Room).where(Room.code == code.upper()).options(selectinload(Room.players))
    )
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if room.status != RoomStatus.waiting:
        raise HTTPException(status_code=400, detail="Game already started")

    active = [p for p in room.players if p.is_connected]
    if len(active) >= 8:
        raise HTTPException(status_code=400, detail="Room is full")

    # Reconnect logic: same user or same nickname
    existing = None
    if user:
        existing = next((p for p in room.players if p.user_id == user.id), None)
    if not existing:
        existing = next((p for p in room.players if p.nickname == nickname and not p.is_connected), None)

    if existing:
        existing.is_connected = True
        await db.commit()
        return {"room_code": code, "player_id": existing.id}

    order = max((p.czar_order for p in room.players), default=-1) + 1
    player = Player(
        room_id=room.id,
        user_id=user.id if user else None,
        nickname=nickname if not user else user.username,
        is_host=False,
        czar_order=order,
    )
    db.add(player)
    await db.commit()
    return {"room_code": code, "player_id": player.id}


@router.get("/public", response_model=list[RoomOut])
async def list_public_rooms(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Room)
        .where(Room.is_public == True, Room.status == RoomStatus.waiting)
        .options(selectinload(Room.players))
        .order_by(Room.created_at.desc())
        .limit(50)
    )
    rooms = result.scalars().all()
    out = []
    for r in rooms:
        active = [p for p in r.players if p.is_connected]
        out.append(
            RoomOut(
                id=r.id,
                code=r.code,
                status=r.status.value,
                mode=r.mode.value,
                timer_play=r.timer_play,
                timer_vote=r.timer_vote,
                cards_count=r.cards_count,
                penalty_count=r.penalty_count,
                rounds_count=r.rounds_count,
                is_public=r.is_public,
                category=r.category.value,
                player_count=len(active),
            )
        )
    return out


@router.get("/{code}/status")
async def room_status(code: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Room).where(Room.code == code.upper()).options(selectinload(Room.players))
    )
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    active = [p for p in room.players if p.is_connected]
    return {
        "code": room.code,
        "status": room.status.value,
        "mode": room.mode.value,
        "player_count": len(active),
    }


@router.delete("/{code}/kick/{player_id}")
async def kick_player(
    code: str,
    player_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
):
    result = await db.execute(
        select(Room).where(Room.code == code).options(selectinload(Room.players))
    )
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    host = next((p for p in room.players if p.user_id == user.id and p.is_host), None)
    if not host:
        raise HTTPException(status_code=403, detail="Only host can kick")

    target = next((p for p in room.players if p.id == player_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Player not found")

    target.is_connected = False
    await db.commit()
    return {"ok": True}
