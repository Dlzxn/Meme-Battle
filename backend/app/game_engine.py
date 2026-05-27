"""Core game logic: round management, timers, card operations."""
import asyncio
import logging
import random
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal
from app.models import (
    Room, Player, Meme, PlayerCard, Round, Play, Vote,
    RoundStatus, RoomStatus, GameMode, SituationCategory, Situation
)
from app.connection_manager import manager

logger = logging.getLogger(__name__)

# Strong-reference set so background tasks aren't GC'd before they finish.
_bg_tasks: set = set()

# Rounds that have been finalized early (all voted before timer expired).
# vote_timer / play_timer check this to stop broadcasting stale ticks.
_cancelled_rounds: set[int] = set()


def _bg(coro) -> asyncio.Task:
    t = asyncio.create_task(coro)
    _bg_tasks.add(t)
    t.add_done_callback(_bg_tasks.discard)
    t.add_done_callback(_log_bg_error)
    return t


def _log_bg_error(task: asyncio.Task) -> None:
    if task.cancelled():
        return
    try:
        exc = task.exception()
    except Exception:
        return
    if exc:
        logger.exception(
            "Background task failed: %s", exc,
            exc_info=(type(exc), exc, exc.__traceback__),
        )


PACK_UNLOCK_THRESHOLDS = {10: "classic_internet", 25: "russian_segment", 50: "gaming"}
SPECIAL_CARD_CHANCE = 0.08


async def deal_cards(db: AsyncSession, player: Player, count: int, category: str = "starter") -> list[Meme]:
    """Deal `count` random non-special memes to a player, avoiding duplicates."""
    held_ids = [pc.meme_id for pc in player.cards]

    query = select(Meme).where(
        Meme.category.in_(["starter", category]),
        Meme.is_special == False,  # noqa: E712
    )
    if held_ids:
        query = query.where(Meme.id.not_in(held_ids))
    query = query.order_by(func.random()).limit(count)

    result = await db.execute(query)
    memes = list(result.scalars().all())

    # Occasionally inject a special card
    if random.random() < SPECIAL_CARD_CHANCE:
        special_q = select(Meme).where(Meme.is_special == True).order_by(func.random()).limit(1)  # noqa: E712
        sr = await db.execute(special_q)
        special = sr.scalar_one_or_none()
        if special and special.id not in held_ids:
            memes.append(special)

    cards = [PlayerCard(player_id=player.id, meme_id=m.id) for m in memes]
    db.add_all(cards)
    await db.flush()
    return memes


async def get_room_with_players(db: AsyncSession, room_code: str) -> Optional[Room]:
    result = await db.execute(
        select(Room)
        .where(Room.code == room_code)
        .options(
            selectinload(Room.players).selectinload(Player.cards).selectinload(PlayerCard.meme)
        )
    )
    return result.scalar_one_or_none()


async def get_active_players(db: AsyncSession, room_code: str) -> list[Player]:
    result = await db.execute(
        select(Player)
        .join(Room, Player.room_id == Room.id)
        .where(Room.code == room_code, Player.is_connected == True)  # noqa: E712
        .options(selectinload(Player.cards).selectinload(PlayerCard.meme))
        .execution_options(populate_existing=True)
    )
    return list(result.scalars().all())


def player_card_list(player: Player) -> list[dict]:
    return [
        {
            "card_id": pc.id,
            "meme_id": pc.meme_id,
            "url": pc.meme.url,
            "name": pc.meme.name,
            "is_special": pc.meme.is_special,
            "special_type": pc.meme.special_type.value if pc.meme.special_type else None,
        }
        for pc in player.cards
    ]


