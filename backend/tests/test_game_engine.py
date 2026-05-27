"""Tests for core game engine functions."""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.game_engine import (
    deal_cards, get_active_players, player_card_list,
    broadcast_room_state, pick_situation, start_round,
    finalize_round, _check_skip_penalty, _get_random_memes,
    _end_game, _end_arena_game, _auto_play_missing, _start_voting,
    _schedule_next_round, _schedule_arena_end, _schedule_game_end,
    vote_timer, play_timer,
)
from app.models import (
    Room, Player, Meme, PlayerCard, Round, Play, Vote, Reaction,
    RoundStatus, RoomStatus, GameMode, SituationCategory, Situation,
    SpecialType, GameStats, UnlockedPack, ReactionType,
)


# ── deal_cards ────────────────────────────────────────────────


async def test_deal_cards_fills_hand(db, room_with_players, mock_manager, mock_create_task):
    room, p1, p2 = room_with_players
    # Reload p1 with cards relationship
    p1_q = await db.execute(
        select(Player).where(Player.id == p1.id).options(selectinload(Player.cards))
    )
    p1 = p1_q.scalar_one()

    memes_dealt = await deal_cards(db, p1, 5)
    assert len(memes_dealt) >= 5  # may include an occasional bonus special card

    await db.refresh(p1)
    p1_q = await db.execute(
        select(Player).where(Player.id == p1.id).options(selectinload(Player.cards))
    )
    p1 = p1_q.scalar_one()
    assert len(p1.cards) >= 5


async def test_deal_cards_avoids_duplicates(db, room_with_players, mock_manager, mock_create_task):
    room, p1, p2 = room_with_players
    p1_q = await db.execute(
        select(Player).where(Player.id == p1.id).options(selectinload(Player.cards))
    )
    p1 = p1_q.scalar_one()

    first_batch = await deal_cards(db, p1, 5)
    await db.commit()

    # Refresh p1 so the cards collection reflects what's now in the DB
    await db.refresh(p1)
    # Load cards relationship explicitly
    p1_q = await db.execute(
        select(Player).where(Player.id == p1.id)
        .options(selectinload(Player.cards).selectinload(PlayerCard.meme))
        .execution_options(populate_existing=True)
    )
    p1 = p1_q.scalar_one()
    assert len(p1.cards) == 5  # verify cards are loaded

    second_batch = await deal_cards(db, p1, 3)
    first_ids = {m.id for m in first_batch}
    second_ids = {m.id for m in second_batch}
    assert not first_ids & second_ids


async def test_deal_cards_no_memes_available(db, room_with_players, mock_manager):
    room, p1, _ = room_with_players
    # Delete all memes
    memes_q = await db.execute(select(Meme))
    for m in memes_q.scalars().all():
        await db.delete(m)
    await db.commit()

    p1_q = await db.execute(
        select(Player).where(Player.id == p1.id).options(selectinload(Player.cards))
    )
    p1 = p1_q.scalar_one()
    memes = await deal_cards(db, p1, 5)
    assert memes == []


# ── get_active_players ────────────────────────────────────────


async def test_get_active_players(db, room_with_players, mock_manager):
    room, p1, p2 = room_with_players
    players = await get_active_players(db, room.code)
    assert len(players) == 2
    nicknames = {p.nickname for p in players}
    assert "Host" in nicknames and "Guest" in nicknames


async def test_get_active_players_excludes_disconnected(db, room_with_players, mock_manager):
    room, p1, p2 = room_with_players
    p2.is_connected = False
    await db.commit()

    players = await get_active_players(db, room.code)
    assert len(players) == 1
    assert players[0].nickname == "Host"


# ── player_card_list ──────────────────────────────────────────


async def test_player_card_list(db, playing_room):
    room, p1, p2 = playing_room
    p1_q = await db.execute(
        select(Player).where(Player.id == p1.id)
        .options(selectinload(Player.cards).selectinload(PlayerCard.meme))
    )
    p1 = p1_q.scalar_one()

    cards = player_card_list(p1)
    assert len(cards) == 5
    for c in cards:
        assert "card_id" in c
        assert "url" in c
        assert "name" in c
        assert "is_special" in c


