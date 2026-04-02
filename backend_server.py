"""
Smart Supply Chain Optimization — Standalone Backend Server
Runs on Python + SQLite. No Docker, Kafka, or PostgreSQL needed.
Usage: python backend_server.py
"""
from __future__ import annotations
import asyncio, hashlib, json, math, os, random, time, uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
import sqlalchemy as sa
import httpx

# ─── Config ───────────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyCU08HgGEWLdyD4k88SAxpC3O9-EkAPBEk")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
DB_URL = "sqlite+aiosqlite:///./supply_chain.db"
SECRET = "demo-jwt-secret-2024"

engine = create_async_engine(DB_URL, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

# ─── ORM Base ─────────────────────────────────────────────────────────────────
class Base(DeclarativeBase): pass

class ShipmentRow(Base):
    __tablename__ = "shipments"
    shipment_id    = sa.Column(sa.String, primary_key=True)
    tenant_id      = sa.Column(sa.String, default="demo-tenant")
    origin_name    = sa.Column(sa.String)
    destination_name = sa.Column(sa.String)
    carrier_name   = sa.Column(sa.String)
    status         = sa.Column(sa.String, default="In_Transit")
    risk_score     = sa.Column(sa.Float, default=0.0)
    eta            = sa.Column(sa.String)
    demand_priority = sa.Column(sa.String, default="Normal")
    carbon_kg      = sa.Column(sa.Float, default=0.0)
    created_at     = sa.Column(sa.String)
    updated_at     = sa.Column(sa.String)

class AlertRow(Base):
    __tablename__ = "alerts"
    alert_id    = sa.Column(sa.String, primary_key=True)
    tenant_id   = sa.Column(sa.String, default="demo-tenant")
    shipment_id = sa.Column(sa.String, nullable=True)
    severity    = sa.Column(sa.String)
    trigger_type = sa.Column(sa.String)
    message     = sa.Column(sa.String)
    ai_explanation = sa.Column(sa.String, nullable=True)
    created_at  = sa.Column(sa.String)

class CarrierRow(Base):
    __tablename__ = "carriers"
    carrier_id   = sa.Column(sa.String, primary_key=True)
    name         = sa.Column(sa.String)
    on_time_rate_90d = sa.Column(sa.Float)
    on_time_rate_30d = sa.Column(sa.Float)
    incident_count_90d = sa.Column(sa.Integer, default=0)
    capacity_reliability_score = sa.Column(sa.Float)
    risk_score   = sa.Column(sa.Float)
    is_high_risk = sa.Column(sa.Boolean, default=False)
    profile_updated_at = sa.Column(sa.String)

class RiskEventRow(Base):
    __tablename__ = "risk_events"
    event_id     = sa.Column(sa.String, primary_key=True)
    shipment_id  = sa.Column(sa.String)
    risk_score   = sa.Column(sa.Float)
    weather_component = sa.Column(sa.Float)
    operational_component = sa.Column(sa.Float)
    war_state_component = sa.Column(sa.Float)
    geopolitical_component = sa.Column(sa.Float)
    recorded_at  = sa.Column(sa.String)

class UserRow(Base):
    __tablename__ = "users"
    user_id    = sa.Column(sa.String, primary_key=True)
    tenant_id  = sa.Column(sa.String, default="demo-tenant")
    email      = sa.Column(sa.String, unique=True)
    name       = sa.Column(sa.String)
    password_hash = sa.Column(sa.String)
    role       = sa.Column(sa.String, default="Viewer")
    phone      = sa.Column(sa.String, nullable=True)
    company    = sa.Column(sa.String, nullable=True)
    job_title  = sa.Column(sa.String, nullable=True)
    bio        = sa.Column(sa.String, nullable=True)
    location   = sa.Column(sa.String, nullable=True)
    avatar     = sa.Column(sa.Text, nullable=True)   # base64 data URL
    created_at = sa.Column(sa.String)

# ─── Seed Data ────────────────────────────────────────────────────────────────
CARRIERS = [
    ("Maersk Line", 0.94, 0.91, 2, 0.96, 12.0, False),
    ("DHL Express", 0.88, 0.85, 5, 0.90, 28.0, False),
    ("FedEx Freight", 0.79, 0.74, 9, 0.82, 42.0, True),
    ("MSC Shipping", 0.92, 0.89, 3, 0.93, 18.0, False),
    ("UPS Supply Chain", 0.85, 0.83, 6, 0.87, 32.0, False),
    ("COSCO Shipping", 0.76, 0.71, 11, 0.78, 52.0, True),
    ("Evergreen Marine", 0.90, 0.88, 4, 0.91, 22.0, False),
    ("DB Schenker", 0.87, 0.84, 5, 0.88, 30.0, False),
]

ROUTES = [
    ("Shanghai", "Rotterdam"),
    ("Los Angeles", "New York"),
    ("Dubai", "London"),
    ("Singapore", "Hamburg"),
    ("Mumbai", "Antwerp"),
    ("Tokyo", "Seattle"),
    ("Hong Kong", "Frankfurt"),
    ("Busan", "Vancouver"),
    ("Guangzhou", "Barcelona"),
    ("Shenzhen", "Felixstowe"),
    ("Jakarta", "Sydney"),
    ("Colombo", "Jeddah"),
]

DISRUPTION_MESSAGES = [
    ("Port congestion at Rotterdam causing 48h delays", "Warning"),
    ("Typhoon warning in South China Sea — rerouting advised", "Critical"),
    ("Carrier capacity reduction on Trans-Pacific route", "Warning"),
    ("Geopolitical tensions in Red Sea corridor", "Critical"),
    ("Weather delay at Los Angeles port", "Warning"),
    ("Rail strike affecting European inland transport", "Warning"),
    ("Airspace closure over Eastern Europe", "Critical"),
    ("Customs backlog at Singapore — 24h delay expected", "Warning"),
]

DEMO_USERS = [
    ("demo-admin-0001", "admin@demo.com", "Alex Admin", "Admin"),
    ("demo-manager-0002", "manager@demo.com", "Morgan Manager", "Manager"),
    ("demo-analyst-0003", "analyst@demo.com", "Sam Analyst", "Analyst"),
    ("demo-viewer-0004", "viewer@demo.com", "Jordan Viewer", "Viewer"),
]

def _hash(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _future(hours: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()

def _past(hours: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

async def seed_database(session: AsyncSession) -> None:
    # Users
    for uid, email, name, role in DEMO_USERS:
        exists = await session.get(UserRow, uid)
        if not exists:
            session.add(UserRow(
                user_id=uid, email=email, name=name,
                password_hash=_hash("demo1234"), role=role,
                created_at=_now()
            ))

    # Carriers
    carrier_ids = []
    for i, (name, r90, r30, inc, cap, risk, high) in enumerate(CARRIERS):
        cid = f"carrier-{i+1:04d}-0000-0000-000000000001"
        carrier_ids.append(cid)
        exists = await session.get(CarrierRow, cid)
        if not exists:
            session.add(CarrierRow(
                carrier_id=cid, name=name,
                on_time_rate_90d=r90, on_time_rate_30d=r30,
                incident_count_90d=inc, capacity_reliability_score=cap,
                risk_score=risk, is_high_risk=high,
                profile_updated_at=_now()
            ))

    # Shipments + risk events
    statuses = ["In_Transit", "In_Transit", "In_Transit", "Delayed", "Connectivity_Impaired"]
    priorities = ["Normal", "Normal", "Elevated", "High"]
    for i in range(40):
        sid = f"ship-{i+1:04d}-0000-0000-000000000001"
        exists = await session.get(ShipmentRow, sid)
        if not exists:
            origin, dest = ROUTES[i % len(ROUTES)]
            carrier = CARRIERS[i % len(CARRIERS)][0]
            risk = round(random.uniform(5, 95), 1)
            session.add(ShipmentRow(
                shipment_id=sid,
                origin_name=origin, destination_name=dest,
                carrier_name=carrier,
                status=statuses[i % len(statuses)],
                risk_score=risk,
                eta=_future(random.randint(12, 240)),
                demand_priority=priorities[i % len(priorities)],
                carbon_kg=round(random.uniform(200, 3000), 1),
                created_at=_past(random.randint(1, 720)),
                updated_at=_now()
            ))
            # Risk history (last 48h)
            for h in range(48, 0, -4):
                session.add(RiskEventRow(
                    event_id=str(uuid.uuid4()),
                    shipment_id=sid,
                    risk_score=round(max(0, min(100, risk + random.uniform(-15, 15))), 1),
                    weather_component=round(random.uniform(0, 30), 1),
                    operational_component=round(random.uniform(0, 35), 1),
                    war_state_component=round(random.uniform(0, 25), 1),
                    geopolitical_component=round(random.uniform(0, 20), 1),
                    recorded_at=_past(h)
                ))

    # Alerts
    for i in range(20):
        aid = f"alert-{i+1:04d}-0000-0000-000000000001"
        exists = await session.get(AlertRow, aid)
        if not exists:
            msg, sev = DISRUPTION_MESSAGES[i % len(DISRUPTION_MESSAGES)]
            session.add(AlertRow(
                alert_id=aid,
                shipment_id=f"ship-{(i%40)+1:04d}-0000-0000-000000000001",
                severity=sev,
                trigger_type="risk_escalation" if sev == "Critical" else "risk_score_threshold",
                message=msg,
                created_at=_past(random.randint(0, 48))
            ))

    await session.commit()

# ─── Auth helpers ─────────────────────────────────────────────────────────────
from jose import jwt as jose_jwt

def make_token(user_id: str, email: str, role: str, tenant_id: str) -> str:
    payload = {
        "sub": user_id, "email": email, "role": role,
        "tenant_id": tenant_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=24),
    }
    return jose_jwt.encode(payload, SECRET, algorithm="HS256")

def decode_token(token: str) -> dict:
    return jose_jwt.decode(token, SECRET, algorithms=["HS256"])

bearer = HTTPBearer(auto_error=False)

async def get_db():
    async with SessionLocal() as session:
        yield session

async def current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
    db: AsyncSession = Depends(get_db)
) -> dict:
    if not creds:
        raise HTTPException(401, "Not authenticated")
    try:
        payload = decode_token(creds.credentials)
        return payload
    except Exception:
        raise HTTPException(401, "Invalid token")

# ─── App ──────────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with SessionLocal() as session:
        await seed_database(session)
    print("\n✅  Supply Chain Backend running at http://localhost:8000")
    print("   API docs: http://localhost:8000/docs\n")
    yield

app = FastAPI(title="Supply Chain API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

# ─── Auth endpoints ───────────────────────────────────────────────────────────
class LoginReq(BaseModel):
    email: str
    password: str
    totp_code: Optional[str] = None

class RegisterReq(BaseModel):
    name: str
    email: str
    password: str
    company: str
    role: Optional[str] = "Viewer"

@app.post("/api/v1/auth/login")
async def login(body: LoginReq, db: AsyncSession = Depends(get_db)):
    result = await db.execute(sa.select(UserRow).where(UserRow.email == body.email))
    user = result.scalar_one_or_none()
    if not user or user.password_hash != _hash(body.password):
        raise HTTPException(401, "Invalid credentials")
    token = make_token(user.user_id, user.email, user.role, user.tenant_id)
    return {
        "access_token": token, "token_type": "bearer",
        "user": {
            "stakeholder_id": user.user_id, "tenant_id": user.tenant_id,
            "email": user.email, "name": user.name, "role": user.role,
            "notification_channels": ["email"], "created_at": user.created_at,
        }
    }

@app.post("/api/v1/auth/register")
async def register(body: RegisterReq, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(sa.select(UserRow).where(UserRow.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Email already registered")
    uid = str(uuid.uuid4())
    user = UserRow(
        user_id=uid, email=body.email, name=body.name,
        password_hash=_hash(body.password),
        role=body.role or "Viewer",
        tenant_id="demo-tenant",
        created_at=_now()
    )
    db.add(user)
    await db.commit()
    token = make_token(uid, body.email, user.role, "demo-tenant")
    return {
        "access_token": token, "token_type": "bearer",
        "user": {
            "stakeholder_id": uid, "tenant_id": "demo-tenant",
            "email": body.email, "name": body.name, "role": user.role,
            "notification_channels": ["email"], "created_at": user.created_at,
        }
    }

@app.post("/api/v1/auth/logout")
async def logout(): return {"ok": True}

@app.get("/api/v1/auth/me")
async def me(user=Depends(current_user)): return user

# ─── Shipments ────────────────────────────────────────────────────────────────
def _ship_dict(s: ShipmentRow) -> dict:
    return {
        "shipment_id": s.shipment_id, "tenant_id": s.tenant_id,
        "origin": {"node_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, s.origin_name)), "name": s.origin_name},
        "destination": {"node_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, s.destination_name)), "name": s.destination_name},
        "active_route_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, s.shipment_id + "_route")),
        "carrier_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, s.carrier_name or "unknown")),
        "carrier_name": s.carrier_name,
        "status": s.status, "risk_score": s.risk_score,
        "risk_score_updated_at": s.updated_at,
        "eta": s.eta,
        "eta_confidence_interval": [
            (datetime.fromisoformat(s.eta.replace("Z","")) - timedelta(hours=2)).isoformat() if s.eta else _future(2),
            (datetime.fromisoformat(s.eta.replace("Z","")) + timedelta(hours=2)).isoformat() if s.eta else _future(6),
        ],
        "demand_priority": s.demand_priority, "carbon_kg": s.carbon_kg,
        "created_at": s.created_at, "updated_at": s.updated_at,
    }

@app.get("/api/v1/shipments")
async def list_shipments(
    page: int = 1, page_size: int = 50,
    status: Optional[str] = None,
    risk_min: Optional[float] = None,
    risk_max: Optional[float] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _user=Depends(current_user)
):
    q = sa.select(ShipmentRow)
    if status: q = q.where(ShipmentRow.status == status)
    if risk_min is not None: q = q.where(ShipmentRow.risk_score >= risk_min)
    if risk_max is not None: q = q.where(ShipmentRow.risk_score <= risk_max)
    if search:
        q = q.where(sa.or_(
            ShipmentRow.origin_name.ilike(f"%{search}%"),
            ShipmentRow.destination_name.ilike(f"%{search}%"),
            ShipmentRow.carrier_name.ilike(f"%{search}%"),
        ))
    count_q = sa.select(sa.func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar_one()
    rows = (await db.execute(q.offset((page-1)*page_size).limit(page_size))).scalars().all()
    return {"items": [_ship_dict(s) for s in rows], "total": total, "page": page, "page_size": page_size}

@app.get("/api/v1/shipments/{sid}")
async def get_shipment(sid: str, db: AsyncSession = Depends(get_db), _user=Depends(current_user)):
    s = await db.get(ShipmentRow, sid)
    if not s: raise HTTPException(404, "Shipment not found")
    return _ship_dict(s)

@app.get("/api/v1/shipments/{sid}/risk-history")
async def risk_history(sid: str, limit: int = 100, db: AsyncSession = Depends(get_db), _user=Depends(current_user)):
    rows = (await db.execute(
        sa.select(RiskEventRow).where(RiskEventRow.shipment_id == sid)
        .order_by(RiskEventRow.recorded_at.asc()).limit(limit)
    )).scalars().all()
    return [{"event_id": r.event_id, "shipment_id": r.shipment_id,
             "risk_score": r.risk_score, "weather_component": r.weather_component,
             "operational_component": r.operational_component,
             "war_state_component": r.war_state_component,
             "geopolitical_component": r.geopolitical_component,
             "recorded_at": r.recorded_at} for r in rows]

@app.get("/api/v1/shipments/{sid}/recommendations")
async def recommendations(sid: str, _user=Depends(current_user)):
    s_num = int(sid.split("-")[1]) if "-" in sid else 1
    if s_num % 3 != 0: return []
    return [{
        "recommendation_id": str(uuid.uuid4()),
        "shipment_id": sid, "tenant_id": "demo-tenant",
        "triggering_risk_score": 75.0,
        "disruption_id": str(uuid.uuid4()),
        "candidate_route": {
            "route_id": str(uuid.uuid4()), "tenant_id": "demo-tenant",
            "shipment_id": sid, "legs": [
                {"leg_id": str(uuid.uuid4()), "sequence": 1,
                 "origin_node_id": str(uuid.uuid4()), "origin_name": "Singapore",
                 "destination_node_id": str(uuid.uuid4()), "destination_name": "Hamburg",
                 "transport_mode": "sea", "carrier_id": str(uuid.uuid4()),
                 "estimated_duration_hours": 336, "estimated_cost_usd": 4200, "carbon_kg": 890}
            ],
            "total_distance_km": 15800, "total_estimated_duration_hours": 336,
            "total_estimated_cost_usd": 4200, "total_carbon_kg": 890,
            "is_active": False, "created_at": _now()
        },
        "new_eta": _future(340), "cost_delta_usd": -320.0,
        "carbon_delta_kg": -45.0, "rank_score": 0.82,
        "status": "pending", "created_at": _now()
    }]

@app.post("/api/v1/shipments/{sid}/recommendations/{rid}/accept")
async def accept_rec(sid: str, rid: str, _user=Depends(current_user)):
    return {"shipment_id": sid, "recommendation_id": rid, "status": "accepted", "new_eta": _future(340)}

@app.post("/api/v1/shipments/{sid}/recommendations/{rid}/reject")
async def reject_rec(sid: str, rid: str, _user=Depends(current_user)):
    return {"shipment_id": sid, "recommendation_id": rid, "status": "rejected"}

@app.get("/api/v1/shipments/{sid}/ai-explanation")
async def ai_explanation(sid: str, db: AsyncSession = Depends(get_db), _user=Depends(current_user)):
    s = await db.get(ShipmentRow, sid)
    risk = s.risk_score if s else 50.0
    explanation = f"Risk score of {risk:.1f} is driven primarily by operational delays on the {s.origin_name if s else 'origin'} corridor. Weather conditions are moderate. Carrier performance is within acceptable bounds. Recommend monitoring for the next 6 hours."
    return {"shipment_id": sid, "explanation": explanation, "fallback_used": True, "generated_at": _now()}

@app.get("/api/v1/shipments/{sid}/carbon")
async def carbon(sid: str, db: AsyncSession = Depends(get_db), _user=Depends(current_user)):
    s = await db.get(ShipmentRow, sid)
    return {"shipment_id": sid, "carbon_kg": s.carbon_kg if s else 0}

# ─── Alerts ───────────────────────────────────────────────────────────────────
def _alert_dict(a: AlertRow) -> dict:
    return {
        "alert_id": a.alert_id, "tenant_id": a.tenant_id,
        "shipment_id": a.shipment_id, "disruption_id": None,
        "severity": a.severity, "trigger_type": a.trigger_type,
        "message": a.message, "ai_explanation": a.ai_explanation,
        "created_at": a.created_at, "deliveries": []
    }

@app.get("/api/v1/alerts")
async def list_alerts(
    severity: Optional[str] = None, page: int = 1, page_size: int = 25,
    db: AsyncSession = Depends(get_db), _user=Depends(current_user)
):
    q = sa.select(AlertRow)
    if severity: q = q.where(AlertRow.severity == severity)
    q = q.order_by(AlertRow.created_at.desc())
    total = (await db.execute(sa.select(sa.func.count()).select_from(q.subquery()))).scalar_one()
    rows = (await db.execute(q.offset((page-1)*page_size).limit(page_size))).scalars().all()
    return {"items": [_alert_dict(a) for a in rows], "total": total, "page": page, "page_size": page_size}

@app.get("/api/v1/alerts/{aid}")
async def get_alert(aid: str, db: AsyncSession = Depends(get_db), _user=Depends(current_user)):
    a = await db.get(AlertRow, aid)
    if not a: raise HTTPException(404, "Alert not found")
    return _alert_dict(a)

@app.get("/api/v1/alerts/{aid}/deliveries")
async def alert_deliveries(aid: str, _user=Depends(current_user)):
    return [{"delivery_id": str(uuid.uuid4()), "alert_id": aid,
             "stakeholder_id": "demo-admin-0001", "channel": "email",
             "status": "delivered", "delivered_at": _now(), "retry_count": 0}]

# ─── Carriers ─────────────────────────────────────────────────────────────────
def _carrier_dict(c: CarrierRow) -> dict:
    return {
        "carrier_id": c.carrier_id, "name": c.name,
        "on_time_rate_90d": c.on_time_rate_90d, "on_time_rate_30d": c.on_time_rate_30d,
        "incident_count_90d": c.incident_count_90d,
        "capacity_reliability_score": c.capacity_reliability_score,
        "risk_score": c.risk_score, "is_high_risk": c.is_high_risk,
        "profile_updated_at": c.profile_updated_at
    }

@app.get("/api/v1/carriers")
async def list_carriers(page: int = 1, page_size: int = 50,
                        db: AsyncSession = Depends(get_db), _user=Depends(current_user)):
    rows = (await db.execute(sa.select(CarrierRow))).scalars().all()
    return {"items": [_carrier_dict(c) for c in rows], "total": len(rows), "page": 1, "page_size": 50}

@app.get("/api/v1/carriers/{cid}/profile")
async def carrier_profile(cid: str, db: AsyncSession = Depends(get_db), _user=Depends(current_user)):
    c = await db.get(CarrierRow, cid)
    if not c: raise HTTPException(404, "Carrier not found")
    return _carrier_dict(c)

@app.get("/api/v1/carriers/{cid}/risk-history")
async def carrier_risk_history(cid: str, _user=Depends(current_user)):
    return [{"risk_score": round(random.uniform(10, 60), 1),
             "recorded_at": _past(h)} for h in range(720, 0, -24)]

# ─── Regions ──────────────────────────────────────────────────────────────────
REGIONS = [
    ("Red Sea Corridor", "High_Risk", 78.0),
    ("South China Sea", "Caution", 45.0),
    ("Strait of Hormuz", "High_Risk", 82.0),
    ("Black Sea", "Restricted", 95.0),
    ("Mediterranean", "Safe", 15.0),
    ("North Atlantic", "Safe", 8.0),
    ("Gulf of Aden", "High_Risk", 88.0),
    ("Taiwan Strait", "Caution", 55.0),
]

@app.get("/api/v1/regions")
async def list_regions(_user=Depends(current_user)):
    return [{"region_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, n)),
             "name": n, "iso_codes": [], "geopolitical_risk_index": idx,
             "war_state": ws, "risk_index_updated_at": _now(),
             "war_state_updated_at": _now()} for n, ws, idx in REGIONS]

@app.get("/api/v1/regions/{rid}/risk")
async def region_risk(rid: str, _user=Depends(current_user)):
    for name, ws, idx in REGIONS:
        if str(uuid.uuid5(uuid.NAMESPACE_DNS, name)) == rid:
            return {"region_id": rid, "name": name, "geopolitical_risk_index": idx,
                    "war_state": ws, "risk_index_updated_at": _now(), "war_state_updated_at": _now()}
    return {"region_id": rid, "name": "Unknown", "geopolitical_risk_index": 20.0,
            "war_state": "Safe", "risk_index_updated_at": _now(), "war_state_updated_at": _now()}

# ─── Disruptions ──────────────────────────────────────────────────────────────
@app.get("/api/v1/disruptions")
async def list_disruptions(page: int = 1, page_size: int = 25, _user=Depends(current_user)):
    items = [{"disruption_id": str(uuid.uuid4()), "tenant_id": "demo-tenant",
              "disruption_type": t, "severity": s, "description": d,
              "affected_node_ids": [], "source": "Demo",
              "started_at": _past(random.randint(1, 48)), "created_at": _past(random.randint(1, 48))}
             for d, s, t in [
                 ("Port congestion at Rotterdam", "High", "port_closure"),
                 ("Typhoon warning South China Sea", "Critical", "weather"),
                 ("Rail strike Central Europe", "Medium", "carrier_delay"),
                 ("Airspace closure Eastern Europe", "Critical", "conflict"),
             ]]
    return {"items": items, "total": len(items), "page": 1, "page_size": 25}

# ─── Reports & Analytics ──────────────────────────────────────────────────────
@app.get("/api/v1/reports/risk-score-trend")
async def risk_trend(start: str = "", end: str = "", format: str = "json",
                     db: AsyncSession = Depends(get_db), _user=Depends(current_user)):
    data = [{"date": _past(h*24).split("T")[0],
             "avg_risk_score": round(random.uniform(30, 70), 1),
             "max_risk_score": round(random.uniform(60, 95), 1),
             "event_count": random.randint(50, 200)} for h in range(30, 0, -1)]
    return data

@app.get("/api/v1/reports/carrier-performance")
async def carrier_perf(start: str = "", end: str = "", format: str = "json",
                       db: AsyncSession = Depends(get_db), _user=Depends(current_user)):
    rows = (await db.execute(sa.select(CarrierRow))).scalars().all()
    return [{"carrier_name": c.name, "on_time_rate_90d": c.on_time_rate_90d,
             "on_time_rate_30d": c.on_time_rate_30d, "incident_count_90d": c.incident_count_90d,
             "risk_score": c.risk_score} for c in rows]

@app.get("/api/v1/reports/disruption-frequency")
async def disruption_freq(start: str = "", end: str = "", format: str = "json", _user=Depends(current_user)):
    return [{"disruption_type": t, "severity": s, "count": random.randint(1, 15),
             "disruption_count": random.randint(1, 15)}
            for t, s in [("weather", "High"), ("carrier_delay", "Medium"),
                         ("port_closure", "High"), ("conflict", "Critical"),
                         ("geopolitical", "High"), ("infrastructure", "Medium")]]

@app.get("/api/v1/analytics/risk-score-trend")
async def analytics_risk_trend(tenant_id: str = "", start: str = "", end: str = "",
                                bucket_interval: str = "1 hour", format: str = "json",
                                _user=Depends(current_user)):
    return [{"bucket": _past(h*4), "avg_risk_score": round(random.uniform(25, 75), 1),
             "min_risk_score": round(random.uniform(5, 30), 1),
             "max_risk_score": round(random.uniform(70, 95), 1),
             "event_count": random.randint(10, 100)} for h in range(42, 0, -1)]

@app.get("/api/v1/analytics/carrier-performance")
async def analytics_carrier_perf(start: str = "", end: str = "", format: str = "json",
                                  db: AsyncSession = Depends(get_db), _user=Depends(current_user)):
    rows = (await db.execute(sa.select(CarrierRow))).scalars().all()
    return [{"carrier_id": c.carrier_id, "name": c.name,
             "on_time_rate_90d": c.on_time_rate_90d, "on_time_rate_30d": c.on_time_rate_30d,
             "incident_count_90d": c.incident_count_90d, "risk_score": c.risk_score,
             "is_high_risk": c.is_high_risk} for c in rows]

@app.get("/api/v1/analytics/disruption-frequency")
async def analytics_disruption_freq(start: str = "", end: str = "", format: str = "json", _user=Depends(current_user)):
    return [{"disruption_type": t, "severity": s, "disruption_count": random.randint(1, 15),
             "first_occurrence": _past(48), "last_occurrence": _past(2)}
            for t, s in [("weather", "High"), ("carrier_delay", "Medium"),
                         ("port_closure", "High"), ("conflict", "Critical")]]

@app.get("/api/v1/carbon/summary")
async def carbon_summary(db: AsyncSession = Depends(get_db), _user=Depends(current_user)):
    result = await db.execute(sa.select(sa.func.sum(ShipmentRow.carbon_kg), sa.func.count(ShipmentRow.shipment_id)))
    total, count = result.one()
    return {"tenant_id": "demo-tenant", "total_carbon_kg": round(total or 0, 1),
            "shipment_count": count or 0,
            "by_mode": [{"mode": m, "carbon_kg": round(random.uniform(500, 5000), 1)}
                        for m in ["sea", "air", "rail", "road"]]}

# ─── Digital Twin ─────────────────────────────────────────────────────────────
scenarios_store: dict[str, dict] = {}

class ScenarioReq(BaseModel):
    scenario_name: str
    parameters: dict = {}

@app.post("/api/v1/digital-twin/scenarios")
async def create_scenario(body: ScenarioReq, _user=Depends(current_user)):
    sid = str(uuid.uuid4())
    scenarios_store[sid] = {"scenario_id": sid, "scenario_name": body.scenario_name,
                             "status": "running", "parameters": body.parameters,
                             "created_at": _now(), "result": None}
    asyncio.create_task(_run_scenario(sid))
    return {"scenario_id": sid, "status": "running", "estimated_completion_seconds": 5}

async def _run_scenario(sid: str):
    await asyncio.sleep(5)
    scenarios_store[sid]["status"] = "completed"
    scenarios_store[sid]["result"] = {
        "affected_shipment_count": random.randint(5, 25),
        "average_eta_deviation_hours": round(random.uniform(4, 48), 1),
        "mitigation_recommendations": [
            "Reroute affected shipments via Cape of Good Hope",
            "Pre-position inventory at alternative distribution centers",
            "Activate backup carrier agreements for impacted lanes",
        ]
    }

@app.get("/api/v1/digital-twin/scenarios")
async def list_scenarios(_user=Depends(current_user)):
    return list(scenarios_store.values())

@app.get("/api/v1/digital-twin/scenarios/{sid}")
async def get_scenario(sid: str, _user=Depends(current_user)):
    s = scenarios_store.get(sid)
    if not s: raise HTTPException(404, "Scenario not found")
    return s

@app.get("/api/v1/digital-twin/scenarios/{sid}/report")
async def scenario_report(sid: str, _user=Depends(current_user)):
    s = scenarios_store.get(sid)
    if not s or s["status"] != "completed": raise HTTPException(404, "Report not ready")
    return {**s, "completed_at": _now(), "duration_seconds": 5.2}

# ─── Decision Audit ───────────────────────────────────────────────────────────
@app.get("/api/v1/decisions/audit")
async def decision_audit(lookback_days: int = 30, page: int = 1, page_size: int = 25,
                         _user=Depends(current_user)):
    items = [{"entry_id": str(uuid.uuid4()), "tenant_id": "demo-tenant",
              "shipment_id": f"ship-{i+1:04d}-0000-0000-000000000001",
              "decision_type": "autonomous_reroute" if i % 3 != 0 else "manual_override",
              "triggering_risk_score": round(random.uniform(70, 95), 1),
              "actor": "system" if i % 3 != 0 else "demo-manager-0002",
              "actor_role": None if i % 3 != 0 else "Manager",
              "previous_route_id": str(uuid.uuid4()), "new_route_id": str(uuid.uuid4()),
              "timestamp": _past(random.randint(0, lookback_days*24))}
             for i in range(min(page_size, 15))]
    return {"items": items, "total": 15, "page": page, "page_size": page_size}

# ─── AI Chat ──────────────────────────────────────────────────────────────────
class ChatReq(BaseModel):
    session_id: str
    message: str
    context: dict = {}

@app.post("/api/v1/ai/chat")
async def ai_chat(body: ChatReq, _user=Depends(current_user)):
    start = time.time()
    fallback = False
    response = ""
    if GEMINI_API_KEY:
        try:
            prompt = f"""You are an AI assistant for a Smart Supply Chain Optimization platform.
Help logistics managers understand shipment risks, disruptions, and routing decisions.
Be concise and professional. Use data-driven insights.

User question: {body.message}"""
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.post(
                    f"{GEMINI_URL}?key={GEMINI_API_KEY}",
                    json={"contents": [{"parts": [{"text": prompt}]}],
                          "generationConfig": {"maxOutputTokens": 512, "temperature": 0.7}}
                )
                if res.status_code == 200:
                    data = res.json()
                    response = data["candidates"][0]["content"]["parts"][0]["text"]
                else:
                    raise Exception(f"Gemini error {res.status_code}")
        except Exception as e:
            fallback = True
            response = f"I'm currently operating in fallback mode. Based on current data: your supply chain shows elevated risk in the Red Sea corridor. 3 shipments have risk scores above 70. Recommend reviewing reroute recommendations for affected shipments."
    else:
        fallback = True
        response = "AI service not configured. Please set GEMINI_API_KEY."
    return {"response": response, "session_id": body.session_id,
            "latency_ms": round((time.time() - start) * 1000), "fallback_used": fallback}

@app.post("/api/v1/ai/reports/narrative")
async def narrative_report(body: dict, _user=Depends(current_user)):
    return {"report": "Supply chain performance is stable with moderate disruption activity. Key risks remain in the Red Sea corridor and South China Sea. Carrier on-time rates average 87% across the fleet. Recommend proactive rerouting for 3 high-risk shipments.", "generated_at": _now()}

# ─── Settings ─────────────────────────────────────────────────────────────────
@app.get("/api/v1/settings/tenant")
async def tenant_settings(_user=Depends(current_user)):
    return {"tenant_id": "demo-tenant", "name": "Demo Organization",
            "mfa_enabled": False, "eco_routing_enabled": True,
            "autonomous_decision_enabled": False,
            "risk_score_weights": {"w_weather": 0.25, "w_operational": 0.30, "w_war": 0.25, "w_geopolitical": 0.20},
            "api_rate_limit_per_minute": 1000, "quiet_period_start": None, "quiet_period_end": None,
            "custom_risk_thresholds": []}

@app.patch("/api/v1/settings/tenant")
async def update_tenant_settings(body: dict, _user=Depends(current_user)):
    return {"tenant_id": "demo-tenant", **body}

@app.get("/api/v1/settings/api-keys")
async def api_keys(_user=Depends(current_user)):
    return [{"key_id": "key-001", "name": "Production Integration",
             "key_prefix": "sc_live_xxxx", "created_at": _past(720),
             "rate_limit_per_minute": 1000}]

@app.post("/api/v1/settings/api-keys")
async def create_api_key(body: dict, _user=Depends(current_user)):
    return {"key_id": str(uuid.uuid4()), "key": f"sc_live_{uuid.uuid4().hex[:32]}"}

@app.delete("/api/v1/settings/api-keys/{kid}")
async def delete_api_key(kid: str, _user=Depends(current_user)):
    return {"deleted": True}

# ─── Edge sync ────────────────────────────────────────────────────────────────
@app.post("/api/v1/edge/sync")
async def edge_sync(body: dict, _user=Depends(current_user)):
    events = body.get("events", [])
    return {"received": len(events), "published": len(events)}

# ─── Health ───────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "service": "supply-chain-backend", "gemini": bool(GEMINI_API_KEY)}

@app.get("/")
async def root():
    return {"message": "Supply Chain API", "docs": "/docs", "health": "/health"}

# ─── Run ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)

# ─── Profile endpoints ────────────────────────────────────────────────────────

class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    job_title: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    avatar: Optional[str] = None  # base64 data URL

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

@app.get("/api/v1/profile")
async def get_profile(db: AsyncSession = Depends(get_db), user=Depends(current_user)):
    u = await db.get(UserRow, user["sub"])
    if not u:
        raise HTTPException(404, "User not found")
    return {
        "stakeholder_id": u.user_id, "tenant_id": u.tenant_id,
        "email": u.email, "name": u.name, "role": u.role,
        "phone": getattr(u, "phone", None),
        "company": getattr(u, "company", None),
        "job_title": getattr(u, "job_title", None),
        "bio": getattr(u, "bio", None),
        "location": getattr(u, "location", None),
        "avatar": getattr(u, "avatar", None),
        "notification_channels": ["email"],
        "created_at": u.created_at,
    }

@app.patch("/api/v1/profile")
async def update_profile(body: ProfileUpdate, db: AsyncSession = Depends(get_db), user=Depends(current_user)):
    u = await db.get(UserRow, user["sub"])
    if not u:
        raise HTTPException(404, "User not found")
    for field, value in body.model_dump(exclude_none=True).items():
        if hasattr(u, field):
            setattr(u, field, value)
    await db.commit()
    return {
        "stakeholder_id": u.user_id, "tenant_id": u.tenant_id,
        "email": u.email, "name": u.name, "role": u.role,
        "phone": getattr(u, "phone", None),
        "company": getattr(u, "company", None),
        "job_title": getattr(u, "job_title", None),
        "bio": getattr(u, "bio", None),
        "location": getattr(u, "location", None),
        "avatar": getattr(u, "avatar", None),
        "notification_channels": ["email"],
        "created_at": u.created_at,
    }

@app.post("/api/v1/profile/change-password")
async def change_password(body: PasswordChange, db: AsyncSession = Depends(get_db), user=Depends(current_user)):
    u = await db.get(UserRow, user["sub"])
    if not u or u.password_hash != _hash(body.current_password):
        raise HTTPException(400, "Current password is incorrect")
    u.password_hash = _hash(body.new_password)
    await db.commit()
    return {"message": "Password changed successfully"}

# ─── Shipment Request (Approval Workflow) ─────────────────────────────────────

class ShipmentRequestRow(Base):
    __tablename__ = "shipment_requests"
    request_id     = sa.Column(sa.String, primary_key=True)
    tenant_id      = sa.Column(sa.String, default="demo-tenant")
    submitted_by   = sa.Column(sa.String)   # user_id
    submitter_name = sa.Column(sa.String)
    submitter_role = sa.Column(sa.String)
    origin         = sa.Column(sa.String)
    destination    = sa.Column(sa.String)
    carrier_name   = sa.Column(sa.String)
    cargo_type     = sa.Column(sa.String)
    weight_kg      = sa.Column(sa.Float, default=0.0)
    priority       = sa.Column(sa.String, default="Normal")
    requested_eta  = sa.Column(sa.String)
    notes          = sa.Column(sa.String, nullable=True)
    status         = sa.Column(sa.String, default="pending")  # pending/approved/rejected
    reviewed_by    = sa.Column(sa.String, nullable=True)
    reviewer_name  = sa.Column(sa.String, nullable=True)
    review_note    = sa.Column(sa.String, nullable=True)
    reviewed_at    = sa.Column(sa.String, nullable=True)
    shipment_id    = sa.Column(sa.String, nullable=True)  # set when approved
    created_at     = sa.Column(sa.String)

class ShipmentRequestCreate(BaseModel):
    origin: str
    destination: str
    carrier_name: str
    cargo_type: str
    weight_kg: float = 0.0
    priority: str = "Normal"
    requested_eta: str
    notes: Optional[str] = None

class ReviewAction(BaseModel):
    action: str   # "approve" or "reject"
    review_note: Optional[str] = None

def _req_dict(r: ShipmentRequestRow) -> dict:
    return {
        "request_id": r.request_id, "tenant_id": r.tenant_id,
        "submitted_by": r.submitted_by, "submitter_name": r.submitter_name,
        "submitter_role": r.submitter_role,
        "origin": r.origin, "destination": r.destination,
        "carrier_name": r.carrier_name, "cargo_type": r.cargo_type,
        "weight_kg": r.weight_kg, "priority": r.priority,
        "requested_eta": r.requested_eta, "notes": r.notes,
        "status": r.status, "reviewed_by": r.reviewed_by,
        "reviewer_name": r.reviewer_name, "review_note": r.review_note,
        "reviewed_at": r.reviewed_at, "shipment_id": r.shipment_id,
        "created_at": r.created_at,
    }

@app.post("/api/v1/shipment-requests", status_code=201)
async def create_shipment_request(
    body: ShipmentRequestCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(current_user)
):
    """Any authenticated user can submit a shipment request."""
    u = await db.get(UserRow, user["sub"])
    req = ShipmentRequestRow(
        request_id=str(uuid.uuid4()),
        submitted_by=user["sub"],
        submitter_name=u.name if u else user.get("email", "Unknown"),
        submitter_role=user.get("role", "Viewer"),
        origin=body.origin, destination=body.destination,
        carrier_name=body.carrier_name, cargo_type=body.cargo_type,
        weight_kg=body.weight_kg, priority=body.priority,
        requested_eta=body.requested_eta, notes=body.notes,
        status="pending", created_at=_now()
    )
    db.add(req)
    await db.commit()
    return _req_dict(req)

@app.get("/api/v1/shipment-requests")
async def list_shipment_requests(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user=Depends(current_user)
):
    """Managers/Admins see all requests; others see only their own."""
    role = user.get("role", "Viewer")
    q = sa.select(ShipmentRequestRow).order_by(ShipmentRequestRow.created_at.desc())
    if role not in ("Manager", "Admin"):
        q = q.where(ShipmentRequestRow.submitted_by == user["sub"])
    if status:
        q = q.where(ShipmentRequestRow.status == status)
    rows = (await db.execute(q)).scalars().all()
    return [_req_dict(r) for r in rows]

@app.patch("/api/v1/shipment-requests/{req_id}/review")
async def review_shipment_request(
    req_id: str,
    body: ReviewAction,
    db: AsyncSession = Depends(get_db),
    user=Depends(current_user)
):
    """Manager/Admin approves or rejects a pending request."""
    role = user.get("role", "Viewer")
    if role not in ("Manager", "Admin"):
        raise HTTPException(403, "Only Managers and Admins can review requests")

    req = await db.get(ShipmentRequestRow, req_id)
    if not req:
        raise HTTPException(404, "Request not found")
    if req.status != "pending":
        raise HTTPException(400, f"Request is already {req.status}")

    u = await db.get(UserRow, user["sub"])
    req.reviewed_by = user["sub"]
    req.reviewer_name = u.name if u else user.get("email", "Manager")
    req.review_note = body.review_note
    req.reviewed_at = _now()

    if body.action == "approve":
        req.status = "approved"
        # Create the actual shipment
        sid = str(uuid.uuid4())
        req.shipment_id = sid
        carrier = req.carrier_name or "Unknown Carrier"
        db.add(ShipmentRow(
            shipment_id=sid,
            tenant_id=req.tenant_id,
            origin_node_id=str(uuid.uuid5(uuid.NAMESPACE_DNS, req.origin)),
            origin_node_name=req.origin,
            destination_node_id=str(uuid.uuid5(uuid.NAMESPACE_DNS, req.destination)),
            destination_node_name=req.destination,
            active_route_id=str(uuid.uuid4()),
            carrier_id=str(uuid.uuid5(uuid.NAMESPACE_DNS, carrier)),
            status="In_Transit",
            risk_score=round(random.uniform(10, 50), 1),
            risk_score_updated_at=_now(),
            eta=req.requested_eta,
            eta_lower=req.requested_eta,
            eta_upper=req.requested_eta,
            demand_priority=req.priority,
            carbon_kg=round(req.weight_kg * 0.05, 1),
            created_at=_now(),
            updated_at=_now(),
        ))
    else:
        req.status = "rejected"

    await db.commit()
    return _req_dict(req)

@app.get("/api/v1/shipment-requests/pending-count")
async def pending_count(db: AsyncSession = Depends(get_db), user=Depends(current_user)):
    result = await db.execute(
        sa.select(sa.func.count()).where(ShipmentRequestRow.status == "pending")
    )
    return {"count": result.scalar_one()}
