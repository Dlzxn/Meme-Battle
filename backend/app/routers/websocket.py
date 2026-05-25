"""WebSocket endpoint — handles all real-time game events."""
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db, AsyncSessionLocal
from app.models import (
    Room, Player, Play, Vote, Reaction, Round, PlayerCard, Meme,
    RoomStatus, RoundStatus, GameMode, ReactionType
)
from app.connection_manager import manager
from app.game_engine import (
    start_round, finalize_round, broadcast_room_state,
    deal_cards, player_card_list, get_active_players, _check_skip_penalty
)

router = APIRouter(tags=["websocket"])
logger = logging.getLogger(__name__)


@router.websocket("/ws/{room_code}/{player_id}")
async def websocket_endpoint(websocket: WebSocket, room_code: str, player_id: int):
    await manager.connect(websocket, room_code, player_id)

    async with AsyncSessionLocal() as db:
        player = await _load_player(db, player_id, room_code)
        if not player:
            await websocket.close(code=4004)
            return

        player.is_connected = True
        await db.commit()
        await broadcast_room_state(db, room_code)

    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            event_type = msg.get("type")
            payload = msg.get("payload", {})

            async with AsyncSessionLocal() as db:
                player = await _load_player(db, player_id, room_code)
                if not player:
                    break
                await _dispatch(db, event_type, payload, player, room_code)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.exception("WS error: %s", e)
    finally:
        manager.disconnect(room_code, player_id)
        async with AsyncSessionLocal() as db:
            await _handle_disconnect(db, player_id, room_code)


async def _load_player(db: AsyncSession, player_id: int, room_code: str) -> Player | None:
    result = await db.execute(
        select(Player)
        .join(Room, Player.room_id == Room.id)
        .where(Player.id == player_id, Room.code == room_code)
        .options(
            selectinload(Player.cards).selectinload(PlayerCard.meme),
            selectinload(Player.room),
        )
    )
    return result.scalar_one_or_none()


async def _dispatch(db: AsyncSession, event_type: str, payload: dict, player: Player, room_code: str) -> None:
    handlers = {
        "start_game": _handle_start_game,
        "play_card": _handle_play_card,
        "vote": _handle_vote,
        "add_reaction": _handle_reaction,
        "czar_pick": _handle_czar_pick,
        "use_special_card": _handle_special_card,
    }
    handler = handlers.get(event_type)
    if handler:
        await handler(db, payload, player, room_code)


async def _handle_start_game(db: AsyncSession, payload: dict, player: Player, room_code: str) -> None:
    if not player.is_host:
        return

    room = await db.get(Room, player.room_id)
    if not room or room.status != RoomStatus.waiting:
        return

    players = await get_active_players(db, room_code)
    if len(players) < 2:
        await manager.send_personal(
            player.id, room_code,
            {"type": "error", "payload": {"message": "Минимум 2 игрока для старта"}}
        )
        return

    room.status = RoomStatus.playing
    await db.flush()

    # Deal starting cards
    for p in players:
        await deal_cards(db, p, room.cards_count)

    await db.commit()

    # Reload with cards
    players = await get_active_players(db, room_code)

    await manager.broadcast(room_code, {"type": "game_started", "payload": {}})
    await start_round(db, room, room_code, round_number=1)


async def _handle_play_card(db: AsyncSession, payload: dict, player: Player, room_code: str) -> None:
    card_id = payload.get("card_id")
    second_card_id = payload.get("second_card_id")

    # Find active round
    round_ = await _get_active_round(db, player.room_id)
    if not round_ or round_.status != RoundStatus.playing:
        return

    room = await db.get(Room, player.room_id)
    if room.mode == GameMode.czar and player.id == round_.czar_id:
        return  # czar doesn't play

    # Check already played
    existing = await db.execute(select(Play).where(Play.round_id == round_.id, Play.player_id == player.id))
    if existing.scalar_one_or_none():
        return

    # Validate card ownership
    card = next((pc for pc in player.cards if pc.id == card_id), None)
    if not card:
        return

    # Handle double_play special card
    second_meme_id = None
    if second_card_id:
        # Validate player has a double_play special
        double_card = next(
            (pc for pc in player.cards if pc.meme.is_special and pc.meme.special_type and pc.meme.special_type.value == "double_play"),
            None,
        )
        second_card = next((pc for pc in player.cards if pc.id == second_card_id), None)
        if double_card and second_card:
            second_meme_id = second_card.meme_id
            db.delete(double_card)

    play = Play(round_id=round_.id, player_id=player.id, meme_id=card.meme_id, second_meme_id=second_meme_id)
    db.add(play)
    db.delete(card)
    if second_card_id and second_meme_id:
        second_card = next((pc for pc in player.cards if pc.id == second_card_id), None)
        if second_card:
            db.delete(second_card)

    await db.flush()

    await manager.broadcast(room_code, {"type": "player_played", "payload": {"player_id": player.id}})

    # Check if everyone played
    plays_q = await db.execute(select(Play).where(Play.round_id == round_.id))
    plays = list(plays_q.scalars().all())

    active_players = await get_active_players(db, room_code)
    expected = len(active_players) - (1 if room.mode == GameMode.czar else 0)

    if len(plays) >= expected:
        round_.status = RoundStatus.voting
        await db.commit()
        from app.game_engine import _start_voting
        await _start_voting(db, room_code, round_.id)
    else:
        await db.commit()


