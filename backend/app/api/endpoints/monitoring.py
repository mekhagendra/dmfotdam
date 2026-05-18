"""
Live-monitoring endpoints — CRUD for sources, alerts, dashboard metrics,
one-off scan trigger, and a WebSocket that streams new alerts in real time.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import re
from typing import Any, Dict
from urllib.parse import urlparse

from bson import ObjectId
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from pydantic import BaseModel

from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.core.database import (
    alerts_col,
    analyses_col,
    collected_items_col,
    sources_col,
)
from app.core.security import decode_access_token
from app.models.alert import AlertPublic
from app.models.source import SourceCreate, SourcePublic
from app.services.collector_manager import broadcaster, run_all_sources
import app.services.ml_service as _ml

router = APIRouter(prefix="/monitoring", tags=["monitoring"])
_settings = get_settings()


def _normalize_threat_score(raw: float | int | None) -> float:
    """Normalize mixed legacy score scales to 0..1 for consistent UI/API behavior."""
    if raw is None:
        return 0.0
    try:
        score = float(raw)
    except Exception:
        return 0.0

    # Legacy data may have been stored as percentage points (0..100).
    if score > 1.0 and score <= 100.0:
        score = score / 100.0

    # Guard against malformed values.
    if score < 0.0:
        return 0.0
    if score > 1.0:
        return 1.0
    return round(score, 4)


def _normalize_source_url(source_type: str, value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        raise HTTPException(status_code=400, detail="Source value is required")

    if source_type == "reddit":
        # Accept subreddit slug, r/subreddit, or full reddit URL.
        candidate = raw
        if candidate.startswith("http://") or candidate.startswith("https://"):
            parsed = urlparse(candidate)
            path = (parsed.path or "").strip("/")
            parts = [p for p in path.split("/") if p]
            if len(parts) >= 2 and parts[0].lower() == "r":
                candidate = parts[1]
            else:
                raise HTTPException(
                    status_code=400,
                    detail="For Reddit, provide a subreddit like 'worldnews' or a valid /r/<name> URL",
                )
        if candidate.lower().startswith("r/"):
            candidate = candidate[2:]

        candidate = candidate.strip()
        if not re.fullmatch(r"[A-Za-z0-9_]{2,21}", candidate):
            raise HTTPException(
                status_code=400,
                detail="Invalid subreddit format",
            )
        return candidate

    # RSS + Website(URL): require absolute http/https URL
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(
            status_code=400,
            detail="Provide a valid http/https URL",
        )
    return raw


# ---------- dto helpers ----------


def _src_public(doc: dict) -> SourcePublic:
    return SourcePublic(
        id=str(doc["_id"]),
        name=doc["name"],
        url=doc["url"],
        source_type=doc["source_type"],
        keywords=doc.get("keywords") or [],
        is_active=doc.get("is_active", True),
        check_interval=doc.get("check_interval", 300),
        last_checked=doc.get("last_checked"),
        created_at=doc["created_at"],
    )


def _alert_public(doc: dict) -> AlertPublic:
    details = doc.get("details") or {}
    return AlertPublic(
        id=str(doc["_id"]),
        title=doc["title"],
        description=doc.get("description"),
        threat_level=doc["threat_level"],
        threat_score=_normalize_threat_score(doc.get("threat_score", 0.0)),
        source=doc.get("source"),
        source_name=details.get("source_name"),
        source_type=doc.get("source_type"),
        is_read=doc.get("is_read", False),
        is_resolved=doc.get("is_resolved", False),
        created_at=doc["created_at"],
    )


class DashboardMetrics(BaseModel):
    model_config = {"protected_namespaces": ()}
    
    total_analyses: int
    total_alerts: int
    critical_alerts: int
    high_alerts: int
    active_sources: int
    avg_threat_score: float
    # New fields
    medium_alerts: int
    low_alerts: int
    category_breakdown: Dict[str, int]
    threat_trend_24h: float | None = None
    analyses_today: int
    source_breakdown: Dict[str, int]
    active_model: str | None = None
    model_f1: float | None = None


class SourceTrendPoint(BaseModel):
    date: str
    source_id: str
    source_name: str
    source_type: str
    item_count: int
    avg_threat_score: float


class SourceTrendResponse(BaseModel):
    days: int
    points: list[SourceTrendPoint]


class CollectedItemPublic(BaseModel):
    id: str
    source_id: str
    source_name: str
    source_type: str
    title: str
    text: str | None = None
    url: str | None = None
    threat_level: str
    threat_score: float
    collected_at: datetime


# ---------- sources ----------


@router.post("/sources", response_model=SourcePublic, status_code=201)
async def create_source(
    payload: SourceCreate, current=Depends(get_current_user)
) -> SourcePublic:
    if current.get("role") == "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admins cannot add monitoring sources from this page",
        )

    owner_id = current.get("_id")
    if await sources_col().find_one({"name": payload.name, "owner_id": owner_id}):
        raise HTTPException(status_code=400, detail="Source name already exists")

    normalized_url = _normalize_source_url(payload.source_type.value, payload.url)

    if await sources_col().find_one(
        {
            "owner_id": owner_id,
            "source_type": payload.source_type.value,
            "url": normalized_url,
        }
    ):
        raise HTTPException(status_code=400, detail="This source is already added")

    doc: dict[str, Any] = {
        "name": payload.name,
        "url": normalized_url,
        "source_type": payload.source_type.value,
        "keywords": payload.keywords,
        "is_active": True,
        "check_interval": payload.check_interval,
        "last_checked": None,
        "owner_id": owner_id,
        "created_at": datetime.now(timezone.utc),
    }
    res = await sources_col().insert_one(doc)
    doc["_id"] = res.inserted_id
    return _src_public(doc)


@router.get("/sources", response_model=list[SourcePublic])
async def list_sources(current=Depends(get_current_user)) -> list[SourcePublic]:
    cursor = sources_col().find({"owner_id": current.get("_id")}).sort("created_at", -1)
    return [_src_public(d) async for d in cursor]


@router.delete("/sources/{source_id}", status_code=204, response_model=None)
async def delete_source(source_id: str, current=Depends(get_current_user)):
    try:
        oid = ObjectId(source_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid source id")
    res = await sources_col().delete_one({"_id": oid, "owner_id": current.get("_id")})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Source not found")


# ---------- alerts ----------


@router.get("/alerts", response_model=list[AlertPublic])
async def list_alerts(current=Depends(get_current_user)) -> list[AlertPublic]:
    owner_id = str(current.get("_id"))
    cursor = alerts_col().find({"owner_id": owner_id}).sort("created_at", -1).limit(100)
    return [_alert_public(d) async for d in cursor]


@router.patch("/alerts/{alert_id}/read")
async def mark_alert_read(alert_id: str, current=Depends(get_current_user)) -> dict:
    try:
        oid = ObjectId(alert_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid alert id")
    res = await alerts_col().update_one(
        {"_id": oid, "owner_id": str(current.get("_id"))},
        {"$set": {"is_read": True}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"message": "Alert marked as read"}


@router.patch("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str, current=Depends(get_current_user)) -> dict:
    try:
        oid = ObjectId(alert_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid alert id")
    res = await alerts_col().update_one(
        {"_id": oid, "owner_id": str(current.get("_id"))},
        {
            "$set": {
                "is_resolved": True,
                "resolved_at": datetime.now(timezone.utc),
            }
        },
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"message": "Alert resolved"}


@router.get("/items", response_model=list[CollectedItemPublic])
async def list_collected_items(
    days: int = 7,
    limit: int = 200,
    current=Depends(get_current_user),
) -> list[CollectedItemPublic]:
    """List recently scanned monitoring items for current user's sources."""
    clamped_days = max(1, min(days, 180))
    clamped_limit = max(1, min(limit, 1000))
    since = datetime.now(timezone.utc) - timedelta(days=clamped_days)

    owned_sources = [
        s
        async for s in sources_col().find(
            {"owner_id": current.get("_id")},
            {"_id": 1, "name": 1, "source_type": 1},
        )
    ]
    if not owned_sources:
        return []

    source_map: Dict[str, Dict[str, str]] = {
        str(s["_id"]): {
            "name": s.get("name", str(s["_id"])),
            "source_type": s.get("source_type", "unknown"),
        }
        for s in owned_sources
    }
    source_ids = list(source_map.keys())

    cursor = (
        collected_items_col()
        .find(
            {
                "source_id": {"$in": source_ids},
                "source_type": {"$in": ["reddit", "rss", "telegram", "url"]},
                "collected_at": {"$gte": since},
            }
        )
        .sort("collected_at", -1)
        .limit(clamped_limit)
    )

    items: list[CollectedItemPublic] = []
    async for doc in cursor:
        sid = doc.get("source_id")
        if not sid:
            continue
        src = source_map.get(str(sid))
        if not src:
            continue
        items.append(
            CollectedItemPublic(
                id=str(doc.get("_id")),
                source_id=str(sid),
                source_name=src["name"],
                source_type=src["source_type"],
                title=doc.get("title") or "(untitled)",
                text=doc.get("text"),
                url=doc.get("url"),
                threat_level=doc.get("threat_level") or "low",
                threat_score=_normalize_threat_score(doc.get("threat_score") or 0.0),
                collected_at=doc.get("collected_at") or datetime.now(timezone.utc),
            )
        )

    return items


