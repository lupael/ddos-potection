"""
Kafka consumer for high-throughput flow pipeline.
Replaces Redis Streams as primary flow bus when KAFKA_ENABLED=True.
Redis becomes the fast-window cache only.
"""
import asyncio
import json
import logging
from typing import Callable

from config import settings

logger = logging.getLogger(__name__)

try:
    from aiokafka import AIOKafkaProducer, AIOKafkaConsumer  # type: ignore
    _AIOKAFKA_AVAILABLE = True
except ImportError:
    _AIOKAFKA_AVAILABLE = False
    logger.warning("aiokafka not installed; Kafka pipeline unavailable")


class KafkaFlowProducer:
    """Publishes flow records to a Kafka topic."""

    def __init__(self):
        self._producer = None

    async def start(self) -> None:
        if not _AIOKAFKA_AVAILABLE:
            logger.warning("aiokafka not available; KafkaFlowProducer is a no-op")
            return
        if not settings.KAFKA_ENABLED:
            return
        self._producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        await self._producer.start()
        logger.info(
            "KafkaFlowProducer started (bootstrap=%s, topic=%s)",
            settings.KAFKA_BOOTSTRAP_SERVERS,
            settings.KAFKA_FLOW_TOPIC,
        )

    async def stop(self) -> None:
        if self._producer is not None:
            await self._producer.stop()
            self._producer = None
            logger.info("KafkaFlowProducer stopped")

    async def publish_flow(self, flow: dict) -> None:
        """Publish a single flow record to the Kafka flow topic."""
        if not settings.KAFKA_ENABLED or self._producer is None:
            return
        try:
            await self._producer.send_and_wait(settings.KAFKA_FLOW_TOPIC, flow)
        except Exception as exc:
            logger.error("Failed to publish flow to Kafka: %s", exc)


class KafkaFlowConsumer:
    """Consumes flow records from a Kafka topic."""

    def __init__(self):
        self._consumer = None
        self._running = False

    async def start(self) -> None:
        if not _AIOKAFKA_AVAILABLE:
            logger.warning("aiokafka not available; KafkaFlowConsumer is a no-op")
            return
        if not settings.KAFKA_ENABLED:
            return
        self._consumer = AIOKafkaConsumer(
            settings.KAFKA_FLOW_TOPIC,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id=settings.KAFKA_CONSUMER_GROUP,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            auto_offset_reset="latest",
        )
        await self._consumer.start()
        self._running = True
        logger.info(
            "KafkaFlowConsumer started (bootstrap=%s, topic=%s, group=%s)",
            settings.KAFKA_BOOTSTRAP_SERVERS,
            settings.KAFKA_FLOW_TOPIC,
            settings.KAFKA_CONSUMER_GROUP,
        )

    async def stop(self) -> None:
        self._running = False
        if self._consumer is not None:
            await self._consumer.stop()
            self._consumer = None
            logger.info("KafkaFlowConsumer stopped")

    async def consume(self, callback: Callable) -> None:
        """Continuously consume messages and call *callback(flow)* for each."""
        if not settings.KAFKA_ENABLED or self._consumer is None:
            logger.warning("Kafka consumer not started; consume() is a no-op")
            return
        try:
            async for message in self._consumer:
                if not self._running:
                    break
                try:
                    await callback(message.value)
                except Exception as exc:
                    logger.error("Error in Kafka flow callback: %s", exc)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error("Kafka consumer error: %s", exc)