async def _handle_vote(db: AsyncSession, payload: dict, player: Player, room_code: str) -> None:
    target_player_id = payload.get("target_player_id")
    play_id = payload.get("play_id")

    round_ = await _get_active_round(db, player.room_id)
    if not round_ or round_.status != RoundStatus.voting:
        return

    # Can't vote for yourself
    if target_player_id == player.id:
        return

    # Check already voted
    existing = await db.execute(select(Vote).where(Vote.round_id == round_.id, Vote.voter_id == player.id))
    if existing.scalar_one_or_none():
        return

    # Validate target play exists
    play_q = await db.execute(select(Play).where(Play.id == play_id, Play.round_id == round_.id))
    play = play_q.scalar_one_or_none()
    if not play:
        return

    vote = Vote(round_id=round_.id, voter_id=player.id, target_player_id=target_player_id, target_play_id=play_id)
    db.add(vote)
    await db.commit()

    await manager.broadcast(room_code, {"type": "vote_cast", "payload": {"voter_id": player.id}})

    # Check if all voted
    votes_q = await db.execute(select(Vote).where(Vote.round_id == round_.id))
    votes = list(votes_q.scalars().all())

    active_players = await get_active_players(db, room_code)
    plays_q = await db.execute(select(Play).where(Play.round_id == round_.id))
    plays_count = len(list(plays_q.scalars().all()))

    if len(votes) >= plays_count:
        await finalize_round(db, room_code, round_.id)


async def _handle_reaction(db: AsyncSession, payload: dict, player: Player, room_code: str) -> None:
    play_id = payload.get("play_id")
    reaction_type = payload.get("reaction_type")

    if reaction_type not in [r.value for r in ReactionType]:
        return

    # Check play exists
    play_q = await db.execute(select(Play).where(Play.id == play_id))
    play = play_q.scalar_one_or_none()
    if not play:
        return

    # One reaction per player per play
    existing = await db.execute(
        select(Reaction).where(Reaction.play_id == play_id, Reaction.player_id == player.id)
    )
    if existing.scalar_one_or_none():
        return

    reaction = Reaction(play_id=play_id, player_id=player.id, type=ReactionType(reaction_type))
    db.add(reaction)
    await db.commit()

    await manager.broadcast(
        room_code,
        {"type": "reaction_added", "payload": {"play_id": play_id, "reaction_type": reaction_type, "player_id": player.id}},
    )


async def _handle_czar_pick(db: AsyncSession, payload: dict, player: Player, room_code: str) -> None:
    winner_player_id = payload.get("winner_player_id")
    loser_player_id = payload.get("loser_player_id")

    round_ = await _get_active_round(db, player.room_id)
    if not round_ or round_.czar_id != player.id or round_.status != RoundStatus.voting:
        return

    room = await db.get(Room, player.room_id)

    # Add fake votes to represent czar's pick
    plays_q = await db.execute(select(Play).where(Play.round_id == round_.id))
    plays = list(plays_q.scalars().all())

    winner_play = next((p for p in plays if p.player_id == winner_player_id), None)
    if not winner_play:
        return

    # Simulate votes: winner gets 1, loser gets 0
    vote = Vote(
        round_id=round_.id,
        voter_id=player.id,
        target_player_id=winner_player_id,
        target_play_id=winner_play.id,
    )
    db.add(vote)
    await db.commit()

    await finalize_round(db, room_code, round_.id)


async def _handle_special_card(db: AsyncSession, payload: dict, player: Player, room_code: str) -> None:
    card_id = payload.get("card_id")
    target_player_id = payload.get("target_player_id")

    card = next((pc for pc in player.cards if pc.id == card_id), None)
    if not card or not card.meme.is_special:
        return

    special_type = card.meme.special_type.value if card.meme.special_type else None

    if special_type == "steal" and target_player_id:
        # Steal a random card from target
        target_q = await db.execute(
            select(Player).where(Player.id == target_player_id).options(
                selectinload(Player.cards).selectinload(PlayerCard.meme)
            )
        )
        target = target_q.scalar_one_or_none()
        if target and target.cards:
            import random
            stolen_card = random.choice(target.cards)
            stolen_card.player_id = player.id
            db.delete(card)
            await db.commit()

            await manager.send_personal(
                player.id, player.room.code,
                {"type": "card_stolen", "payload": {"meme_url": stolen_card.meme.url, "meme_name": stolen_card.meme.name}},
            )
            await manager.send_personal(
                target_player_id, player.room.code,
                {"type": "card_stolen_from_you", "payload": {"by_nickname": player.nickname}},
            )


async def _get_active_round(db: AsyncSession, room_id: int) -> Round | None:
    result = await db.execute(
        select(Round)
        .where(Round.room_id == room_id, Round.status.in_([RoundStatus.playing, RoundStatus.voting]))
        .order_by(Round.id.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _handle_disconnect(db: AsyncSession, player_id: int, room_code: str) -> None:
    result = await db.execute(
        select(Player).join(Room, Player.room_id == Room.id).where(Player.id == player_id, Room.code == room_code)
    )
    player = result.scalar_one_or_none()
    if not player:
        return

    player.is_connected = False
    room = await db.get(Room, player.room_id)

    await manager.broadcast(
        room_code,
        {"type": "player_disconnected", "payload": {"player_id": player_id, "nickname": player.nickname}},
    )

    if player.is_host and room and room.status == RoomStatus.waiting:
        # Transfer host
        active_q = await db.execute(
            select(Player).where(
                Player.room_id == player.room_id,
                Player.id != player_id,
                Player.is_connected == True,
            )
        )
        others = list(active_q.scalars().all())
        if others:
            new_host = others[0]
            new_host.is_host = True
            player.is_host = False
            room.host_id = new_host.id
            await db.flush()
            await manager.broadcast(
                room_code,
                {"type": "host_changed", "payload": {"new_host_id": new_host.id, "nickname": new_host.nickname}},
            )

    await db.commit()
    await broadcast_room_state(db, room_code)