# ---------- dashboard ----------


@router.get("/dashboard/metrics", response_model=DashboardMetrics)
async def dashboard_metrics(current=Depends(get_current_user)) -> DashboardMetrics:
    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(hours=24)
    day_before = yesterday - timedelta(hours=24)
    user_id = str(current.get("_id"))
    analyses_match = {"user_id": user_id}
    unresolved_alert_match = {"owner_id": user_id, "is_resolved": False}
    owned_sources_match = {"owner_id": current.get("_id")}
    owned_source_ids = [
        str(src["_id"])
        async for src in sources_col().find(owned_sources_match, {"_id": 1})
    ]

    total_analyses = await analyses_col().count_documents(analyses_match)
    total_alerts = await alerts_col().count_documents({"owner_id": user_id})
    critical_alerts = await alerts_col().count_documents(
        {**unresolved_alert_match, "threat_level": "critical"}
    )
    high_alerts = await alerts_col().count_documents(
        {**unresolved_alert_match, "threat_level": "high"}
    )
    medium_alerts = await alerts_col().count_documents(
        {**unresolved_alert_match, "threat_level": "medium"}
    )
    low_alerts = await alerts_col().count_documents(
        {**unresolved_alert_match, "threat_level": "low"}
    )
    active_sources = await sources_col().count_documents({**owned_sources_match, "is_active": True})

    # avg_threat_score
    avg_score = 0.0
    try:
        pipeline_avg = [
            {"$match": {**analyses_match, "status": "completed"}},
            {"$group": {"_id": None, "avg": {"$avg": "$threat_score"}}},
        ]
        async for row in analyses_col().aggregate(pipeline_avg):
            avg_score = float(row.get("avg") or 0.0)
    except Exception:
        pass

    # analyses_today
    analyses_today = 0
    try:
        analyses_today = await analyses_col().count_documents(
            {**analyses_match, "created_at": {"$gte": yesterday}}
        )
    except Exception:
        pass

    # threat_trend_24h — compare avg of last 24h vs previous 24h
    threat_trend_24h: float | None = None
    try:
        pipeline_24h = [
            {
                "$match": {
                    **analyses_match,
                    "status": "completed",
                    "created_at": {"$gte": yesterday},
                }
            },
            {"$group": {"_id": None, "avg": {"$avg": "$threat_score"}}},
        ]
        avg_24h = 0.0
        has_24h = False
        async for row in analyses_col().aggregate(pipeline_24h):
            avg_24h = float(row.get("avg") or 0.0)
            has_24h = True

        pipeline_prev = [
            {
                "$match": {
                    **analyses_match,
                    "status": "completed",
                    "created_at": {"$gte": day_before, "$lt": yesterday},
                }
            },
            {"$group": {"_id": None, "avg": {"$avg": "$threat_score"}}},
        ]
        avg_prev = 0.0
        has_prev = False
        async for row in analyses_col().aggregate(pipeline_prev):
            avg_prev = float(row.get("avg") or 0.0)
            has_prev = True

        if has_24h or has_prev:
            threat_trend_24h = round(avg_24h - avg_prev, 4)
    except Exception:
        pass

    # category_breakdown — group completed analyses by threat_level (24h window)
    category_breakdown: Dict[str, int] = {}
    try:
        pipeline_cat = [
            {
                "$match": {
                    **analyses_match,
                    "status": "completed",
                    "created_at": {"$gte": yesterday},
                }
            },
            {
                "$group": {
                    "_id": "$threat_level",
                    "count": {"$sum": 1},
                }
            },
        ]
        async for row in analyses_col().aggregate(pipeline_cat):
            level = (row.get("_id") or "unknown").lower()
            category_breakdown[level] = row.get("count", 0)
    except Exception:
        pass

    # source_breakdown — count owned monitoring-source items by source_type
    source_breakdown: Dict[str, int] = {}
    try:
        if owned_source_ids:
            pipeline_src = [
                {"$match": {"source_id": {"$in": owned_source_ids}}},
                {"$group": {"_id": "$source_type", "count": {"$sum": 1}}},
            ]
            async for row in collected_items_col().aggregate(pipeline_src):
                src_type = row.get("_id") or "unknown"
                source_breakdown[src_type] = row.get("count", 0)
    except Exception:
        pass

    # Count upload-based analyses as "upload" in source_breakdown
    try:
        upload_count = await analyses_col().count_documents(
            {**analyses_match, "analysis_type": "document"}
        )
        if upload_count > 0:
            source_breakdown["upload"] = source_breakdown.get("upload", 0) + upload_count
    except Exception:
        pass

    # Count text analyses as "text" in source_breakdown
    try:
        text_count = await analyses_col().count_documents(
            {**analyses_match, "analysis_type": "text"}
        )
        if text_count > 0:
            source_breakdown["text"] = source_breakdown.get("text", 0) + text_count
    except Exception:
        pass

    return DashboardMetrics(
        total_analyses=total_analyses,
        total_alerts=total_alerts,
        critical_alerts=critical_alerts,
        high_alerts=high_alerts,
        medium_alerts=medium_alerts,
        low_alerts=low_alerts,
        active_sources=active_sources,
        avg_threat_score=round(avg_score, 4),
        category_breakdown=category_breakdown,
        threat_trend_24h=threat_trend_24h,
        analyses_today=analyses_today,
        source_breakdown=source_breakdown,
        active_model=_ml.ACTIVE_MODEL_NAME if _ml.ACTIVE_MODEL_NAME else None,
        model_f1=_ml.ACTIVE_MODEL_F1 if _ml.ACTIVE_MODEL_NAME else None,
    )


