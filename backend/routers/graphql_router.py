"""GraphQL router for the DDoS Protection Platform.

Provides a minimal GraphQL API for alerts and traffic logs using strawberry.
Falls back to a stub endpoint if strawberry is not installed.
"""
from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db

try:
    import strawberry
    from strawberry.fastapi import GraphQLRouter as StrawberryGraphQLRouter
    _STRAWBERRY_AVAILABLE = True
except ImportError:
    _STRAWBERRY_AVAILABLE = False


def _build_graphql_router() -> StrawberryGraphQLRouter:  # type: ignore[return]
    """Build and return the strawberry GraphQL router."""

    @strawberry.type
    class AlertType:
        id: int
        isp_id: int
        alert_type: str
        severity: str
        source_ip: Optional[str]
        dest_ip: Optional[str]
        created_at: str

    @strawberry.type
    class TrafficLogType:
        id: int
        isp_id: int
        timestamp: str
        source_ip: str
        dest_ip: str
        protocol: str
        packets: int
        bytes: int

    @strawberry.type
    class Query:
        @strawberry.field
        def alerts(
            self,
            info: strawberry.types.Info,
            isp_id: int,
            limit: int = 10,
        ) -> List[AlertType]:
            """Return alerts for a given ISP, filtered by isp_id."""
            db: Session = info.context["db"]
            from models import Alert  # local import to avoid circular deps
            rows = (
                db.query(Alert)
                .filter(Alert.isp_id == isp_id)
                .order_by(Alert.created_at.desc())
                .limit(limit)
                .all()
            )
            return [
                AlertType(
                    id=r.id,
                    isp_id=r.isp_id,
                    alert_type=r.alert_type or "",
                    severity=r.severity or "",
                    source_ip=r.source_ip,
                    dest_ip=r.target_ip,
                    created_at=str(r.created_at),
                )
                for r in rows
            ]

        @strawberry.field
        def traffic_logs(
            self,
            info: strawberry.types.Info,
            isp_id: int,
            limit: int = 10,
        ) -> List[TrafficLogType]:
            """Return traffic log entries for a given ISP, filtered by isp_id."""
            db: Session = info.context["db"]
            from models import TrafficLog  # local import to avoid circular deps
            rows = (
                db.query(TrafficLog)
                .filter(TrafficLog.isp_id == isp_id)
                .order_by(TrafficLog.timestamp.desc())
                .limit(limit)
                .all()
            )
            return [
                TrafficLogType(
                    id=r.id,
                    isp_id=r.isp_id,
                    timestamp=str(r.timestamp),
                    source_ip=r.source_ip or "",
                    dest_ip=r.dest_ip or "",
                    protocol=r.protocol or "",
                    packets=r.packets or 0,
                    bytes=r.bytes or 0,
                )
                for r in rows
            ]

    async def get_context(db: Session = Depends(get_db)):  # type: ignore[override]
        return {"db": db}

    schema = strawberry.Schema(query=Query)
    return StrawberryGraphQLRouter(schema, context_getter=get_context)


# Build the router exposed to main.py
if _STRAWBERRY_AVAILABLE:
    graphql_app = _build_graphql_router()
    router = APIRouter()

    @router.get("/status")
    async def graphql_status() -> dict:
        """GraphQL availability status."""
        return {"status": "available", "endpoint": "/api/v1/graphql"}

else:
    router = APIRouter()

    @router.get("/status")
    async def graphql_status() -> dict:
        """GraphQL stub — strawberry not installed."""
        return {
            "error": "GraphQL not available. Install strawberry-graphql"
        }

    graphql_app = None  # type: ignore[assignment]
