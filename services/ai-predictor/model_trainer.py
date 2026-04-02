"""Scheduled model trainer for the ETAPredictor."""

from __future__ import annotations

import asyncio
import logging
import pickle
from pathlib import Path

import numpy as np
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .eta_predictor import ETAPredictor

logger = logging.getLogger(__name__)

_MODEL_PATH = Path("/tmp/eta_predictor.pkl")
_RETRAIN_INTERVAL_SECONDS = 86400  # 24 hours


class ModelTrainer:
    """Retrain ETAPredictor every 24 hours from historical delivery data."""

    def __init__(self, predictor: ETAPredictor) -> None:
        self._predictor = predictor

    async def train(self, session: AsyncSession) -> None:
        logger.info("Starting ETAPredictor training run")
        try:
            result = await session.execute(
                text(
                    "SELECT distance_km, carrier_risk_score, weather_risk, "
                    "num_legs, historical_avg_duration_h, actual_duration_h "
                    "FROM eta_feedback "
                    "JOIN shipments USING (shipment_id) "
                    "LIMIT 10000"
                )
            )
            rows = result.fetchall()
        except Exception as exc:
            logger.warning("Could not load training data: %s", exc)
            return

        if len(rows) < 10:
            logger.info("Insufficient training data (%d rows), skipping", len(rows))
            return

        X = np.array([[r[0], r[1], r[2], r[3], r[4]] for r in rows])
        y = np.array([r[5] for r in rows])
        self._predictor.fit(X, y)

        # Save to local file (stub for S3 in production)
        with open(_MODEL_PATH, "wb") as f:
            pickle.dump(self._predictor, f)
        logger.info("ETAPredictor retrained on %d samples, saved to %s", len(rows), _MODEL_PATH)

    async def run_loop(self, session: AsyncSession) -> None:
        while True:
            await self.train(session)
            await asyncio.sleep(_RETRAIN_INTERVAL_SECONDS)