@router.get("/trends/source-daily", response_model=SourceTrendResponse)
async def source_daily_trends(days: int = 30, current=Depends(get_current_user)) -> SourceTrendResponse:
    """Return daily trend points grouped by source for the current user's added sources."""
    clamped_days = max(1, min(days, 180))
    since = datetime.now(timezone.utc) - timedelta(days=clamped_days)

    owned_sources = [
        s
        async for s in sources_col().find(
            {"owner_id": current.get("_id")},
            {"_id": 1, "name": 1, "source_type": 1},
        )
    ]
    if not owned_sources:
        return SourceTrendResponse(days=clamped_days, points=[])

    source_map: Dict[str, Dict[str, str]] = {
        str(s["_id"]): {
            "name": s.get("name", str(s["_id"])),
            "source_type": s.get("source_type", "unknown"),
        }
        for s in owned_sources
    }
    source_ids = list(source_map.keys())

    pipeline = [
        {
            "$match": {
                "source_id": {"$in": source_ids},
                "source_type": {"$in": ["reddit", "rss", "telegram", "url"]},
                "collected_at": {"$gte": since},
            }
        },
        {
            "$group": {
                "_id": {
                    "date": {
                        "$dateToString": {
                            "format": "%Y-%m-%d",
                            "date": "$collected_at",
                            "timezone": _settings.TIMEZONE,
                        }
                    },
                    "source_id": "$source_id",
                },
                "item_count": {"$sum": 1},
                "avg_threat_score": {"$avg": "$threat_score"},
            }
        },
        {"$sort": {"_id.date": 1, "_id.source_id": 1}},
    ]

    points: list[SourceTrendPoint] = []
    async for row in collected_items_col().aggregate(pipeline):
        src_id = row.get("_id", {}).get("source_id")
        date = row.get("_id", {}).get("date")
        if not src_id or not date:
            continue
        src_meta = source_map.get(src_id)
        if not src_meta:
            continue
        points.append(
            SourceTrendPoint(
                date=date,
                source_id=src_id,
                source_name=src_meta["name"],
                source_type=src_meta["source_type"],
                item_count=int(row.get("item_count") or 0),
                avg_threat_score=_normalize_threat_score(row.get("avg_threat_score") or 0.0),
            )
        )

    return SourceTrendResponse(days=clamped_days, points=points)


