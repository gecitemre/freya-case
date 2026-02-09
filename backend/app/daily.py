import os
import time
from typing import Tuple

import aiohttp

from pipecat.transports.daily.utils import (
    DailyRESTHelper,
    DailyRoomParams,
    DailyRoomProperties,
)


async def create_room_and_tokens(session_name: str) -> Tuple[str, str, str]:
    api_key = os.environ.get("DAILY_API_KEY")
    if not api_key:
        raise RuntimeError("DAILY_API_KEY is not set")

    async with aiohttp.ClientSession() as session:
        helper = DailyRESTHelper(daily_api_key=api_key, aiohttp_session=session)

        room = await helper.create_room(
            DailyRoomParams(
                name=session_name,
                properties=DailyRoomProperties(
                    exp=int(time.time()) + 60 * 60,
                    enable_chat=False,
                    enable_screenshare=False,
                ),
            )
        )

        room_url = room.url
        # API: owner flag controls privileges
        client_token = await helper.get_token(room_url, owner=False)
        bot_token = await helper.get_token(room_url, owner=True)

        return room_url, client_token, bot_token
