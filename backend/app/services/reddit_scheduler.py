"""
Reddit monitoring scheduler — runs daily scans automatically.

Uses asyncio background task (started in FastAPI lifespan) to:
  - Run a Reddit scan at a configurable interval (default: every 24 hours)
  - Store flagged posts in the database as RedditPost records
  - Generate alerts for high-threat content
  - Compute daily trend data

Can also be triggered manually via the API.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional

from app.core.logging import get_logger

logger = get_logger(__name__)

# Global reference to the scheduler task
_scheduler_task: Optional[asyncio.Task] = None


async def run_daily_reddit_scan(
    subreddits: Optional[list[str]] = None,
    limit: int = 100,
    threat_threshold: float = 0.3,
) -> dict:
    """
    Execute a full Reddit scan, store results in DB, and generate alerts.

    This runs the PRAW calls in a thread pool (they are blocking I/O)
    and then stores flagged content in the database asynchronously.
    """
    from app.services.reddit_service import RedditService
    from app.core.database import async_session
    from app.models.reddit_post import RedditPost
    from app.models.alert import Alert
    from sqlalchemy import select

    reddit = RedditService()
    if not reddit.is_available:
        logger.warning("Reddit API not available, skipping scan")
        return {"status": "skipped", "reason": "Reddit API not configured"}

    # Run blocking PRAW calls in thread pool
    loop = asyncio.get_event_loop()
    scan_result = await loop.run_in_executor(
        None,
        lambda: reddit.run_scan(
            subreddits=subreddits,
            limit=limit,
            threat_threshold=threat_threshold,
        ),
    )

    flagged = scan_result.get("flagged_posts", [])
    scan_time = datetime.now(timezone.utc)

    async with async_session() as session:
        new_posts = 0
        new_alerts = 0

        for post in flagged:
            # Check if this post was already stored
            existing = await session.execute(
                select(RedditPost).where(RedditPost.reddit_id == post["reddit_id"])
            )
            if existing.scalar_one_or_none():
                continue

            # Store the flagged post
            reddit_post = RedditPost(
                reddit_id=post["reddit_id"],
                subreddit=post["subreddit"],
                title=post["title"],
                text=post.get("selftext", ""),
                author=post.get("author", "[deleted]"),
                url=post.get("url", ""),
                score=post.get("score", 0),
                num_comments=post.get("num_comments", 0),
                threat_score=post["threat_score"],
                threat_level=post["threat_level"],
                analysis_details=post.get("analysis"),
                posted_at=datetime.fromisoformat(post["created_utc"]) if post.get("created_utc") else scan_time,
                scanned_at=scan_time,
            )
            session.add(reddit_post)
            new_posts += 1

            # Generate alert for high-threat posts
            if post["threat_score"] >= 0.5:
                alert = Alert(
                    title=f"Reddit: {post['title'][:100]}",
                    description=(
                        f"Flagged content from r/{post['subreddit']} "
                        f"(score: {post['threat_score']:.2f}). "
                        f"URL: {post.get('url', 'N/A')}"
                    ),
                    threat_level=post["threat_level"],
                    threat_score=post["threat_score"],
                    source=post.get("url", f"r/{post['subreddit']}"),
                    source_type="reddit",
                    details={
                        "reddit_id": post["reddit_id"],
                        "subreddit": post["subreddit"],
                        "author": post.get("author"),
                        "analysis": post.get("analysis"),
                    },
                )
                session.add(alert)
                new_alerts += 1

        await session.commit()

    logger.info(
        "Reddit daily scan stored",
        new_posts=new_posts,
        new_alerts=new_alerts,
        total_flagged=len(flagged),
    )

    return {
        "status": "completed",
        "scan_time": scan_time.isoformat(),
        "total_scanned": scan_result["scan_summary"]["total"],
        "total_flagged": len(flagged),
        "new_posts_stored": new_posts,
        "new_alerts_generated": new_alerts,
        "scan_summary": scan_result["scan_summary"],
    }


async def compute_daily_trends(days: int = 30) -> list[dict]:
    """
    Compute daily trend data from stored Reddit posts.

    Returns a list of daily aggregates:
      date, total_posts, flagged_posts, avg_threat_score, top_subreddits
    """
    from app.core.database import async_session
    from app.models.reddit_post import RedditPost
    from sqlalchemy import select, func, cast, Date

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    async with async_session() as session:
        # Daily aggregates
        results = await session.execute(
            select(
                cast(RedditPost.scanned_at, Date).label("date"),
                func.count().label("total_posts"),
                func.avg(RedditPost.threat_score).label("avg_threat_score"),
                func.max(RedditPost.threat_score).label("max_threat_score"),
                func.sum(
                    func.cast(RedditPost.threat_level == "high", Integer)
                ).label("high_threat_count"),
            )
            .where(RedditPost.scanned_at >= cutoff)
            .group_by(cast(RedditPost.scanned_at, Date))
            .order_by(cast(RedditPost.scanned_at, Date).desc())
        )

        # Fallback: simpler query without cast issues
        trends = []
        try:
            rows = results.all()
            for row in rows:
                trends.append({
                    "date": str(row.date),
                    "total_posts": row.total_posts,
                    "avg_threat_score": round(float(row.avg_threat_score or 0), 4),
                    "max_threat_score": round(float(row.max_threat_score or 0), 4),
                    "high_threat_count": int(row.high_threat_count or 0),
                })
        except Exception:
            # Fallback: manual aggregation
            all_posts_result = await session.execute(
                select(RedditPost)
                .where(RedditPost.scanned_at >= cutoff)
                .order_by(RedditPost.scanned_at.desc())
            )
            all_posts = all_posts_result.scalars().all()

            from collections import defaultdict
            daily = defaultdict(list)
            for post in all_posts:
                day = post.scanned_at.strftime("%Y-%m-%d") if post.scanned_at else "unknown"
                daily[day].append(post)

            for day, posts in sorted(daily.items(), reverse=True):
                scores = [p.threat_score for p in posts if p.threat_score is not None]
                trends.append({
                    "date": day,
                    "total_posts": len(posts),
                    "avg_threat_score": round(sum(scores) / len(scores), 4) if scores else 0,
                    "max_threat_score": round(max(scores), 4) if scores else 0,
                    "high_threat_count": len([p for p in posts if p.threat_level == "high"]),
                })

    return trends


async def generate_daily_report(date: Optional[datetime] = None, top_n: int = 100) -> str:
    """
    Generate a CSV daily report of the top-N extremist posts for a given date.

    Saves to: data/datasets/eda_output/daily_reports/YYYY-MM-DD.csv
    Returns the path to the saved file.
    """
    import csv
    import os
    from app.core.database import async_session
    from app.models.reddit_post import RedditPost
    from sqlalchemy import select

    report_date = date or datetime.now(timezone.utc)
    date_str = report_date.strftime("%Y-%m-%d")

    # Query top-N flagged posts for that day ordered by threat score
    day_start = report_date.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)

    async with async_session() as session:
        result = await session.execute(
            select(RedditPost)
            .where(RedditPost.scanned_at >= day_start)
            .where(RedditPost.scanned_at < day_end)
            .order_by(RedditPost.threat_score.desc())
            .limit(top_n)
        )
        posts = result.scalars().all()

    if not posts:
        logger.info(f"No posts found for {date_str}, skipping daily report")
        return ""

    report_dir = os.path.join("data", "datasets", "eda_output", "daily_reports")
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, f"{date_str}.csv")

    fieldnames = [
        "rank", "reddit_id", "subreddit", "title", "author", "url",
        "score", "num_comments", "threat_score", "threat_level",
        "keyword_hits", "categories_detected", "posted_at", "scanned_at",
    ]

    with open(report_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for rank, post in enumerate(posts, start=1):
            details = post.analysis_details or {}
            writer.writerow({
                "rank": rank,
                "reddit_id": post.reddit_id,
                "subreddit": post.subreddit,
                "title": post.title,
                "author": post.author,
                "url": post.url,
                "score": post.score,
                "num_comments": post.num_comments,
                "threat_score": round(post.threat_score, 4),
                "threat_level": post.threat_level,
                "keyword_hits": "|".join(details.get("keyword_hits", {}).keys()) if isinstance(details.get("keyword_hits"), dict) else "",
                "categories_detected": "|".join(details.get("categories_detected", [])),
                "posted_at": post.posted_at.isoformat() if post.posted_at else "",
                "scanned_at": post.scanned_at.isoformat() if post.scanned_at else "",
            })

    logger.info(f"Daily report saved: {report_path} ({len(posts)} posts)")
    return report_path


async def _scheduler_loop(interval_hours: int = 24):
    """Background loop that runs Reddit scan at set intervals."""
    logger.info(f"Reddit scheduler started (interval: {interval_hours}h)")

    while True:
        try:
            logger.info("Running scheduled Reddit scan...")
            result = await run_daily_reddit_scan()
            logger.info("Scheduled scan result", **{k: v for k, v in result.items() if k != "scan_summary"})
            # Generate the daily report after every scan
            report_path = await generate_daily_report(top_n=100)
            if report_path:
                logger.info(f"Daily report ready: {report_path}")
        except Exception as e:
            logger.error("Scheduled Reddit scan failed", error=str(e))

        # Sleep until next scan
        await asyncio.sleep(interval_hours * 3600)


def start_scheduler(interval_hours: int = 24):
    """Start the background scheduler task. Call during app lifespan startup."""
    global _scheduler_task

    if _scheduler_task is not None:
        logger.warning("Reddit scheduler already running")
        return

    _scheduler_task = asyncio.create_task(_scheduler_loop(interval_hours))
    logger.info("Reddit scheduler task created")


def stop_scheduler():
    """Stop the background scheduler."""
    global _scheduler_task
    if _scheduler_task:
        _scheduler_task.cancel()
        _scheduler_task = None
        logger.info("Reddit scheduler stopped")


# Fix import for Integer type
from sqlalchemy import Integer  # noqa: E402