# ---------- manual scan trigger ----------


@router.post("/scan/run")
async def run_scan_now(current=Depends(get_current_user)) -> dict:
    """Trigger an immediate poll of the current user's active sources."""
    return await run_all_sources(owner_id=current.get("_id"))


@router.delete("/data/reset")
async def reset_scanned_data(current=Depends(get_current_user)) -> dict:
    """Delete only the current user's scanned monitoring data (alerts + collected items)."""
    owner_id_obj = current.get("_id")
    owner_id_str = str(owner_id_obj)

    owned_source_ids = [
        str(src["_id"])
        async for src in sources_col().find({"owner_id": owner_id_obj}, {"_id": 1})
    ]

    alerts_res = await alerts_col().delete_many({"owner_id": owner_id_str})
    items_res = (
        await collected_items_col().delete_many({"source_id": {"$in": owned_source_ids}})
        if owned_source_ids
        else None
    )

    return {
        "message": "Scanned data reset completed",
        "alerts_deleted": alerts_res.deleted_count,
        "items_deleted": items_res.deleted_count if items_res else 0,
    }


# ---------- real-time alert stream ----------


@router.websocket("/live")
async def live_alerts(websocket: WebSocket) -> None:
    """
    Stream newly-raised alerts over WebSocket.

    The client must either:
      * send the JWT as the `token` query param:  /api/v1/monitoring/live?token=xxx
      * or send `{"type": "auth", "token": "xxx"}` as the first message.
    """
    await websocket.accept()

    token = websocket.query_params.get("token")
    user_id: str | None = None
    try:
        if not token:
            msg = await asyncio.wait_for(websocket.receive_json(), timeout=10)
            token = msg.get("token")
        if not token:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        payload = decode_access_token(token)
        user_id = str(payload.get("sub") or "")
        if not user_id:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    await broadcaster.subscribe(queue)
    try:
        await websocket.send_json({"event": "connected"})
        while True:
            event = await queue.get()
            if event.get("event") == "alert":
                alert = event.get("alert") or {}
                if alert.get("owner_id") != user_id:
                    continue
            await websocket.send_json(event)
    except WebSocketDisconnect:
        pass
    finally:
        await broadcaster.unsubscribe(queue)
