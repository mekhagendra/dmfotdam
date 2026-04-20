"""
Reddit-specific endpoints on top of the unified collector architecture.

Historically this router wired SQLAlchemy `RedditPost` models. That layer
is now replaced by the generic `collected_items` collection in MongoDB
plus the `/monitoring/*` endpoints. This module exposes a few thin
conveniences: trigger a scan of arbitrary subreddits ad-hoc and query the
stored collected items filtered to `source_type == "reddit"`.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.dependencies import get_current_user
from app.core.database import collected_items_col, sources_col
from app.services import reddit_collector
from app.services.collector_manager import run_one_source

router = APIRouter(prefix="/reddit", tags=["reddit"])

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DEFAULT_SUBREDDITS = [
    "news", "worldnews", "CredibleDefense", "geopolitics",
    "IntelligenceNews", "terrorism", "SecurityAnalysis",
    "PoliticalDiscussion", "ConflictNews",
]


def _serialise_item(d: dict) -> dict:
    """Turn a collected_items Mongo doc into a JSON-safe dict."""
    cls = d.get("classification") or {}
    return {
        "id": str(d["_id"]),
        "reddit_id": d.get("external_id", ""),
        "subreddit": d.get("source", ""),
        "title": d.get("title", ""),
        "text": d.get("text", ""),
        "author": d.get("author", ""),
        "url": d.get("url", ""),
        "score": d.get("score", 0),
        "num_comments": d.get("num_comments", 0),
        "threat_score": d.get("threat_score", 0.0),
        "threat_level": d.get("threat_level", "low"),
        "analysis_details": cls,
        "posted_at": _iso(d.get("posted_at")),
        "scanned_at": _iso(d.get("collected_at")),
        "is_reviewed": d.get("is_reviewed", False),
    }


def _iso(v) -> Optional[str]:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.isoformat()
    return str(v)


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class ScanRequest(BaseModel):
    subreddits: list[str] = Field(default_factory=list)
    limit: int = Field(50, ge=1, le=100)
    threat_threshold: float | None = None


class SearchRequest(BaseModel):
    query: str
    subreddits: list[str] = Field(default_factory=list)
    limit: int = Field(25, ge=1, le=100)
    time_filter: str | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/scan")
async def scan_subreddits(
    req: ScanRequest, current=Depends(get_current_user)
) -> dict:
    """Trigger an immediate scan of one or more subreddits."""
    subs = req.subreddits or _DEFAULT_SUBREDDITS

    results = []
    total_scanned = 0
    total_flagged = 0
    new_stored = 0
    for sub in subs:
        existing = await sources_col().find_one(
            {"source_type": "reddit", "url": sub}
        )
        if existing is None:
            doc = {
                "name": f"Reddit r/{sub}",
                "url": sub,
                "source_type": "reddit",
                "keywords": [],
                "is_active": True,
                "check_interval": 300,
                "last_checked": None,
                "created_at": datetime.now(timezone.utc),
            }
            ins = await sources_col().insert_one(doc)
            doc["_id"] = ins.inserted_id
            existing = doc
        r = await run_one_source(existing)
        results.append(r)
        total_scanned += r.get("fetched", 0)
        new_stored += r.get("new", 0)

    # Count items above threshold that were just collected
    threshold = req.threat_threshold or 0.5
    total_flagged = await collected_items_col().count_documents(
        {"source_type": "reddit", "threat_score": {"$gte": threshold}}
    )

    return {
        "status": "completed",
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "total_scanned": total_scanned,
        "total_flagged": total_flagged,
        "new_posts_stored": new_stored,
        "new_alerts_generated": 0,
        "reason": None,
    }


@router.get("/posts")
async def list_reddit_posts(
    threat_level: Optional[str] = Query(None),
    subreddit: Optional[str] = Query(None),
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current=Depends(get_current_user),
) -> list[dict]:
    """List collected reddit items with optional filters."""
    filt: dict = {"source_type": "reddit"}
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    filt["collected_at"] = {"$gte": cutoff}
    if threat_level:
        filt["threat_level"] = threat_level
    if subreddit:
        filt["source"] = subreddit

    cursor = (
        collected_items_col()
        .find(filt)
        .sort("collected_at", -1)
        .skip(offset)
        .limit(limit)
    )
    return [_serialise_item(d) async for d in cursor]


@router.get("/posts/{post_id}")
async def get_reddit_post(post_id: str, current=Depends(get_current_user)) -> dict:
    """Fetch a single reddit item by its Mongo _id."""
    if not ObjectId.is_valid(post_id):
        raise HTTPException(status_code=404, detail="Post not found")
    doc = await collected_items_col().find_one(
        {"_id": ObjectId(post_id), "source_type": "reddit"}
    )
    if doc is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return _serialise_item(doc)


@router.patch("/posts/{post_id}/review")
async def mark_post_reviewed(post_id: str, current=Depends(get_current_user)) -> dict:
    """Mark a reddit item as reviewed."""
    if not ObjectId.is_valid(post_id):
        raise HTTPException(status_code=404, detail="Post not found")
    result = await collected_items_col().update_one(
        {"_id": ObjectId(post_id), "source_type": "reddit"},
        {"$set": {"is_reviewed": True}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Post not found")
    return {"status": "ok"}


@router.get("/trends")
async def reddit_trends(
    days: int = Query(30, ge=1, le=365),
    current=Depends(get_current_user),
) -> list[dict]:
    """Daily aggregated trend data for reddit items."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    pipeline = [
        {"$match": {"source_type": "reddit", "collected_at": {"$gte": cutoff}}},
        {
            "$group": {
                "_id": {
                    "$dateToString": {"format": "%Y-%m-%d", "date": "$collected_at"}
                },
                "total_posts": {"$sum": 1},
                "avg_threat_score": {"$avg": "$threat_score"},
                "max_threat_score": {"$max": "$threat_score"},
                "high_threat_count": {
                    "$sum": {
                        "$cond": [{"$gte": ["$threat_score", 0.5]}, 1, 0]
                    }
                },
            }
        },
        {"$sort": {"_id": 1}},
    ]
    results = []
    async for doc in collected_items_col().aggregate(pipeline):
        results.append(
            {
                "date": doc["_id"],
                "total_posts": doc["total_posts"],
                "avg_threat_score": round(doc["avg_threat_score"], 4),
                "max_threat_score": round(doc["max_threat_score"], 4),
                "high_threat_count": doc["high_threat_count"],
            }
        )
    return results