async def test_player_card_list_empty(db, room_with_players):
    room, p1, _ = room_with_players
    p1_q = await db.execute(
        select(Player).where(Player.id == p1.id)
        .options(selectinload(Player.cards).selectinload(PlayerCard.meme))
    )
    p1 = p1_q.scalar_one()
    assert player_card_list(p1) == []


# ── broadcast_room_state ──────────────────────────────────────


async def test_broadcast_room_state(db, room_with_players, mock_manager):
    room, _, _ = room_with_players
    await broadcast_room_state(db, room.code)
    mock_manager.broadcast.assert_called_once()
    call_args = mock_manager.broadcast.call_args[0]
    assert call_args[0] == room.code
    assert call_args[1]["type"] == "room_updated"


# ── pick_situation ────────────────────────────────────────────


async def test_pick_situation_from_db(db, room_with_players, situations):
    room, _, _ = room_with_players
    text, sit_id = await pick_situation(db, room, [])
    assert isinstance(text, str)
    assert len(text) > 0
    assert sit_id is not None


async def test_pick_situation_custom(db, room_with_players):
    room, _, _ = room_with_players
    room.custom_situations = "Custom Situation A\nCustom Situation B"
    await db.commit()

    text, sit_id = await pick_situation(db, room, [])
    assert text in ("Custom Situation A", "Custom Situation B")
    assert sit_id is None


async def test_pick_situation_fallback_when_all_used(db, room_with_players, situations):
    room, _, _ = room_with_players
    used_ids = [s.id for s in situations]
    text, sit_id = await pick_situation(db, room, used_ids)
    assert isinstance(text, str)


async def test_pick_situation_no_db_fallback(db, room_with_players):
    room, _, _ = room_with_players
    # Delete all situations so fallback text is returned
    all_q = await db.execute(select(Situation))
    for s in all_q.scalars().all():
        await db.delete(s)
    await db.commit()

    text, sit_id = await pick_situation(db, room, [])
    assert text == "Что бы вы сделали?"
    assert sit_id is None


# ── start_round ───────────────────────────────────────────────


async def test_start_round_creates_round(db, room_with_players, situations, mock_manager, mock_create_task):
    room, p1, p2 = room_with_players
    room.status = RoomStatus.playing

    # Deal cards first
    from sqlalchemy import select as sa_select
    meme_q = await db.execute(sa_select(Meme).where(Meme.is_special == False).limit(10))  # noqa: E712
    all_memes = list(meme_q.scalars().all())
    for idx, player in enumerate([p1, p2]):
        for m in all_memes[idx * 5: idx * 5 + 5]:
            db.add(PlayerCard(player_id=player.id, meme_id=m.id))
    await db.commit()

    # Reload players
    from sqlalchemy.orm import selectinload
    p1_q = await db.execute(
        sa_select(Player).where(Player.id == p1.id)
        .options(selectinload(Player.cards).selectinload(PlayerCard.meme))
    )
    p1 = p1_q.scalar_one()

    await start_round(db, room, room.code, 1)

    rounds_q = await db.execute(sa_select(Round).where(Round.room_id == room.id))
    rounds = rounds_q.scalars().all()
    assert len(rounds) == 1
    assert rounds[0].round_number == 1
    assert rounds[0].status == RoundStatus.playing


async def test_start_round_no_players(db, room_with_players, situations, mock_manager, mock_create_task):
    room, p1, p2 = room_with_players
    p1.is_connected = False
    p2.is_connected = False
    await db.commit()

    await start_round(db, room, room.code, 1)  # Should return early

    from sqlalchemy import select as sa_select
    rounds_q = await db.execute(sa_select(Round).where(Round.room_id == room.id))
    assert rounds_q.scalars().first() is None


async def test_start_round_czar_mode(db, room_with_players, situations, mock_manager, mock_create_task):
    room, p1, p2 = room_with_players
    room.mode = GameMode.czar
    room.status = RoomStatus.playing

    from sqlalchemy import select as sa_select
    meme_q = await db.execute(sa_select(Meme).where(Meme.is_special == False).limit(10))  # noqa: E712
    all_memes = list(meme_q.scalars().all())
    for idx, player in enumerate([p1, p2]):
        for m in all_memes[idx * 5: idx * 5 + 5]:
            db.add(PlayerCard(player_id=player.id, meme_id=m.id))
    await db.commit()

    await start_round(db, room, room.code, 1)

    rounds_q = await db.execute(sa_select(Round).where(Round.room_id == room.id))
    rnd = rounds_q.scalars().first()
    assert rnd is not None
    assert rnd.czar_id in [p1.id, p2.id]


