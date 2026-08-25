"""Redis Streams producer for the Document Service M1 event contract."""

from __future__ import annotations

from collections.abc import Mapping

import redis


class RedisStreamPublisher:
    def __init__(self, *, redis_url: str, stream_name: str) -> None:
        self._redis_url = redis_url
        self._stream_name = stream_name

    def publish_document(self, fields: Mapping[str, str]) -> str:
        client = redis.from_url(self._redis_url, socket_connect_timeout=2)
        try:
            message_id = client.xadd(self._stream_name, fields)
            return message_id.decode() if isinstance(message_id, bytes) else message_id
        finally:
            client.close()
