import asyncio
import os
import random
import time
from typing import Tuple

import aiohttp

from pipecat.transports.daily.utils import (
    DailyRESTHelper,
    DailyRoomParams,
    DailyRoomProperties,
)

import logging

logger = logging.getLogger("agent-console")


async def _retry_async(operation, *, attempts: int, base_delay: float, name: str):
    last_exc = None
    for attempt in range(1, attempts + 1):
        try:
            return await operation()
        except Exception as exc:
            last_exc = exc
            if attempt >= attempts:
                break
            # Exponential backoff with small jitter
            delay = base_delay * (2 ** (attempt - 1))
            delay += random.uniform(0, base_delay)
            logger.warning(
                "%s failed (attempt %s/%s): %s. Retrying in %.2fs",
                name,
                attempt,
                attempts,
                exc,
                delay,
            )
            await asyncio.sleep(delay)
    raise last_exc

async def create_room_and_tokens(session_name: str) -> Tuple[str, str, str]:
    api_key = os.environ.get("DAILY_API_KEY")
    if not api_key:
        raise RuntimeError("DAILY_API_KEY is not set")

    async with aiohttp.ClientSession() as session:
        helper = DailyRESTHelper(daily_api_key=api_key, aiohttp_session=session)

        async def _create_room():
            return await helper.create_room(
                DailyRoomParams(
                    name=session_name,
                    properties=DailyRoomProperties(
                        exp=int(time.time()) + 60 * 60,
                        enable_chat=False,
                        enable_screenshare=False,
                    ),
                )
            )

        room = await _retry_async(_create_room, attempts=3, base_delay=0.5, name="daily.create_room")

        room_url = room.url

        async def _get_client_token():
            return await helper.get_token(room_url, owner=False)

        async def _get_bot_token():
            return await helper.get_token(room_url, owner=True)

        # API: owner flag controls privileges
        client_token = await _retry_async(
            _get_client_token, attempts=3, base_delay=0.3, name="daily.get_token.client"
        )
        bot_token = await _retry_async(
            _get_bot_token, attempts=3, base_delay=0.3, name="daily.get_token.bot"
        )

        return room_url, client_token, bot_token