# ── finalize_round ────────────────────────────────────────────


async def _setup_round_with_plays(db, room, p1, p2, memes):
    """Helper: create round + 2 plays."""
    rnd = Round(room_id=room.id, situation_text="Test", round_number=1, status=RoundStatus.voting)
    db.add(rnd)
    await db.flush()

    play1 = Play(round_id=rnd.id, player_id=p1.id, meme_id=memes[0].id)
    play2 = Play(round_id=rnd.id, player_id=p2.id, meme_id=memes[1].id)
    db.add_all([play1, play2])
    await db.flush()

    return rnd, play1, play2


async def test_finalize_round_with_winner(db, playing_room, mock_manager, mock_create_task):
    room, p1, p2 = playing_room
    memes_q = await db.execute(select(Meme).where(Meme.is_special == False).limit(2))  # noqa: E712
    memes = list(memes_q.scalars().all())

    rnd, play1, play2 = await _setup_round_with_plays(db, room, p1, p2, memes)

    # p1 votes for p2, so p2 wins (most votes = winner, fewest = loser)
    vote = Vote(round_id=rnd.id, voter_id=p1.id, target_player_id=p2.id, target_play_id=play2.id)
    db.add(vote)
    await db.commit()

    await finalize_round(db, room.code, rnd.id)

    broadcast_calls = [call[0][1] for call in mock_manager.broadcast.call_args_list]
    round_result = next((c for c in broadcast_calls if c.get("type") == "round_result"), None)
    assert round_result is not None
    assert round_result["payload"]["is_tie"] is False


async def test_finalize_round_tie(db, playing_room, mock_manager, mock_create_task):
    room, p1, p2 = playing_room
    memes_q = await db.execute(select(Meme).where(Meme.is_special == False).limit(2))  # noqa: E712
    memes = list(memes_q.scalars().all())

    rnd, play1, play2 = await _setup_round_with_plays(db, room, p1, p2, memes)
    # No votes — both have 0 → tie
    await db.commit()

    await finalize_round(db, room.code, rnd.id)

    broadcast_calls = [call[0][1] for call in mock_manager.broadcast.call_args_list]
    round_result = next((c for c in broadcast_calls if c.get("type") == "round_result"), None)
    assert round_result is not None
    assert round_result["payload"]["is_tie"] is True


async def test_finalize_round_double_call_noop(db, playing_room, mock_manager, mock_create_task):
    """Second finalize_round call on the same round must be a no-op."""
    room, p1, p2 = playing_room
    memes_q = await db.execute(select(Meme).where(Meme.is_special == False).limit(2))  # noqa: E712
    memes = list(memes_q.scalars().all())

    rnd, play1, play2 = await _setup_round_with_plays(db, room, p1, p2, memes)
    await db.commit()

    await finalize_round(db, room.code, rnd.id)
    call_count_after_first = mock_manager.broadcast.call_count

    await finalize_round(db, room.code, rnd.id)  # should be skipped
    assert mock_manager.broadcast.call_count == call_count_after_first


async def test_finalize_round_no_plays(db, room_with_players, situations, mock_manager, mock_create_task):
    room, p1, p2 = room_with_players
    rnd = Round(room_id=room.id, situation_text="x", round_number=1, status=RoundStatus.voting)
    db.add(rnd)
    await db.commit()

    await finalize_round(db, room.code, rnd.id)
    # Should commit without error, no round_result broadcast
    broadcast_calls = [call[0][1].get("type") for call in mock_manager.broadcast.call_args_list]
    assert "round_result" not in broadcast_calls


# ── _check_skip_penalty ───────────────────────────────────────


