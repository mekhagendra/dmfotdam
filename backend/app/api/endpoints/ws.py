"""
WebSocket endpoint — pushes new alerts and metrics updates to connected clients.
Path: /api/v1/ws/live
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jose import JWTError

from app.core.logging import get_logger
from app.core.security import decode_access_token

logger = get_logger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])

connected_clients: Set[WebSocket] = set()
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
        clients = list(connected_clients)

    disconnected: list[WebSocket] = []
    for ws in clients:
        try:
            await ws.send_json(message)
        except Exception:
            disconnected.append(ws)

    if disconnected:
        async with _clients_lock:
            for ws in disconnected:
                connected_clients.discard(ws)


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

    try:
        decode_access_token(token)
    except (JWTError, Exception):
        try:
            await websocket.accept()
            await websocket.close(code=4001)
        except Exception:
            pass
        return

    await websocket.accept()

    async with _clients_lock:
        connected_clients.add(websocket)

    logger.info("ws.client_connected", clients=len(connected_clients))

    try:
        # Send initial metrics snapshot
        try:
            from app.api.endpoints.monitoring import dashboard_metrics as _get_metrics
            # We can't call the endpoint directly (it needs Depends), so build
            # a lightweight version using the same DB queries.
            metrics = await _build_current_metrics()
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
            connected_clients.discard(websocket)
        logger.info("ws.client_disconnected", clients=len(connected_clients))


async def _build_current_metrics() -> Dict[str, Any]:
    """Build a metrics dict for the initial WebSocket payload."""
    from datetime import datetime, timedelta, timezone

    from app.core.database import alerts_col, analyses_col, sources_col
    from app.core.database import collected_items_col
    import app.services.ml_service as _ml

    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(hours=24)

    try:
        total_analyses = await analyses_col().count_documents({})
        total_alerts = await alerts_col().count_documents({})
        critical_alerts = await alerts_col().count_documents(
            {"threat_level": "critical", "is_resolved": False}
        )
        high_alerts = await alerts_col().count_documents(
            {"threat_level": "high", "is_resolved": False}
        )
        medium_alerts = await alerts_col().count_documents(
            {"threat_level": "medium", "is_resolved": False}
        )
        low_alerts = await alerts_col().count_documents(
            {"threat_level": "low", "is_resolved": False}
        )
        active_sources = await sources_col().count_documents({"is_active": True})
        analyses_today = await analyses_col().count_documents(
            {"created_at": {"$gte": yesterday}}
        )

        avg_score = 0.0
        pipeline_avg = [
            {"$match": {"status": "completed"}},
            {"$group": {"_id": None, "avg": {"$avg": "$threat_score"}}},
        ]
        async for row in analyses_col().aggregate(pipeline_avg):
            avg_score = float(row.get("avg") or 0.0)

        # source_breakdown
        source_breakdown: Dict[str, int] = {}
        try:
            async for row in collected_items_col().aggregate(
                [{"$group": {"_id": "$source_type", "count": {"$sum": 1}}}]
            ):
                source_breakdown[row.get("_id") or "unknown"] = row.get("count", 0)
            upload_count = await analyses_col().count_documents({"analysis_type": "document"})
            if upload_count:
                source_breakdown["upload"] = source_breakdown.get("upload", 0) + upload_count
            text_count = await analyses_col().count_documents({"analysis_type": "text"})
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
            "threat_trend_24h": 0.0,
            "analyses_today": analyses_today,
            "source_breakdown": source_breakdown,
            "active_model": _ml.ACTIVE_MODEL_NAME or "not loaded",
            "model_f1": _ml.ACTIVE_MODEL_F1,
        }
    except Exception as exc:
        logger.warning("ws.metrics_build_failed", error=str(exc))
        return {}
