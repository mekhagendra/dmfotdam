"""
Reddit monitoring API endpoints.

Provides:
  - Manual scan trigger
  - Reddit search
  - Flagged extremism content listing with pagination
  - Daily trend data
  - Post detail and review actions
"""

from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, cast, Date
from pydantic import BaseModel, Field
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.reddit_post import RedditPost

router = APIRouter()


# ── Request / Response schemas ───────────────────────────────────────

class ScanRequest(BaseModel):
    subreddits: Optional[list[str]] = None
    limit: int = Field(50, ge=1, le=200)
    threat_threshold: float = Field(0.3, ge=0.0, le=1.0)


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=200)
    subreddits: Optional[list[str]] = None
    limit: int = Field(25, ge=1, le=100)
    time_filter: str = Field("day", pattern="^(hour|day|week|month|year|all)$")


class RedditPostResponse(BaseModel):
    id: int
    reddit_id: str
    subreddit: str
    title: str
    text: str
    author: str
    url: str
    score: int
    num_comments: int
    threat_score: float
    threat_level: str
    analysis_details: dict | None
    posted_at: datetime | None
    scanned_at: datetime | None
    is_reviewed: bool

    class Config:
        from_attributes = True


class TrendDataPoint(BaseModel):
    date: str
    total_posts: int
    avg_threat_score: float
    max_threat_score: float
    high_threat_count: int


class ScanResultResponse(BaseModel):
    status: str
    scan_time: str | None = None
    total_scanned: int = 0
    total_flagged: int = 0
    new_posts_stored: int = 0
    new_alerts_generated: int = 0
    reason: str | None = None


class RedditStatusResponse(BaseModel):
    available: bool
    message: str
    default_subreddits: list[str]
    total_stored_posts: int
    last_scan_time: str | None


# ── Endpoints ────────────────────────────────────────────────────────

@router.get("/status", response_model=RedditStatusResponse)
async def reddit_status(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Check Reddit API status and monitoring statistics."""
    from app.services.reddit_service import RedditService

    reddit = RedditService()
    available = reddit.is_available

    total = (await db.execute(
        select(func.count()).select_from(RedditPost)
    )).scalar() or 0

    last_post = (await db.execute(
        select(RedditPost.scanned_at)
        .order_by(desc(RedditPost.scanned_at))
        .limit(1)
    )).scalar_one_or_none()

    from app.services.reddit_service import DEFAULT_SUBREDDITS

    return RedditStatusResponse(
        available=available,
        message="Reddit API connected" if available else "Reddit API not configured. Set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET in .env",
        default_subreddits=DEFAULT_SUBREDDITS,
        total_stored_posts=total,
        last_scan_time=last_post.isoformat() if last_post else None,
    )


@router.post("/scan", response_model=ScanResultResponse)
async def trigger_scan(
    request: ScanRequest,
    user_id: int = Depends(get_current_user_id),
):
    """Manually trigger a Reddit scan. Fetches posts, analyzes them, stores flagged content."""
    from app.services.reddit_scheduler import run_daily_reddit_scan

    result = await run_daily_reddit_scan(
        subreddits=request.subreddits,
        limit=request.limit,
        threat_threshold=request.threat_threshold,
    )
    return ScanResultResponse(**result)


@router.post("/search")
async def search_reddit(
    request: SearchRequest,
    user_id: int = Depends(get_current_user_id),
):
    """Search Reddit for specific terms and analyze results."""
    import asyncio
    from app.services.reddit_service import RedditService

    reddit = RedditService()
    if not reddit.is_available:
        raise HTTPException(status_code=503, detail="Reddit API not configured")

    loop = asyncio.get_event_loop()
    posts = await loop.run_in_executor(
        None,
        lambda: reddit.search_reddit(
            query=request.query,
            subreddits=request.subreddits,
            limit=request.limit,
            time_filter=request.time_filter,
        ),
    )

    analyzed = await loop.run_in_executor(None, lambda: reddit.analyze_posts(posts))

    return {
        "query": request.query,
        "total_results": len(analyzed),
        "posts": analyzed,
    }


@router.get("/posts", response_model=list[RedditPostResponse])
async def list_flagged_posts(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    threat_level: Optional[str] = Query(None, pattern="^(low|high)$"),
    subreddit: Optional[str] = Query(None),
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List stored flagged Reddit posts with optional filters."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    query = select(RedditPost).where(RedditPost.scanned_at >= cutoff)

    if threat_level:
        query = query.where(RedditPost.threat_level == threat_level)
    if subreddit:
        query = query.where(RedditPost.subreddit == subreddit)

    query = query.order_by(desc(RedditPost.threat_score)).offset(offset).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/posts/{post_id}", response_model=RedditPostResponse)
async def get_post_detail(
    post_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed information about a specific flagged Reddit post."""
    result = await db.execute(
        select(RedditPost).where(RedditPost.id == post_id)
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@router.patch("/posts/{post_id}/review")
async def mark_post_reviewed(
    post_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Mark a flagged Reddit post as reviewed."""
    result = await db.execute(
        select(RedditPost).where(RedditPost.id == post_id)
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    post.is_reviewed = True
    post.reviewed_at = datetime.now(timezone.utc)
    return {"message": "Post marked as reviewed"}


@router.get("/trends", response_model=list[TrendDataPoint])
async def get_trends(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
):
    """Get daily trend data — post counts, threat scores, flagged content over time."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(RedditPost)
        .where(RedditPost.scanned_at >= cutoff)
        .order_by(RedditPost.scanned_at)
    )
    all_posts = result.scalars().all()

    if not all_posts:
        return []

    # Group by date
    from collections import defaultdict
    daily = defaultdict(list)
    for post in all_posts:
        day = post.scanned_at.strftime("%Y-%m-%d") if post.scanned_at else "unknown"
        daily[day].append(post)

    trends = []
    for day in sorted(daily.keys()):
        posts = daily[day]
        scores = [p.threat_score for p in posts if p.threat_score is not None]
        trends.append(TrendDataPoint(
            date=day,
            total_posts=len(posts),
            avg_threat_score=round(sum(scores) / len(scores), 4) if scores else 0,
            max_threat_score=round(max(scores), 4) if scores else 0,
            high_threat_count=len([p for p in posts if p.threat_level == "high"]),
        ))

    return trends


@router.get("/subreddits")
async def get_subreddit_stats(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
):
    """Get per-subreddit statistics from stored posts."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(RedditPost).where(RedditPost.scanned_at >= cutoff)
    )
    all_posts = result.scalars().all()

    from collections import defaultdict
    subreddit_data = defaultdict(lambda: {"posts": 0, "scores": [], "high_count": 0})

    for post in all_posts:
        sub = post.subreddit
        subreddit_data[sub]["posts"] += 1
        if post.threat_score is not None:
            subreddit_data[sub]["scores"].append(post.threat_score)
        if post.threat_level == "high":
            subreddit_data[sub]["high_count"] += 1

    stats = []
    for sub, data in sorted(subreddit_data.items(), key=lambda x: x[1]["posts"], reverse=True):
        scores = data["scores"]
        stats.append({
            "subreddit": sub,
            "total_posts": data["posts"],
            "avg_threat_score": round(sum(scores) / len(scores), 4) if scores else 0,
            "max_threat_score": round(max(scores), 4) if scores else 0,
            "high_threat_count": data["high_count"],
        })

    return stats
