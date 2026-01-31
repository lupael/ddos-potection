from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from routers import (
    traffic_router,
    rules_router,
    mitigation_router,
    isp_router,
    alerts_router,
    reports_router,
    auth_router
)
from database import engine, Base
from config import settings

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
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(traffic_router.router, prefix="/api/v1/traffic", tags=["Traffic"])
app.include_router(rules_router.router, prefix="/api/v1/rules", tags=["Rules"])
app.include_router(mitigation_router.router, prefix="/api/v1/mitigation", tags=["Mitigation"])
app.include_router(isp_router.router, prefix="/api/v1/isp", tags=["ISP Management"])
app.include_router(alerts_router.router, prefix="/api/v1/alerts", tags=["Alerts"])
app.include_router(reports_router.router, prefix="/api/v1/reports", tags=["Reports"])

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

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