async def broadcast_room_state(db: AsyncSession, room_code: str) -> None:
    players = await get_active_players(db, room_code)
    room_q = await db.execute(select(Room).where(Room.code == room_code))
    room = room_q.scalar_one_or_none()

    config: dict = {}
    if room:
        config = {
            "mode": room.mode.value,
            "category": room.category.value,
            "timer_play": room.timer_play,
            "timer_vote": room.timer_vote,
            "cards_count": room.cards_count,
            "penalty_count": room.penalty_count,
            "rounds_count": room.rounds_count,
            "is_public": room.is_public,
            "custom_situations": room.custom_situations,
        }

    await manager.broadcast(
        room_code,
        {
            "type": "room_updated",
            "payload": {
                "players": [
                    {
                        "id": p.id,
                        "nickname": p.nickname,
                        "is_host": p.is_host,
                        "is_connected": p.is_connected,
                        "card_count": len(p.cards),
                    }
                    for p in players
                ],
                "config": config,
            },
        },
    )


async def pick_situation(db: AsyncSession, room: Room, used_ids: list[int]) -> tuple[str, Optional[int]]:
    if room.custom_situations:
        lines = [ln.strip() for ln in room.custom_situations.splitlines() if ln.strip()]
        if lines:
            used_texts_q = await db.execute(
                select(Round.situation_text)
                .where(Round.room_id == room.id, Round.situation_text.in_(lines))
            )
            used_texts = set(used_texts_q.scalars().all())
            remaining = [l for l in lines if l not in used_texts]
            if remaining:
                return random.choice(remaining), None
            # All custom situations exhausted — fall through to DB situations

    query = select(Situation)
    if room.category != SituationCategory.all:
        query = query.where(Situation.category == room.category)
    if used_ids:
        query = query.where(Situation.id.not_in(used_ids))
    query = query.order_by(func.random()).limit(1)
    result = await db.execute(query)
    sit = result.scalar_one_or_none()

    if not sit:
        # All situations used — pick any
        result = await db.execute(select(Situation).order_by(func.random()).limit(1))
        sit = result.scalar_one_or_none()

    return (sit.text, sit.id) if sit else ("Что бы вы сделали?", None)


async def clear_player_cards(db: AsyncSession, player_id: int) -> None:
    """Remove all cards from a player's hand."""
    await db.execute(
        select(PlayerCard).where(PlayerCard.player_id == player_id)
    )
    from sqlalchemy import delete as sa_delete
    await db.execute(sa_delete(PlayerCard).where(PlayerCard.player_id == player_id))


async def start_round(db: AsyncSession, room: Room, room_code: str, round_number: int) -> None:
    players = await get_active_players(db, room_code)
    if not players:
        return

    # In arena mode, deal fresh cards to all players at the start of each round
    if room.mode == GameMode.arena:
        for p in players:
            await clear_player_cards(db, p.id)
        await db.flush()
        for p in players:
            p.cards = []  # clear identity map
            await deal_cards(db, p, room.cards_count)
        await db.flush()
        # Reload with fresh cards
        players = await get_active_players(db, room_code)

    used_q = await db.execute(
        select(Round.situation_id).where(
            Round.room_id == room.id, Round.situation_id.isnot(None)
        )
    )
    used_ids = [r for r in used_q.scalars().all() if r]

    situation_text, situation_id = await pick_situation(db, room, used_ids)

    czar_id: Optional[int] = None
    if room.mode == GameMode.czar:
        sorted_players = sorted(players, key=lambda p: p.czar_order)
        czar = sorted_players[round_number % len(sorted_players)]
        czar_id = czar.id

    round_ = Round(
        room_id=room.id,
        situation_id=situation_id,
        situation_text=situation_text,
        czar_id=czar_id,
        status=RoundStatus.playing,
        round_number=round_number,
    )
    db.add(round_)
    await db.flush()

    await db.flush()

    # Commit round before sending cards so cards are in a stable state
    await db.commit()

    for p in players:
        # Query cards directly to avoid stale identity-map data
        cards_q = await db.execute(
            select(PlayerCard)
            .where(PlayerCard.player_id == p.id)
            .options(selectinload(PlayerCard.meme))
        )
        fresh_cards = list(cards_q.scalars().all())
        your_cards = [
            {
                "card_id": pc.id,
                "meme_id": pc.meme_id,
                "url": pc.meme.url,
                "name": pc.meme.name,
                "is_special": pc.meme.is_special,
                "special_type": pc.meme.special_type.value if pc.meme.special_type else None,
            }
            for pc in fresh_cards
        ]
        await manager.send_personal(
            p.id,
            room_code,
            {
                "type": "situation_dealt",
                "payload": {
                    "round_id": round_.id,
                    "round_number": round_number,
                    "situation": situation_text,
                    "your_cards": your_cards,
                    "czar_id": czar_id,
                    "is_czar": p.id == czar_id,
                    "timer": room.timer_play,
                },
            },
        )

    _bg(play_timer(room.id, room_code, round_.id, room.timer_play))