async def test_skip_penalty_with_skip_card(db, playing_room, mock_manager):
    room, p1, p2 = playing_room
    # Give p2 a skip_penalty special card
    skip_meme_q = await db.execute(
        select(Meme).where(Meme.special_type == SpecialType.skip_penalty)
    )
    skip_meme = skip_meme_q.scalar_one_or_none()
    if not skip_meme:
        pytest.skip("No skip_penalty meme in fixtures")

    db.add(PlayerCard(player_id=p2.id, meme_id=skip_meme.id))
    await db.commit()

    p2_q = await db.execute(
        select(Player).where(Player.id == p2.id)
        .options(selectinload(Player.cards).selectinload(PlayerCard.meme))
    )
    p2 = p2_q.scalar_one()

    cards_before = len(p2.cards)
    await _check_skip_penalty(db, room.code, p2, room)
    await db.commit()

    p2_q = await db.execute(
        select(Player).where(Player.id == p2.id)
        .options(selectinload(Player.cards))
        .execution_options(populate_existing=True)
    )
    p2 = p2_q.scalar_one()
    assert len(p2.cards) == cards_before - 1  # skip card consumed


async def test_skip_penalty_without_skip_card(db, playing_room, mock_manager):
    room, p1, p2 = playing_room
    p2_q = await db.execute(
        select(Player).where(Player.id == p2.id)
        .options(selectinload(Player.cards).selectinload(PlayerCard.meme))
    )
    p2 = p2_q.scalar_one()
    cards_before = len(p2.cards)

    await _check_skip_penalty(db, room.code, p2, room)
    await db.commit()

    p2_q = await db.execute(
        select(Player).where(Player.id == p2.id)
        .options(selectinload(Player.cards))
        .execution_options(populate_existing=True)
    )
    p2 = p2_q.scalar_one()
    # Penalty adds `penalty_count` cards (room.penalty_count = 1)
    assert len(p2.cards) == cards_before + 1


# ── _get_random_memes ─────────────────────────────────────────


async def test_get_random_memes(db, memes):
    result = await _get_random_memes(db, 3, [])
    assert len(result) == 3


async def test_get_random_memes_with_exclusions(db, memes):
    exclude_ids = [m.id for m in memes[:10]]
    result = await _get_random_memes(db, 3, exclude_ids)
    for m in result:
        assert m.id not in exclude_ids


# ── _end_game ─────────────────────────────────────────────────


async def test_end_game_updates_stats(db, playing_room, mock_manager, mock_create_task):
    room, p1, p2 = playing_room
    p1.user_id = None
    p2.user_id = None
    await db.commit()

    p1_q = await db.execute(
        select(Player).where(Player.id == p1.id)
        .options(selectinload(Player.cards).selectinload(PlayerCard.meme))
    )
    p1_loaded = p1_q.scalar_one()
    p2_q = await db.execute(
        select(Player).where(Player.id == p2.id)
        .options(selectinload(Player.cards).selectinload(PlayerCard.meme))
    )
    p2_loaded = p2_q.scalar_one()

    await _end_game(db, room.code, room, [p1_loaded, p2_loaded], p1_loaded)

    # Room should be finished
    await db.refresh(room)
    assert room.status == RoomStatus.finished

    broadcast_types = [call[0][1]["type"] for call in mock_manager.broadcast.call_args_list]
    assert "game_over" in broadcast_types


async def test_end_game_with_registered_players(db, playing_room, user1, user2, mock_manager, mock_create_task):
    room, p1, p2 = playing_room
    p1.user_id = user1.id
    p2.user_id = user2.id
    await db.commit()

    p1_q = await db.execute(
        select(Player).where(Player.id == p1.id)
        .options(selectinload(Player.cards).selectinload(PlayerCard.meme))
    )
    p1_loaded = p1_q.scalar_one()
    p2_q = await db.execute(
        select(Player).where(Player.id == p2.id)
        .options(selectinload(Player.cards).selectinload(PlayerCard.meme))
    )
    p2_loaded = p2_q.scalar_one()

    await _end_game(db, room.code, room, [p1_loaded, p2_loaded], p1_loaded)

    from sqlalchemy import select as sa_select
    stats_q = await db.execute(sa_select(GameStats).where(GameStats.user_id == user1.id))
    stats = stats_q.scalar_one()
    assert stats.games_played == 1
    assert stats.games_won == 1


