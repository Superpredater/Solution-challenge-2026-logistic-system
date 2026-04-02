"""Collaboration Workspace — TaskManager: task creation and status tracking."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.shared.models import CollaborationTask
from services.shared.orm_models import CollaborationTaskORM

logger = logging.getLogger(__name__)


class TaskManager:
    """Task creation, assignment, and status tracking (Req 17.3)."""

    async def create_task(
        self,
        task: CollaborationTask,
        session: AsyncSession,
    ) -> CollaborationTask:
        """Persist a new collaboration task."""
        orm = CollaborationTaskORM(
            task_id=task.task_id,
            tenant_id=task.tenant_id,
            shipment_id=task.shipment_id,
            title=task.title,
            description=task.description,
            assigned_to=task.assigned_to,
            status=task.status,
            due_date=task.due_date,
            created_by=task.created_by,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )
        session.add(orm)
        await session.commit()
        return task

    async def update_status(
        self,
        task_id: UUID,
        status: str,
        tenant_id: UUID,
        session: AsyncSession,
    ) -> CollaborationTask:
        """Update the status of an existing task."""
        result = await session.execute(
            select(CollaborationTaskORM).where(
                CollaborationTaskORM.task_id == task_id,
                CollaborationTaskORM.tenant_id == tenant_id,
            )
        )
        orm = result.scalar_one_or_none()
        if orm is None:
            raise ValueError(f"Task {task_id} not found for tenant {tenant_id}")

        orm.status = status
        orm.updated_at = datetime.now(timezone.utc)
        await session.commit()

        return CollaborationTask(
            task_id=orm.task_id,
            tenant_id=orm.tenant_id,
            shipment_id=orm.shipment_id,
            title=orm.title,
            description=orm.description,
            assigned_to=orm.assigned_to,
            status=orm.status,
            due_date=orm.due_date,
            created_by=orm.created_by,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    async def get_tasks(
        self,
        shipment_id: UUID,
        tenant_id: UUID,
        session: AsyncSession,
    ) -> list[CollaborationTask]:
        """Retrieve all tasks for a shipment."""
        result = await session.execute(
            select(CollaborationTaskORM).where(
                CollaborationTaskORM.shipment_id == shipment_id,
                CollaborationTaskORM.tenant_id == tenant_id,
            ).order_by(CollaborationTaskORM.created_at.asc())
        )
        rows = result.scalars().all()
        return [
            CollaborationTask(
                task_id=r.task_id,
                tenant_id=r.tenant_id,
                shipment_id=r.shipment_id,
                title=r.title,
                description=r.description,
                assigned_to=r.assigned_to,
                status=r.status,
                due_date=r.due_date,
                created_by=r.created_by,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in rows
        ]
