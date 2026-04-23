from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import redis as redis_lib

from routers import (
    traffic_router,
    rules_router,
    mitigation_router,
    isp_router,
    alerts_router,
    reports_router,
    auth_router,
    attack_map_router,
    hostgroup_router,
    capture_router,
    traffic_collection_router,
    subscription_router,
    payment_router,
)
from routers.sla_router import router as sla_router
from routers.webhook_router import router as webhook_router
from routers.threat_intel_router import router as threat_intel_router
from routers.totp_router import router as totp_router
from routers.flow_source_router import router as flow_source_router
from routers.customer_router import router as customer_router
from routers.gdpr_router import router as gdpr_router
from routers.audit_router import router as audit_router
from routers.campaign_router import router as campaign_router
from routers.forecast_router import router as forecast_router
from routers.rpki_router import router as rpki_router
from routers.lstm_router import router as lstm_router
from routers.cloud_flow_router import router as cloud_flow_router
from routers.router_inventory_router import router as router_inventory_router
from routers.scrubbing_router import router as scrubbing_router
from routers.sla_compliance_router import router as sla_compliance_router
from routers.ticketing_router import router as ticketing_router
from routers.branding_router import router as branding_router
from routers.signature_router import router as signature_router
from routers.risk_router import router as risk_router
from routers.bi_router import router as bi_router
from routers.graphql_router import router as graphql_status_router, graphql_app
from middleware.audit_middleware import AuditMiddleware
from database import engine, Base, get_db
from config import settings
from services.metrics_collector import get_metrics_content, CONTENT_TYPE_LATEST

# Create database tables
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting DDoS Protection Platform API...")
    yield
    # Shutdown
    print("Shutting down...")

app = FastAPI(
    title="DDoS Protection Platform API",
    description="Multi-tenant DDoS protection platform for ISPs",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Audit logging middleware — logs all POST/PUT/PATCH/DELETE requests
app.add_middleware(AuditMiddleware)

# Include routers
app.include_router(auth_router.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(traffic_router.router, prefix="/api/v1/traffic", tags=["Traffic"])
app.include_router(rules_router.router, prefix="/api/v1/rules", tags=["Rules"])
app.include_router(mitigation_router.router, prefix="/api/v1/mitigation", tags=["Mitigation"])
app.include_router(isp_router.router, prefix="/api/v1/isp", tags=["ISP Management"])
app.include_router(alerts_router.router, prefix="/api/v1/alerts", tags=["Alerts"])
app.include_router(reports_router.router, prefix="/api/v1/reports", tags=["Reports"])
app.include_router(subscription_router.router, prefix="/api/v1/subscriptions", tags=["Subscriptions"])
app.include_router(payment_router.router, prefix="/api/v1/payments", tags=["Payments"])
app.include_router(attack_map_router.router, prefix="/api/v1/attack-map", tags=["Attack Map"])
app.include_router(hostgroup_router.router)  # Already has prefix in router definition
app.include_router(capture_router.router)  # Already has prefix in router definition
app.include_router(traffic_collection_router.router, prefix="/api/v1/traffic-collection", tags=["Traffic Collection"])
app.include_router(sla_router)
app.include_router(webhook_router)
app.include_router(threat_intel_router)
app.include_router(totp_router, prefix="/api/v1/auth")
app.include_router(flow_source_router)
app.include_router(customer_router)
app.include_router(gdpr_router)
app.include_router(audit_router)
app.include_router(campaign_router)
app.include_router(forecast_router)
app.include_router(rpki_router)
app.include_router(lstm_router)
app.include_router(cloud_flow_router)
app.include_router(router_inventory_router)
app.include_router(scrubbing_router)
app.include_router(sla_compliance_router)
app.include_router(ticketing_router)
app.include_router(branding_router)
app.include_router(signature_router)
app.include_router(risk_router)
app.include_router(bi_router)
app.include_router(graphql_status_router, prefix="/api/v1/graphql", tags=["GraphQL"])
if graphql_app is not None:
    app.include_router(graphql_app, prefix="/api/v1/graphql")

@app.get("/")
async def root():
    return {
        "message": "DDoS Protection Platform API",
        "version": "1.0.0",
        "status": "operational"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/health/live", tags=["Health"])
async def liveness():
    """Kubernetes liveness probe — always 200 if the process is alive."""
    return {"status": "alive"}

@app.get("/health/ready", tags=["Health"])
async def readiness():
    """
    Kubernetes readiness probe.
    Returns 200 only when both PostgreSQL and Redis are reachable.
    """
    errors: list[str] = []

    # Check PostgreSQL
    try:
        from sqlalchemy import text
        db_gen = get_db()
        db = next(db_gen)
        try:
            db.execute(text("SELECT 1"))
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass
    except Exception as exc:
        errors.append(f"postgres: {exc}")

    # Check Redis
    try:
        r = redis_lib.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            socket_connect_timeout=2,
        )
        r.ping()
    except Exception as exc:
        errors.append(f"redis: {exc}")

    if errors:
        from fastapi import Response as FastAPIResponse
        import json
        return FastAPIResponse(
            content=json.dumps({"status": "not ready", "errors": errors}),
            status_code=503,
            media_type="application/json",
        )

    return {"status": "ready"}

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    metrics_data = get_metrics_content()
    return Response(content=metrics_data, headers={"Content-Type": CONTENT_TYPE_LATEST})

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