async def test_end_game_unlocks_packs(db, playing_room, user1, mock_manager, mock_create_task):
    room, p1, p2 = playing_room
    p1.user_id = user1.id

    from sqlalchemy import select as sa_select
    st_q = await db.execute(sa_select(GameStats).where(GameStats.user_id == user1.id))
    stats = st_q.scalar_one()
    stats.games_played = 9  # will become 10 → unlock classic_internet
    await db.commit()

    p1_q = await db.execute(
        select(Player).where(Player.id == p1.id)
        .options(selectinload(Player.cards).selectinload(PlayerCard.meme))
    )
    p1_loaded = p1_q.scalar_one()
    p2_q = await db.execute(
        select(Player).where(Player.id == p2.id)
        .options(selectinload(Player.cards).selectinload(PlayerCard.meme))
    )
    p2_loaded = p2_q.scalar_one()

    await _end_game(db, room.code, room, [p1_loaded, p2_loaded], p1_loaded)

    packs_q = await db.execute(sa_select(UnlockedPack).where(UnlockedPack.user_id == user1.id))
    packs = [p.pack_name for p in packs_q.scalars().all()]
    assert "classic_internet" in packs


# ── _auto_play_missing ────────────────────────────────────────


async def test_auto_play_missing_submits_for_idle_player(
    db, playing_room, situations, mock_manager, mock_create_task
):
    room, p1, p2 = playing_room
    room.status = RoomStatus.playing

    rnd = Round(room_id=room.id, situation_text="x", round_number=1, status=RoundStatus.playing)
    db.add(rnd)
    await db.flush()

    # p1 already played, p2 did not
    memes_q = await db.execute(select(Meme).where(Meme.is_special == False).limit(1))  # noqa: E712
    m = memes_q.scalar_one()
    db.add(Play(round_id=rnd.id, player_id=p1.id, meme_id=m.id))
    await db.commit()

    await _auto_play_missing(db, room.code, rnd.id)

    plays_q = await db.execute(select(Play).where(Play.round_id == rnd.id))
    plays = plays_q.scalars().all()
    assert len(plays) == 2  # p2 auto-played


async def test_auto_play_skips_czar(db, playing_room, situations, mock_manager, mock_create_task):
    room, p1, p2 = playing_room
    room.mode = GameMode.czar
    room.status = RoomStatus.playing

    rnd = Round(
        room_id=room.id, situation_text="x", round_number=1,
        status=RoundStatus.playing, czar_id=p2.id
    )
    db.add(rnd)
    await db.flush()
    # p1 played, p2 is czar and should not auto-play
    memes_q = await db.execute(select(Meme).where(Meme.is_special == False).limit(1))  # noqa: E712
    m = memes_q.scalar_one()
    db.add(Play(round_id=rnd.id, player_id=p1.id, meme_id=m.id))
    await db.commit()

    await _auto_play_missing(db, room.code, rnd.id)

    plays_q = await db.execute(select(Play).where(Play.round_id == rnd.id))
    plays = list(plays_q.scalars().all())
    player_ids = {pl.player_id for pl in plays}
    assert p2.id not in player_ids  # czar not auto-played


async def test_auto_play_already_finished_round(db, playing_room, mock_manager, mock_create_task):
    room, p1, p2 = playing_room
    rnd = Round(room_id=room.id, situation_text="x", round_number=1, status=RoundStatus.finished)
    db.add(rnd)
    await db.commit()

    await _auto_play_missing(db, room.code, rnd.id)  # no-op, round already done
    mock_manager.broadcast.assert_not_called()


# ── _schedule_next_round ──────────────────────────────────────


async def test_schedule_next_round_calls_start_round(mock_manager):
    """_schedule_next_round calls start_round when room is still playing."""
    start_round_calls = []

    fake_room = MagicMock()
    fake_room.status = RoomStatus.playing

    async def fake_start_round(db, room, code, rn):
        start_round_calls.append(rn)

    mock_db = AsyncMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=False)
    mock_db.get = AsyncMock(return_value=fake_room)

    with (
        patch("app.game_engine.AsyncSessionLocal", return_value=mock_db),
        patch("app.game_engine.start_round", fake_start_round),
    ):
        await _schedule_next_round("CODE1", room_id=1, next_round_number=2, delay=0)

    assert start_round_calls == [2]


