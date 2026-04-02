"""aiokafka producer/consumer helpers."""

import json
import logging
from typing import Any, AsyncGenerator, Callable, Awaitable

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from .config import settings

logger = logging.getLogger(__name__)


async def get_producer() -> AsyncGenerator[AIOKafkaProducer, None]:
    """Async context manager yielding a Kafka producer."""
    producer = AIOKafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        key_serializer=lambda k: k.encode("utf-8") if k else None,
    )
    await producer.start()
    try:
        yield producer
    finally:
        await producer.stop()


async def publish(topic: str, value: dict[str, Any], key: str | None = None) -> None:
    """Publish a single message to a Kafka topic."""
    producer = AIOKafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        key_serializer=lambda k: k.encode("utf-8") if k else None,
    )
    await producer.start()
    try:
        await producer.send_and_wait(topic, value=value, key=key)
    finally:
        await producer.stop()


async def consume(
    topics: list[str],
    group_id: str,
    handler: Callable[[str, dict[str, Any]], Awaitable[None]],
) -> None:
    """
    Consume messages from Kafka topics and dispatch to handler.
    Runs indefinitely until cancelled.
    """
    consumer = AIOKafkaConsumer(
        *topics,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id=group_id,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
    )
    await consumer.start()
    try:
        async for msg in consumer:
            try:
                await handler(msg.topic, msg.value)
            except Exception as exc:
                logger.error("Error handling message from %s: %s", msg.topic, exc)
    finally:
        await consumer.stop()
