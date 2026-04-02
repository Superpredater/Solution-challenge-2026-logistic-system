"""Main FastAPI API Gateway — includes all routers, middleware, and GraphQL."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.auth_service.router import router as auth_router
from services.auth_service.rls import TenantRLSMiddleware

from services.api.middleware.rate_limiter import RateLimiterMiddleware
from services.api.middleware.versioning import VersioningMiddleware

from services.api.routers.shipments import router as shipments_router
from services.api.routers.alerts import router as alerts_router
from services.api.routers.disruptions import router as disruptions_router
from services.api.routers.regions import router as regions_router
from services.api.routers.carriers import router as carriers_router
from services.api.routers.ai import router as ai_router
from services.api.routers.digital_twin import router as digital_twin_router
from services.api.routers.reports import router as reports_router
from services.api.routers.carbon import router as carbon_router
from services.api.routers.edge import router as edge_router
from services.api.routers.decisions import router as decisions_router
from services.api.routers.analytics import router as analytics_router

from services.api.graphql.main import graphql_router

app = FastAPI(
    title="Smart Supply Chain API",
    version="1.0.0",
    description="AI-powered logistics intelligence platform",
)

# ---------------------------------------------------------------------------
# Middleware (order matters: outermost first)
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(VersioningMiddleware)
app.add_middleware(RateLimiterMiddleware)
app.add_middleware(TenantRLSMiddleware)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(auth_router)
app.include_router(shipments_router)
app.include_router(alerts_router)
app.include_router(disruptions_router)
app.include_router(regions_router)
app.include_router(carriers_router)
app.include_router(ai_router)
app.include_router(digital_twin_router)
app.include_router(reports_router)
app.include_router(carbon_router)
app.include_router(edge_router)
app.include_router(decisions_router)
app.include_router(analytics_router)

# ---------------------------------------------------------------------------
# GraphQL
# ---------------------------------------------------------------------------
app.include_router(graphql_router, prefix="/graphql")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "api-gateway"}


@app.get("/api/v1/status")
async def api_status() -> dict:
    return {"status": "running", "version": "1.0.0"}