async def test_schedule_next_round_skips_if_not_playing(mock_manager):
    """_schedule_next_round does nothing when room is finished."""
    start_round_calls = []

    fake_room = MagicMock()
    fake_room.status = RoomStatus.finished

    async def fake_start_round(*a, **kw):
        start_round_calls.append(True)

    mock_db = AsyncMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=False)
    mock_db.get = AsyncMock(return_value=fake_room)

    with (
        patch("app.game_engine.AsyncSessionLocal", return_value=mock_db),
        patch("app.game_engine.start_round", fake_start_round),
    ):
        await _schedule_next_round("CODE2", room_id=2, next_round_number=3, delay=0)

    assert start_round_calls == []


async def test_schedule_next_round_skips_if_room_missing(mock_manager):
    """_schedule_next_round does nothing if room no longer exists."""
    start_round_calls = []

    mock_db = AsyncMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=False)
    mock_db.get = AsyncMock(return_value=None)

    with (
        patch("app.game_engine.AsyncSessionLocal", return_value=mock_db),
        patch("app.game_engine.start_round", AsyncMock(side_effect=lambda *a, **kw: start_round_calls.append(True))),
    ):
        await _schedule_next_round("GONE", room_id=99, next_round_number=2, delay=0)

    assert start_round_calls == []


# ── _schedule_arena_end ───────────────────────────────────────


async def test_schedule_arena_end_calls_end_arena_game(mock_manager):
    end_arena_calls = []

    fake_room = MagicMock()
    fake_room.status = RoomStatus.playing

    async def fake_end_arena(db, room_code, room, players):
        end_arena_calls.append(room_code)

    mock_db = AsyncMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=False)
    mock_db.get = AsyncMock(return_value=fake_room)

    with (
        patch("app.game_engine.AsyncSessionLocal", return_value=mock_db),
        patch("app.game_engine._end_arena_game", fake_end_arena),
        patch("app.game_engine.get_active_players", AsyncMock(return_value=[])),
    ):
        await _schedule_arena_end("AREN1", room_id=1, delay=0)

    assert end_arena_calls == ["AREN1"]


async def test_schedule_arena_end_skips_if_room_missing(mock_manager):
    end_arena_calls = []

    mock_db = AsyncMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=False)
    mock_db.get = AsyncMock(return_value=None)

    with (
        patch("app.game_engine.AsyncSessionLocal", return_value=mock_db),
        patch("app.game_engine._end_arena_game", AsyncMock(side_effect=lambda *a, **kw: end_arena_calls.append(True))),
        patch("app.game_engine.get_active_players", AsyncMock(return_value=[])),
    ):
        await _schedule_arena_end("AREN2", room_id=99, delay=0)

    assert end_arena_calls == []


# ── _schedule_game_end ────────────────────────────────────────


async def test_schedule_game_end_calls_end_game_when_winner_found(mock_manager):
    end_game_calls = []

    fake_winner = MagicMock()
    fake_winner.id = 42

    fake_room = MagicMock()

    async def fake_end_game(db, room_code, room, players, winner):
        end_game_calls.append((room_code, winner.id))

    mock_db = AsyncMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=False)
    mock_db.get = AsyncMock(return_value=fake_room)

    with (
        patch("app.game_engine.AsyncSessionLocal", return_value=mock_db),
        patch("app.game_engine._end_game", fake_end_game),
        patch("app.game_engine.get_active_players", AsyncMock(return_value=[fake_winner])),
    ):
        await _schedule_game_end("GEND1", room_id=1, winner_player_id=42, delay=0)

    assert end_game_calls == [("GEND1", 42)]


async def test_schedule_game_end_skips_if_winner_disconnected(mock_manager):
    """If winner left, get_active_players won't include them — no end_game call."""
    end_game_calls = []

    mock_db = AsyncMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=False)
    mock_db.get = AsyncMock(return_value=MagicMock())

    with (
        patch("app.game_engine.AsyncSessionLocal", return_value=mock_db),
        patch("app.game_engine._end_game", AsyncMock(side_effect=lambda *a, **kw: end_game_calls.append(True))),
        patch("app.game_engine.get_active_players", AsyncMock(return_value=[])),
    ):
        await _schedule_game_end("GEND2", room_id=2, winner_player_id=99, delay=0)

    assert end_game_calls == []


# ── finalize_round uses _bg not sleep ────────────────────────