@router.get("/subreddits")
async def subreddit_stats(
    days: int = Query(30, ge=1, le=365),
    current=Depends(get_current_user),
) -> list[dict]:
    """Per-subreddit aggregated stats."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    pipeline = [
        {"$match": {"source_type": "reddit", "collected_at": {"$gte": cutoff}}},
        {
            "$group": {
                "_id": "$source",
                "total_posts": {"$sum": 1},
                "avg_threat_score": {"$avg": "$threat_score"},
                "max_threat_score": {"$max": "$threat_score"},
                "high_threat_count": {
                    "$sum": {
                        "$cond": [{"$gte": ["$threat_score", 0.5]}, 1, 0]
                    }
                },
            }
        },
        {"$sort": {"total_posts": -1}},
    ]
    results = []
    async for doc in collected_items_col().aggregate(pipeline):
        results.append(
            {
                "subreddit": doc["_id"] or "unknown",
                "total_posts": doc["total_posts"],
                "avg_threat_score": round(doc["avg_threat_score"], 4),
                "max_threat_score": round(doc["max_threat_score"], 4),
                "high_threat_count": doc["high_threat_count"],
            }
        )
    return results


@router.post("/search")
async def search_reddit(
    req: SearchRequest, current=Depends(get_current_user)
) -> dict:
    """Search collected reddit items by text query."""
    filt: dict = {"source_type": "reddit"}
    if req.subreddits:
        filt["source"] = {"$in": req.subreddits}

    # Text search via regex (case-insensitive)
    import re
    pattern = re.escape(req.query)
    text_match = {"$regex": pattern, "$options": "i"}
    filt["$or"] = [{"title": text_match}, {"text": text_match}]

    cursor = (
        collected_items_col()
        .find(filt)
        .sort("threat_score", -1)
        .limit(req.limit)
    )
    posts = []
    async for d in cursor:
        posts.append(
            {
                "reddit_id": d.get("external_id", ""),
                "subreddit": d.get("source", ""),
                "title": d.get("title", ""),
                "text": d.get("text", ""),
                "author": d.get("author", ""),
                "url": d.get("url", ""),
                "score": d.get("score", 0),
                "num_comments": d.get("num_comments", 0),
                "threat_score": d.get("threat_score", 0.0),
                "threat_level": d.get("threat_level", "low"),
                "created_utc": _iso(d.get("posted_at") or d.get("collected_at")),
                "analysis": d.get("classification"),
            }
        )
    return {"query": req.query, "total_results": len(posts), "posts": posts}


@router.get("/flagged")
async def list_flagged_reddit_items(
    limit: int = Query(50, ge=1, le=200),
    min_score: float = Query(0.5, ge=0.0, le=1.0),
    current=Depends(get_current_user),
) -> list[dict]:
    """List reddit items that scored above a threshold."""
    cursor = (
        collected_items_col()
        .find({"source_type": "reddit", "threat_score": {"$gte": min_score}})
        .sort("threat_score", -1)
        .limit(limit)
    )
    out: list[dict] = []
    async for d in cursor:
        out.append(
            {
                "external_id": d.get("external_id"),
                "title": d.get("title"),
                "url": d.get("url"),
                "source": d.get("source"),
                "author": d.get("author"),
                "threat_score": d.get("threat_score"),
                "threat_level": d.get("threat_level"),
                "collected_at": d.get("collected_at"),
            }
        )
    return out


@router.get("/status")
async def reddit_status(current=Depends(get_current_user)) -> dict:
    """Report whether Reddit credentials are set up and stats."""
    client = reddit_collector._reddit_client()
    total = await collected_items_col().count_documents({"source_type": "reddit"})

    # Find the most recent last_checked across all reddit sources
    latest_source = await sources_col().find_one(
        {"source_type": "reddit", "last_checked": {"$ne": None}},
        sort=[("last_checked", -1)],
        projection={"last_checked": 1},
    )
    last_scan = _iso(latest_source["last_checked"]) if latest_source else None

    return {
        "available": client is not None,
        "message": "Reddit API connected" if client else "Reddit credentials not configured",
        "default_subreddits": _DEFAULT_SUBREDDITS,
        "total_stored_posts": total,
        "last_scan_time": last_scan,
    }