# ──────────────────────────────────────────────────────────────
# Timers — use AsyncSessionLocal directly (no SessionClass arg)
# ──────────────────────────────────────────────────────────────

async def play_timer(room_id: int, room_code: str, round_id: int, seconds: int) -> None:
    for tick in range(seconds, 0, -1):
        await asyncio.sleep(1)
        if round_id in _cancelled_rounds:
            return
        await manager.broadcast(
            room_code, {"type": "timer_tick", "payload": {"phase": "play", "seconds": tick - 1}}
        )
    if round_id in _cancelled_rounds:
        return
    async with AsyncSessionLocal() as db:
        await _auto_play_missing(db, room_code, round_id)


async def vote_timer(room_id: int, room_code: str, round_id: int, seconds: int) -> None:
    for tick in range(seconds, 0, -1):
        await asyncio.sleep(1)
        if round_id in _cancelled_rounds:
            return
        await manager.broadcast(
            room_code, {"type": "timer_tick", "payload": {"phase": "vote", "seconds": tick - 1}}
        )
    if round_id in _cancelled_rounds:
        return
    async with AsyncSessionLocal() as db:
        await finalize_round(db, room_code, round_id)


async def _auto_play_missing(db: AsyncSession, room_code: str, round_id: int) -> None:
    round_ = await db.get(Round, round_id)
    if not round_ or round_.status != RoundStatus.playing:
        return

    played_q = await db.execute(select(Play.player_id).where(Play.round_id == round_id))
    played_ids = set(played_q.scalars().all())

    players = await get_active_players(db, room_code)
    room = await db.get(Room, round_.room_id)

    for p in players:
        if p.id in played_ids:
            continue
        if room.mode == GameMode.czar and p.id == round_.czar_id:
            continue
        if not p.cards:
            continue
        card = random.choice(p.cards)
        play = Play(round_id=round_id, player_id=p.id, meme_id=card.meme_id)
        db.add(play)
        await db.delete(card)
        await db.flush()
        await manager.broadcast(room_code, {"type": "player_played", "payload": {"player_id": p.id}})

    # Atomic update: only proceed if round is still in playing state
    upd = await db.execute(
        update(Round)
        .where(Round.id == round_id, Round.status == RoundStatus.playing)
        .values(status=RoundStatus.voting)
        .returning(Round.id)
    )
    await db.flush()
    if upd.scalar_one_or_none() is None:
        return  # Another path already advanced the round
    await db.commit()
    await _start_voting(db, room_code, round_id)


