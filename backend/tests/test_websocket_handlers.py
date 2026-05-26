"""Tests for WebSocket event handlers (called directly, not via network)."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.routers.websocket import (
    _handle_start_game, _handle_play_card, _handle_vote,
    _handle_reaction, _handle_czar_pick, _handle_disconnect,
    _get_active_round, _load_player,
)
from app.models import (
    Room, Player, Meme, PlayerCard, Round, Play, Vote, Reaction,
    RoundStatus, RoomStatus, GameMode, ReactionType, SpecialType,
)


async def _reload_player(db, player_id) -> Player:
    q = await db.execute(
        select(Player).where(Player.id == player_id)
        .options(selectinload(Player.cards).selectinload(PlayerCard.meme),
                 selectinload(Player.room))
    )
    return q.scalar_one()


# ── _handle_start_game ─────────────────────────────────────────


async def test_start_game_success(db, room_with_players, situations, mock_manager, mock_create_task):
    room, p1, p2 = room_with_players

    p1 = await _reload_player(db, p1.id)

    with patch("app.routers.websocket.deal_cards", new_callable=AsyncMock) as mock_deal, \
         patch("app.routers.websocket.start_round", new_callable=AsyncMock) as mock_start, \
         patch("app.routers.websocket.get_active_players", new_callable=AsyncMock) as mock_gap:
        mock_gap.return_value = [p1, p2]
        mock_deal.return_value = []

        await _handle_start_game(db, {}, p1, room.code)

    await db.refresh(room)
    assert room.status == RoomStatus.playing
    mock_manager.ws.broadcast.assert_called()


async def test_start_game_not_host(db, room_with_players, mock_manager):
    room, p1, p2 = room_with_players
    p2 = await _reload_player(db, p2.id)

    with patch("app.routers.websocket.get_active_players", new_callable=AsyncMock) as mock_gap:
        mock_gap.return_value = [p1, p2]
        await _handle_start_game(db, {}, p2, room.code)

    await db.refresh(room)
    assert room.status == RoomStatus.waiting  # not started


async def test_start_game_not_enough_players(db, room_with_players, mock_manager):
    room, p1, p2 = room_with_players
    p1 = await _reload_player(db, p1.id)

    with patch("app.routers.websocket.get_active_players", new_callable=AsyncMock) as mock_gap:
        mock_gap.return_value = [p1]  # only 1 player
        await _handle_start_game(db, {}, p1, room.code)

    mock_manager.ws.send_personal.assert_called_once()
    call_payload = mock_manager.ws.send_personal.call_args[0][2]
    assert call_payload["type"] == "error"


async def test_start_game_already_playing(db, room_with_players, mock_manager):
    room, p1, p2 = room_with_players
    room.status = RoomStatus.playing
    await db.commit()
    p1 = await _reload_player(db, p1.id)

    with patch("app.routers.websocket.get_active_players", new_callable=AsyncMock):
        await _handle_start_game(db, {}, p1, room.code)

    # Room should still be playing (didn't restart)
    await db.refresh(room)
    assert room.status == RoomStatus.playing


# ── _handle_play_card ──────────────────────────────────────────


async def _setup_playing_round(db, room, p1, p2):
    """Create an active round and deal 1 card to each player."""
    memes_q = await db.execute(
        select(Meme).where(Meme.is_special == False).limit(2)  # noqa: E712
    )
    memes = list(memes_q.scalars().all())

    pc1 = PlayerCard(player_id=p1.id, meme_id=memes[0].id)
    pc2 = PlayerCard(player_id=p2.id, meme_id=memes[1].id)
    db.add_all([pc1, pc2])

    rnd = Round(room_id=room.id, situation_text="T", round_number=1, status=RoundStatus.playing)
    db.add(rnd)
    await db.flush()
    await db.commit()
    return rnd, pc1, pc2


async def test_play_card_success(db, playing_room, mock_manager, mock_create_task):
    room, p1, p2 = playing_room
    rnd = Round(room_id=room.id, situation_text="T", round_number=1, status=RoundStatus.playing)
    db.add(rnd)
    await db.flush()
    await db.commit()

    p1 = await _reload_player(db, p1.id)
    card = p1.cards[0]

    with patch("app.routers.websocket.get_active_players", new_callable=AsyncMock) as mock_gap, \
         patch("app.game_engine._start_voting", new_callable=AsyncMock):
        mock_gap.return_value = [p1, p2]
        await _handle_play_card(db, {"card_id": card.id}, p1, room.code)

    plays_q = await db.execute(select(Play).where(Play.round_id == rnd.id))
    plays = plays_q.scalars().all()
    assert len(plays) == 1
    assert plays[0].player_id == p1.id


async def test_play_card_not_in_hand(db, playing_room, mock_manager, mock_create_task):
    room, p1, p2 = playing_room
    rnd = Round(room_id=room.id, situation_text="T", round_number=1, status=RoundStatus.playing)
    db.add(rnd)
    await db.flush()
    await db.commit()

    p1 = await _reload_player(db, p1.id)

    await _handle_play_card(db, {"card_id": 99999}, p1, room.code)

    plays_q = await db.execute(select(Play).where(Play.round_id == rnd.id))
    assert plays_q.scalars().first() is None


async def test_play_card_already_played(db, playing_room, mock_manager, mock_create_task):
    room, p1, p2 = playing_room
    rnd = Round(room_id=room.id, situation_text="T", round_number=1, status=RoundStatus.playing)
    db.add(rnd)
    await db.flush()

    memes_q = await db.execute(select(Meme).where(Meme.is_special == False).limit(1))  # noqa: E712
    m = memes_q.scalar_one()
    db.add(Play(round_id=rnd.id, player_id=p1.id, meme_id=m.id))
    await db.commit()

    p1 = await _reload_player(db, p1.id)
    card = p1.cards[0]
    await _handle_play_card(db, {"card_id": card.id}, p1, room.code)

    plays_q = await db.execute(select(Play).where(Play.round_id == rnd.id, Play.player_id == p1.id))
    assert len(plays_q.scalars().all()) == 1


# ── _handle_vote ───────────────────────────────────────────────


async def _setup_voting_round(db, room, p1, p2):
    memes_q = await db.execute(
        select(Meme).where(Meme.is_special == False).limit(2)  # noqa: E712
    )
    memes = list(memes_q.scalars().all())

    rnd = Round(room_id=room.id, situation_text="T", round_number=1, status=RoundStatus.voting)
    db.add(rnd)
    await db.flush()

    play1 = Play(round_id=rnd.id, player_id=p1.id, meme_id=memes[0].id)
    play2 = Play(round_id=rnd.id, player_id=p2.id, meme_id=memes[1].id)
    db.add_all([play1, play2])
    await db.flush()
    await db.commit()
    return rnd, play1, play2


async def test_vote_success(db, playing_room, mock_manager, mock_create_task):
    room, p1, p2 = playing_room
    rnd, play1, play2 = await _setup_voting_round(db, room, p1, p2)

    p1 = await _reload_player(db, p1.id)

    with patch("app.routers.websocket.get_active_players", new_callable=AsyncMock) as mock_gap, \
         patch("app.routers.websocket.finalize_round", new_callable=AsyncMock):
        mock_gap.return_value = [p1, p2]
        await _handle_vote(
            db, {"target_player_id": p2.id, "play_id": play2.id}, p1, room.code
        )

    votes_q = await db.execute(select(Vote).where(Vote.round_id == rnd.id))
    assert votes_q.scalar_one_or_none() is not None


async def test_vote_self_vote_rejected(db, playing_room, mock_manager, mock_create_task):
    room, p1, p2 = playing_room
    rnd, play1, play2 = await _setup_voting_round(db, room, p1, p2)
    p1 = await _reload_player(db, p1.id)

    await _handle_vote(
        db, {"target_player_id": p1.id, "play_id": play1.id}, p1, room.code
    )

    votes_q = await db.execute(select(Vote).where(Vote.round_id == rnd.id))
    assert votes_q.scalar_one_or_none() is None


async def test_vote_duplicate_rejected(db, playing_room, mock_manager, mock_create_task):
    room, p1, p2 = playing_room
    rnd, play1, play2 = await _setup_voting_round(db, room, p1, p2)
    p1 = await _reload_player(db, p1.id)

    with patch("app.routers.websocket.get_active_players", new_callable=AsyncMock) as mock_gap, \
         patch("app.routers.websocket.finalize_round", new_callable=AsyncMock):
        mock_gap.return_value = [p1, p2]
        await _handle_vote(db, {"target_player_id": p2.id, "play_id": play2.id}, p1, room.code)
        await _handle_vote(db, {"target_player_id": p2.id, "play_id": play2.id}, p1, room.code)

    votes_q = await db.execute(select(Vote).where(Vote.round_id == rnd.id))
    assert len(votes_q.scalars().all()) == 1


async def test_vote_invalid_play(db, playing_room, mock_manager, mock_create_task):
    room, p1, p2 = playing_room
    rnd, play1, play2 = await _setup_voting_round(db, room, p1, p2)
    p1 = await _reload_player(db, p1.id)

    await _handle_vote(db, {"target_player_id": p2.id, "play_id": 99999}, p1, room.code)

    votes_q = await db.execute(select(Vote).where(Vote.round_id == rnd.id))
    assert votes_q.scalar_one_or_none() is None


# ── _handle_reaction ───────────────────────────────────────────


async def test_reaction_success(db, playing_room, mock_manager):
    room, p1, p2 = playing_room
    memes_q = await db.execute(select(Meme).where(Meme.is_special == False).limit(1))  # noqa: E712
    m = memes_q.scalar_one()
    play = Play(round_id=1, player_id=p2.id, meme_id=m.id)
    # Need a round first
    rnd = Round(room_id=room.id, situation_text="x", round_number=1, status=RoundStatus.voting)
    db.add(rnd)
    await db.flush()
    play.round_id = rnd.id
    db.add(play)
    await db.flush()
    await db.commit()

    p1 = await _reload_player(db, p1.id)
    await _handle_reaction(db, {"play_id": play.id, "reaction_type": "laugh"}, p1, room.code)

    reactions_q = await db.execute(select(Reaction).where(Reaction.play_id == play.id))
    assert reactions_q.scalar_one_or_none() is not None


async def test_reaction_invalid_type(db, playing_room, mock_manager):
    room, p1, p2 = playing_room
    p1 = await _reload_player(db, p1.id)

    await _handle_reaction(db, {"play_id": 1, "reaction_type": "invalid"}, p1, room.code)
    # Should silently return, no error


async def test_reaction_duplicate_rejected(db, playing_room, mock_manager):
    room, p1, p2 = playing_room
    rnd = Round(room_id=room.id, situation_text="x", round_number=1, status=RoundStatus.voting)
    db.add(rnd)
    await db.flush()
    memes_q = await db.execute(select(Meme).where(Meme.is_special == False).limit(1))  # noqa: E712
    m = memes_q.scalar_one()
    play = Play(round_id=rnd.id, player_id=p2.id, meme_id=m.id)
    db.add(play)
    await db.flush()
    await db.commit()

    p1 = await _reload_player(db, p1.id)
    await _handle_reaction(db, {"play_id": play.id, "reaction_type": "fire"}, p1, room.code)
    await _handle_reaction(db, {"play_id": play.id, "reaction_type": "fire"}, p1, room.code)

    reactions_q = await db.execute(select(Reaction).where(Reaction.play_id == play.id))
    assert len(reactions_q.scalars().all()) == 1


# ── _handle_czar_pick ──────────────────────────────────────────


async def test_czar_pick_success(db, playing_room, mock_manager, mock_create_task):
    room, p1, p2 = playing_room
    room.mode = GameMode.czar
    await db.commit()

    rnd = Round(
        room_id=room.id, situation_text="x", round_number=1,
        status=RoundStatus.voting, czar_id=p1.id
    )
    db.add(rnd)
    await db.flush()

    memes_q = await db.execute(select(Meme).where(Meme.is_special == False).limit(2))  # noqa: E712
    memes = list(memes_q.scalars().all())
    play2 = Play(round_id=rnd.id, player_id=p2.id, meme_id=memes[0].id)
    db.add(play2)
    await db.flush()
    await db.commit()

    p1 = await _reload_player(db, p1.id)

    with patch("app.routers.websocket.finalize_round", new_callable=AsyncMock) as mock_fin:
        await _handle_czar_pick(db, {"winner_player_id": p2.id}, p1, room.code)
        mock_fin.assert_called_once()


async def test_czar_pick_non_czar_rejected(db, playing_room, mock_manager):
    room, p1, p2 = playing_room
    rnd = Round(room_id=room.id, situation_text="x", round_number=1,
                status=RoundStatus.voting, czar_id=p1.id)
    db.add(rnd)
    await db.commit()

    p2 = await _reload_player(db, p2.id)  # p2 is not czar

    with patch("app.routers.websocket.finalize_round", new_callable=AsyncMock) as mock_fin:
        await _handle_czar_pick(db, {"winner_player_id": p1.id}, p2, room.code)
        mock_fin.assert_not_called()


# ── _handle_disconnect ─────────────────────────────────────────


async def test_disconnect_marks_player_offline(db, room_with_players, mock_manager):
    room, p1, p2 = room_with_players

    await _handle_disconnect(db, p1.id, room.code)

    await db.refresh(p1)
    assert p1.is_connected is False


async def test_disconnect_host_keeps_host_role(db, room_with_players, mock_manager):
    """After fix: host stays host even after disconnect."""
    room, p1, p2 = room_with_players

    await _handle_disconnect(db, p1.id, room.code)

    await db.refresh(p1)
    assert p1.is_host is True  # Bug fix: host role preserved


async def test_disconnect_unknown_player_noop(db, room_with_players, mock_manager):
    room, _, _ = room_with_players
    # Should not raise
    await _handle_disconnect(db, 99999, room.code)


# ── _get_active_round ──────────────────────────────────────────


async def test_get_active_round_found(db, room_with_players):
    room, _, _ = room_with_players
    rnd = Round(room_id=room.id, situation_text="x", round_number=1, status=RoundStatus.playing)
    db.add(rnd)
    await db.commit()

    found = await _get_active_round(db, room.id)
    assert found is not None
    assert found.id == rnd.id


async def test_get_active_round_not_found(db, room_with_players):
    room, _, _ = room_with_players
    found = await _get_active_round(db, room.id)
    assert found is None


async def test_get_active_round_ignores_finished(db, room_with_players):
    room, _, _ = room_with_players
    rnd = Round(room_id=room.id, situation_text="x", round_number=1, status=RoundStatus.finished)
    db.add(rnd)
    await db.commit()

    found = await _get_active_round(db, room.id)
    assert found is None


# ── _load_player ───────────────────────────────────────────────


async def test_load_player_found(db, room_with_players):
    room, p1, _ = room_with_players
    player = await _load_player(db, p1.id, room.code)
    assert player is not None
    assert player.id == p1.id


async def test_load_player_not_found(db, room_with_players):
    room, _, _ = room_with_players
    player = await _load_player(db, 99999, room.code)
    assert player is None


async def test_load_player_wrong_room(db, room_with_players):
    room, p1, _ = room_with_players
    player = await _load_player(db, p1.id, "WRONG1")
    assert player is None
