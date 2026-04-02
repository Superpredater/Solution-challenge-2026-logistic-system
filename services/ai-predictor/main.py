"""AI Predictor — background tasks and Kafka consumer."""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import UUID

from fastapi import FastAPI

from services.shared.kafka import consume
from .demand_forecaster import DemandForecaster
from .eta_predictor import ETAPredictor
from .model_trainer import ModelTrainer

logger = logging.getLogger(__name__)

app = FastAPI(title="AI Predictor", version="1.0.0")

_predictor = ETAPredictor()
_forecaster = DemandForecaster()
_trainer = ModelTrainer(_predictor)


async def _handle_message(topic: str, value: dict[str, Any]) -> None:
    if topic == "shipment.route.updates":
        shipment_id = value.get("shipment_id")
        features = value.get("features", {})
        if shipment_id and features:
            eta, lower, upper = _predictor.predict(features)
            logger.info(
                "ETA prediction for shipment %s: %s [%s – %s]",
                shipment_id, eta, lower, upper,
            )


@app.on_event("startup")
async def startup() -> None:
    asyncio.create_task(
        consume(["shipment.route.updates"], "ai-predictor", _handle_message)
    )
    # ModelTrainer runs every 24h — requires DB session in production
    # asyncio.create_task(_trainer.run_loop(session))


@app.get("/api/v1/predict/eta")
async def predict_eta(
    distance_km: float = 1000.0,
    carrier_risk_score: float = 20.0,
    weather_risk: float = 10.0,
    num_legs: int = 3,
    historical_avg_duration_h: float = 48.0,
) -> dict:
    features = {
        "distance_km": distance_km,
        "carrier_risk_score": carrier_risk_score,
        "weather_risk": weather_risk,
        "num_legs": num_legs,
        "historical_avg_duration_h": historical_avg_duration_h,
    }
    eta, lower, upper = _predictor.predict(features)
    return {
        "eta": eta.isoformat(),
        "lower_bound": lower.isoformat(),
        "upper_bound": upper.isoformat(),
    }


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