async def _start_voting(db: AsyncSession, room_code: str, round_id: int) -> None:
    round_ = await db.get(Round, round_id)
    if not round_:
        return

    room = await db.get(Room, round_.room_id)

    plays_q = await db.execute(
        select(Play)
        .where(Play.round_id == round_id)
        .options(selectinload(Play.meme), selectinload(Play.second_meme))
    )
    plays = list(plays_q.scalars().all())
    random.shuffle(plays)

    anonymous_plays = [
        {
            "play_id": pl.id,
            "player_id": pl.player_id,
            "meme_url": pl.meme.url,
            "meme_name": pl.meme.name,
            "second_meme_url": pl.second_meme.url if pl.second_meme else None,
        }
        for pl in plays
    ]

    if room.mode == GameMode.czar:
        players = await get_active_players(db, room_code)
        for p in players:
            await manager.send_personal(
                p.id,
                room_code,
                {
                    "type": "voting_started",
                    "payload": {
                        "round_id": round_id,
                        "plays": anonymous_plays,
                        "mode": "czar" if p.id == round_.czar_id else "czar_waiting",
                        "timer": room.timer_vote,
                    },
                },
            )
    else:
        await manager.broadcast(
            room_code,
            {
                "type": "voting_started",
                "payload": {
                    "round_id": round_id,
                    "plays": anonymous_plays,
                    "mode": "vote",
                    "timer": room.timer_vote,
                },
            },
        )

    _bg(vote_timer(room.id, room_code, round_id, room.timer_vote))


async def _schedule_next_round(room_code: str, room_id: int, next_round_number: int, delay: float) -> None:
    await asyncio.sleep(delay)
    async with AsyncSessionLocal() as db:
        room = await db.get(Room, room_id)
        if room and room.status == RoomStatus.playing:
            await start_round(db, room, room_code, next_round_number)


async def _schedule_arena_end(room_code: str, room_id: int, delay: float) -> None:
    await asyncio.sleep(delay)
    async with AsyncSessionLocal() as db:
        room = await db.get(Room, room_id)
        if not room:
            return
        players = await get_active_players(db, room_code)
        await _end_arena_game(db, room_code, room, players)


async def _schedule_game_end(room_code: str, room_id: int, winner_player_id: int, delay: float) -> None:
    await asyncio.sleep(delay)
    async with AsyncSessionLocal() as db:
        room = await db.get(Room, room_id)
        if not room:
            return
        players = await get_active_players(db, room_code)
        winner = next((p for p in players if p.id == winner_player_id), None)
        if winner:
            await _end_game(db, room_code, room, players, winner)


