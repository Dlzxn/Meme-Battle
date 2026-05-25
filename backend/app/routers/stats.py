from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta

from app.database import get_db
from app.models import GameStats, User, UnlockedPack, Meme
from app.schemas import StatsOut, LeaderboardEntry, MemeOut
from app.auth import require_user

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/me", response_model=StatsOut)
async def my_stats(db: AsyncSession = Depends(get_db), user: User = Depends(require_user)):
    stats_q = await db.execute(
        select(GameStats)
        .where(GameStats.user_id == user.id)
        .options(selectinload(GameStats.favorite_meme))
    )
    stats = stats_q.scalar_one_or_none()
    if not stats:
        return StatsOut(games_played=0, games_won=0, win_rate=0.0)

    packs_q = await db.execute(select(UnlockedPack).where(UnlockedPack.user_id == user.id))
    packs = [p.pack_name for p in packs_q.scalars().all()]

    fav = None
    if stats.favorite_meme:
        fav = MemeOut(
            id=stats.favorite_meme.id,
            url=stats.favorite_meme.url,
            name=stats.favorite_meme.name,
            is_special=stats.favorite_meme.is_special,
            special_type=stats.favorite_meme.special_type.value if stats.favorite_meme.special_type else None,
        )

    win_rate = round(stats.games_won / stats.games_played * 100, 1) if stats.games_played > 0 else 0.0
    return StatsOut(
        games_played=stats.games_played,
        games_won=stats.games_won,
        win_rate=win_rate,
        favorite_meme=fav,
        unlocked_packs=packs,
    )


@router.get("/leaderboard", response_model=list[LeaderboardEntry])
async def leaderboard(
    period: str = Query("all", regex="^(all|month|week)$"),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(GameStats, User.username)
        .join(User, GameStats.user_id == User.id)
        .where(GameStats.games_played >= 10)
        .order_by(desc(GameStats.games_won * 1.0 / GameStats.games_played))
        .limit(100)
    )
    result = await db.execute(query)
    rows = result.all()

    entries = []
    for rank, (stats, username) in enumerate(rows, start=1):
        win_rate = round(stats.games_won / stats.games_played * 100, 1)
        entries.append(
            LeaderboardEntry(
                rank=rank,
                username=username,
                games_played=stats.games_played,
                games_won=stats.games_won,
                win_rate=win_rate,
            )
        )
    return entries
