"""
WebSocket endpoint — pushes new alerts and metrics updates to connected clients.
Path: /api/v1/ws/live
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jose import JWTError

from app.core.logging import get_logger
from app.core.security import decode_access_token

logger = get_logger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])

connected_clients: Dict[WebSocket, str] = {}
_clients_lock = asyncio.Lock()


async def broadcast_alert(alert_dict: Dict[str, Any]) -> None:
    """Send a new alert to all connected WebSocket clients."""
    message = {"type": "alert", "data": alert_dict}
    await _broadcast(message)


async def broadcast_metrics(metrics_dict: Dict[str, Any]) -> None:
    """Send updated metrics to all connected WebSocket clients."""
    message = {"type": "metrics", "data": metrics_dict}
    await _broadcast(message)


async def _broadcast(message: Dict[str, Any]) -> None:
    """Send a JSON message to every connected client. Remove disconnected ones."""
    async with _clients_lock:
        clients = list(connected_clients.items())

    disconnected: list[WebSocket] = []
    for ws, user_id in clients:
        try:
            if message.get("type") == "alert":
                alert_owner = str((message.get("data") or {}).get("owner_id") or "")
                if not alert_owner or alert_owner != user_id:
                    continue
            await ws.send_json(message)
        except Exception:
            disconnected.append(ws)

    if disconnected:
        async with _clients_lock:
            for ws in disconnected:
                connected_clients.pop(ws, None)


@router.websocket("/live")
async def ws_live(websocket: WebSocket) -> None:
    """
    Real-time alert + metrics stream.
    Requires a valid JWT token as query parameter: ?token=<jwt>
    Rejects with code 4001 if invalid.
    """
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001)
        return

    user_id: str | None = None
    try:
        payload = decode_access_token(token)
        user_id = str(payload.get("sub") or "")
        if not user_id:
            raise JWTError("invalid-sub")
    except (JWTError, Exception):
        try:
            await websocket.accept()
            await websocket.close(code=4001)
        except Exception:
            pass
        return

    await websocket.accept()

    async with _clients_lock:
        connected_clients[websocket] = user_id

    logger.info("ws.client_connected", clients=len(connected_clients))

    try:
        # Send initial metrics snapshot
        try:
            metrics = await _build_current_metrics(user_id)
            await websocket.send_json({"type": "metrics", "data": metrics})
        except Exception as exc:
            logger.warning("ws.initial_metrics_failed", error=str(exc))

        # Keep connection alive — wait for client messages or disconnect
        while True:
            try:
                await websocket.receive_text()
            except WebSocketDisconnect:
                break
    finally:
        async with _clients_lock:
            connected_clients.pop(websocket, None)
        logger.info("ws.client_disconnected", clients=len(connected_clients))


async def _build_current_metrics(user_id: str) -> Dict[str, Any]:
    """Build a metrics dict for the initial WebSocket payload."""
    from datetime import datetime, timedelta, timezone

    from bson import ObjectId

    from app.core.database import alerts_col, analyses_col, sources_col
    from app.core.database import collected_items_col
    import app.services.ml_service as _ml

    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(hours=24)
    owner_id_obj = ObjectId(user_id)
    analyses_match = {"user_id": user_id}
    unresolved_alert_match = {"owner_id": user_id, "is_resolved": False}
    owned_source_ids = [
        str(src["_id"]) async for src in sources_col().find({"owner_id": owner_id_obj}, {"_id": 1})
    ]

    try:
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
        active_sources = await sources_col().count_documents({"owner_id": owner_id_obj, "is_active": True})
        analyses_today = await analyses_col().count_documents(
            {**analyses_match, "created_at": {"$gte": yesterday}}
        )

        avg_score = 0.0
        pipeline_avg = [
            {"$match": {**analyses_match, "status": "completed"}},
            {"$group": {"_id": None, "avg": {"$avg": "$threat_score"}}},
        ]
        async for row in analyses_col().aggregate(pipeline_avg):
            avg_score = float(row.get("avg") or 0.0)

        # source_breakdown
        source_breakdown: Dict[str, int] = {}
        try:
            if owned_source_ids:
                async for row in collected_items_col().aggregate(
                    [
                        {"$match": {"source_id": {"$in": owned_source_ids}}},
                        {"$group": {"_id": "$source_type", "count": {"$sum": 1}}},
                    ]
                ):
                    source_breakdown[row.get("_id") or "unknown"] = row.get("count", 0)
            upload_count = await analyses_col().count_documents({**analyses_match, "analysis_type": "document"})
            if upload_count:
                source_breakdown["upload"] = source_breakdown.get("upload", 0) + upload_count
            text_count = await analyses_col().count_documents({**analyses_match, "analysis_type": "text"})
            if text_count:
                source_breakdown["text"] = source_breakdown.get("text", 0) + text_count
        except Exception:
            pass

        return {
            "total_analyses": total_analyses,
            "total_alerts": total_alerts,
            "critical_alerts": critical_alerts,
            "high_alerts": high_alerts,
            "medium_alerts": medium_alerts,
            "low_alerts": low_alerts,
            "active_sources": active_sources,
            "avg_threat_score": round(avg_score, 4),
            "category_breakdown": {},
            "threat_trend_24h": None,
            "analyses_today": analyses_today,
            "source_breakdown": source_breakdown,
            "active_model": _ml.ACTIVE_MODEL_NAME if _ml.ACTIVE_MODEL_NAME else None,
            "model_f1": _ml.ACTIVE_MODEL_F1 if _ml.ACTIVE_MODEL_NAME else None,
        }
    except Exception as exc:
        logger.warning("ws.metrics_build_failed", error=str(exc))
        return {}