async def finalize_round(db: AsyncSession, room_code: str, round_id: int) -> None:
    # Atomic status update — prevents double-finalization from timer + last vote
    upd = await db.execute(
        update(Round)
        .where(Round.id == round_id, Round.status.in_([RoundStatus.playing, RoundStatus.voting]))
        .values(status=RoundStatus.finished)
        .returning(Round.id)
    )
    await db.flush()
    if upd.scalar_one_or_none() is None:
        return  # Already finalized

    _cancelled_rounds.add(round_id)  # Stop lingering play/vote timers

    round_ = await db.get(Round, round_id)
    room = await db.get(Room, round_.room_id)

    plays_q = await db.execute(
        select(Play)
        .where(Play.round_id == round_id)
        .options(
            selectinload(Play.meme),
            selectinload(Play.player),
            selectinload(Play.votes_received),
            selectinload(Play.reactions),
        )
    )
    plays = list(plays_q.scalars().all())

    if not plays:
        await manager.broadcast(
            room_code,
            {
                "type": "round_result",
                "payload": {
                    "round_id": round_id,
                    "plays": [],
                    "is_tie": True,
                    "winners": [],
                    "losers": [],
                    "game_over": False,
                    "round_number": round_.round_number,
                    "rounds_total": room.rounds_count if room.mode == GameMode.arena else None,
                },
            },
        )
        await db.commit()
        if room.mode == GameMode.arena:
            if round_.round_number >= room.rounds_count:
                _bg(_schedule_arena_end(room_code, room.id, delay=3))
            else:
                _bg(_schedule_next_round(room_code, room.id, round_.round_number + 1, delay=5))
        else:
            _bg(_schedule_next_round(room_code, room.id, round_.round_number + 1, delay=5))
        return

    play_results = []
    for pl in plays:
        vote_count = len(pl.votes_received)
        reactions_map: dict[str, int] = {}
        for r in pl.reactions:
            reactions_map[r.type.value] = reactions_map.get(r.type.value, 0) + 1
        play_results.append(
            {
                "play_id": pl.id,
                "player_id": pl.player_id,
                "nickname": pl.player.nickname,
                "meme_url": pl.meme.url,
                "meme_name": pl.meme.name,
                "vote_count": vote_count,
                "reactions": reactions_map,
            }
        )

    max_votes = max(p["vote_count"] for p in play_results)
    min_votes = min(p["vote_count"] for p in play_results)

    winners = [p for p in play_results if p["vote_count"] == max_votes]
    losers  = [p for p in play_results if p["vote_count"] == min_votes]
    is_tie  = len(winners) > 1 and max_votes == min_votes

    if room.mode != GameMode.arena and not is_tie and losers[0]["player_id"] != winners[0]["player_id"]:
        # Load loser with cards for penalty logic
        loser_q = await db.execute(
            select(Player)
            .where(Player.id == losers[0]["player_id"])
            .options(selectinload(Player.cards).selectinload(PlayerCard.meme))
        )
        loser_player = loser_q.scalar_one_or_none()
        if loser_player:
            await _check_skip_penalty(db, room_code, loser_player, room)

    await db.commit()

    players = await get_active_players(db, room_code)

    if room.mode == GameMode.arena:
        # Arena: game ends after rounds_count rounds
        game_over = round_.round_number >= room.rounds_count
        await manager.broadcast(
            room_code,
            {
                "type": "round_result",
                "payload": {
                    "round_id": round_id,
                    "plays": play_results,
                    "is_tie": is_tie,
                    "winners": [w["player_id"] for w in winners] if not is_tie else [],
                    "losers": [],
                    "game_over": game_over,
                    "round_number": round_.round_number,
                    "rounds_total": room.rounds_count,
                },
            },
        )
        if game_over:
            _bg(_schedule_arena_end(room_code, room.id, delay=3))
        else:
            _bg(_schedule_next_round(room_code, room.id, round_.round_number + 1, delay=5))
        return

    winner_player = next((p for p in players if len(p.cards) == 0), None)

    await manager.broadcast(
        room_code,
        {
            "type": "round_result",
            "payload": {
                "round_id": round_id,
                "plays": play_results,
                "is_tie": is_tie,
                "winners": [w["player_id"] for w in winners] if not is_tie else [],
                "losers":  [l["player_id"] for l in losers]  if not is_tie else [],
                "game_over": winner_player is not None,
            },
        },
    )

    if winner_player:
        _bg(_schedule_game_end(room_code, room.id, winner_player.id, delay=3))
        return

    _bg(_schedule_next_round(room_code, room.id, round_.round_number + 1, delay=5))


async def _check_skip_penalty(db: AsyncSession, room_code: str, player: Player, room: Room) -> None:
    """Give penalty cards unless player uses skip_penalty special."""
    skip_card = next(
        (
            pc for pc in player.cards
            if pc.meme.is_special
            and pc.meme.special_type
            and pc.meme.special_type.value == "skip_penalty"
        ),
        None,
    )
    if skip_card:
        await db.delete(skip_card)
        await db.flush()
        await manager.send_personal(
            player.id,
            room_code,
            {"type": "special_used", "payload": {"type": "skip_penalty", "message": "Штраф отменён!"}},
        )
        return

    penalty_memes = await _get_random_memes(db, room.penalty_count, [pc.meme_id for pc in player.cards])
    new_cards = [PlayerCard(player_id=player.id, meme_id=m.id) for m in penalty_memes]
    db.add_all(new_cards)
    await db.flush()

    await manager.send_personal(
        player.id,
        room_code,
        {
            "type": "cards_received",
            "payload": {
                "cards": [
                    {
                        "card_id": nc.id,
                        "meme_id": m.id,
                        "url": m.url,
                        "name": m.name,
                        "is_special": m.is_special,
                    }
                    for nc, m in zip(new_cards, penalty_memes)
                ],
                "reason": "penalty",
            },
        },
    )