async def test_finalize_round_schedules_bg_not_sleep(db, playing_room, mock_manager, mock_create_task):
    """finalize_round must not await asyncio.sleep — it must schedule _bg() tasks."""
    room, p1, p2 = playing_room

    memes_q = await db.execute(select(Meme).where(Meme.is_special == False).limit(2))  # noqa: E712
    memes = list(memes_q.scalars().all())

    rnd = Round(room_id=room.id, situation_text="Test", round_number=1, status=RoundStatus.voting)
    db.add(rnd)
    await db.flush()
    play1 = Play(round_id=rnd.id, player_id=p1.id, meme_id=memes[0].id)
    play2 = Play(round_id=rnd.id, player_id=p2.id, meme_id=memes[1].id)
    db.add_all([play1, play2])
    await db.commit()

    sleep_called = []
    real_sleep = asyncio.sleep

    async def fake_sleep(t, *a, **kw):
        sleep_called.append(t)
        return await real_sleep(0)

    with patch("asyncio.sleep", fake_sleep):
        await finalize_round(db, room.code, rnd.id)

    assert sleep_called == [], (
        f"finalize_round called asyncio.sleep({sleep_called}) — "
        "it should schedule _bg() tasks instead"
    )


# ── vote_timer / play_timer ───────────────────────────────────


async def test_vote_timer_calls_finalize_round(mock_manager):
    """vote_timer calls finalize_round after countdown, using a fresh session."""
    finalize_calls = []

    async def fake_finalize(db, room_code, round_id):
        finalize_calls.append((room_code, round_id))

    mock_db = AsyncMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=False)

    real_sleep = asyncio.sleep

    async def instant_sleep(t, *a, **kw):
        await real_sleep(0)

    with (
        patch("app.game_engine.AsyncSessionLocal", return_value=mock_db),
        patch("app.game_engine.finalize_round", fake_finalize),
        patch("asyncio.sleep", instant_sleep),
    ):
        await vote_timer(room_id=1, room_code="VTIME", round_id=42, seconds=2)

    assert finalize_calls == [("VTIME", 42)]


async def test_play_timer_calls_auto_play_missing(mock_manager):
    """play_timer calls _auto_play_missing after countdown."""
    auto_play_calls = []

    async def fake_auto(db, room_code, round_id):
        auto_play_calls.append((room_code, round_id))

    mock_db = AsyncMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=False)

    real_sleep = asyncio.sleep

    async def instant_sleep(t, *a, **kw):
        await real_sleep(0)

    with (
        patch("app.game_engine.AsyncSessionLocal", return_value=mock_db),
        patch("app.game_engine._auto_play_missing", fake_auto),
        patch("asyncio.sleep", instant_sleep),
    ):
        await play_timer(room_id=1, room_code="PTIME", round_id=7, seconds=2)

    assert auto_play_calls == [("PTIME", 7)]


# ── _end_arena_game ───────────────────────────────────────────


async def test_end_arena_game_broadcasts_game_over(db, playing_room, mock_manager, mock_create_task):
    room, p1, p2 = playing_room
    room.mode = GameMode.arena
    await db.commit()

    p1_q = await db.execute(
        select(Player).where(Player.id == p1.id)
        .options(selectinload(Player.cards).selectinload(PlayerCard.meme))
    )
    p1_loaded = p1_q.scalar_one()
    p2_q = await db.execute(
        select(Player).where(Player.id == p2.id)
        .options(selectinload(Player.cards).selectinload(PlayerCard.meme))
    )
    p2_loaded = p2_q.scalar_one()

    await _end_arena_game(db, room.code, room, [p1_loaded, p2_loaded])

    await db.refresh(room)
    assert room.status == RoomStatus.finished

    broadcast_types = [call[0][1]["type"] for call in mock_manager.broadcast.call_args_list]
    assert "game_over" in broadcast_types


async def test_end_arena_game_no_players(db, room_with_players, mock_manager):
    room, p1, p2 = room_with_players
    room.mode = GameMode.arena
    await db.commit()

    await _end_arena_game(db, room.code, room, [])

    await db.refresh(room)
    assert room.status == RoomStatus.finished  # still marks finished
    broadcast_types = [call[0][1]["type"] for call in mock_manager.broadcast.call_args_list]
    assert "game_over" in broadcast_types