async def _get_random_memes(db: AsyncSession, count: int, exclude_ids: list[int]) -> list[Meme]:
    q = select(Meme).where(Meme.is_special == False)  # noqa: E712  # noqa: E712
    if exclude_ids:
        q = q.where(Meme.id.not_in(exclude_ids))
    q = q.order_by(func.random()).limit(count)
    result = await db.execute(q)
    return list(result.scalars().all())


async def _end_arena_game(db: AsyncSession, room_code: str, room: Room, players: list[Player]) -> None:
    """End arena game: tally total votes per player across all rounds."""
    from sqlalchemy import func as sqlfunc
    # Count total votes received by each player in this room
    votes_q = await db.execute(
        select(Vote.target_player_id, sqlfunc.count(Vote.id).label("total"))
        .join(Round, Vote.round_id == Round.id)
        .where(Round.room_id == room.id)
        .group_by(Vote.target_player_id)
    )
    vote_totals: dict[int, int] = {row.target_player_id: row.total for row in votes_q}

    scores = []
    for p in players:
        scores.append({
            "player_id": p.id,
            "nickname": p.nickname,
            "votes": vote_totals.get(p.id, 0),
        })
    scores.sort(key=lambda x: x["votes"], reverse=True)

    winner = scores[0] if scores else None
    room.status = RoomStatus.finished
    await db.commit()

    await manager.broadcast(
        room_code,
        {
            "type": "game_over",
            "payload": {
                "winner_id": winner["player_id"] if winner else None,
                "winner_nickname": winner["nickname"] if winner else "—",
                "leaderboard": scores,
                "mode": "arena",
            },
        },
    )

    # Update stats
    for p in players:
        if not p.user_id:
            continue
        from app.models import GameStats
        stats_q = await db.execute(select(GameStats).where(GameStats.user_id == p.user_id))
        stats = stats_q.scalar_one_or_none()
        if not stats:
            stats = GameStats(user_id=p.user_id)
            db.add(stats)
        stats.games_played += 1
        if winner and p.id == winner["player_id"]:
            stats.games_won += 1
        await db.flush()
    await db.commit()


async def _end_game(
    db: AsyncSession, room_code: str, room: Room, players: list[Player], winner: Player
) -> None:
    room.status = RoomStatus.finished
    await db.commit()

    leaderboard = sorted(players, key=lambda p: len(p.cards))
    await manager.broadcast(
        room_code,
        {
            "type": "game_over",
            "payload": {
                "winner_id": winner.id,
                "winner_nickname": winner.nickname,
                "leaderboard": [
                    {"player_id": p.id, "nickname": p.nickname, "cards_left": len(p.cards)}
                    for p in leaderboard
                ],
            },
        },
    )

    # Update stats for registered players
    for p in players:
        if not p.user_id:
            continue
        from app.models import GameStats, UnlockedPack

        stats_q = await db.execute(select(GameStats).where(GameStats.user_id == p.user_id))
        stats = stats_q.scalar_one_or_none()
        if not stats:
            stats = GameStats(user_id=p.user_id)
            db.add(stats)
        stats.games_played += 1
        if p.id == winner.id:
            stats.games_won += 1
        await db.flush()

        for threshold, pack_name in PACK_UNLOCK_THRESHOLDS.items():
            if stats.games_played >= threshold:
                ex = await db.execute(
                    select(UnlockedPack).where(
                        UnlockedPack.user_id == p.user_id,
                        UnlockedPack.pack_name == pack_name,
                    )
                )
                if not ex.scalar_one_or_none():
                    db.add(UnlockedPack(user_id=p.user_id, pack_name=pack_name))

    await db.commit()
