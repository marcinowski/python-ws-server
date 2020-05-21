#!/usr/bin/env python

import aio_pika
import argparse
import asyncio
import json
import logging
import sys
import websockets

from concurrent.futures import ProcessPoolExecutor
from functools import partial
from logger import logger, get_graypy_handler


def getLogger():
    root = logging.getLogger()
    logLevel = logging.INFO
    root.setLevel(logLevel)
    ws_logger = logging.getLogger("websockets.server")
    ws_logger.setLevel(logging.ERROR)
    ws_logger.addHandler(handler)
    return root


class Connections:
    """
  Used as a connection storage and for some helper functions
  """

    authenticated_connections = {}
    log = getLogger()

    @classmethod
    def is_connected(cls, user_id: int) -> bool:
        user_id in cls.authenticated_connections

    @classmethod
    def add_connection(
        cls, user_id: int, websocket: websockets.server.WebSocketServerProtocol
    ) -> dict:
        cls.log.info(f"Registering user #{user_id} to connections.")
        cls.authenticated_connections[user_id] = websocket
        return cls.authenticated_connections

    @classmethod
    def remove_connection(cls, user_id: int) -> dict:
        cls.log.info(f"Removing user #{user_id} from connections.")
        cls.authenticated_connections.pop(user_id)
        return cls.authenticated_connections

    @classmethod
    async def authenticate(cls, user_id: int, token: str) -> bool:
        cls.log.debug(f"Authenticating user #{user_id}")
        await asyncio.sleep(1)  # call API here
        return True

    @classmethod
    async def send_data_to_user(cls, user_id: int, data: str) -> None:
        cls.log.debug(f"Sending data to user #{user_id}")
        ws = cls.authenticated_connections.get(user_id, None)
        if ws is not None:
            try:
                await ws.send(data)
            except Exception as e:
                cls.log.error(f"Sending data to user #{user_id} failed! {e}")
                cls.remove_connection(user_id)


async def consumer_handler(websocket, path, conns, q):
    """
    This is for receiving messages sent TO the websocket server.
  """
    while True:
        async for message in websocket:
            data = json.loads(message)
            if "propagate" in data:  # this one's coming from our consumers
                await q.put(data["propagate"])
            else:  # this is coming from users
                user_id = data.get("user_id", None)
                token = data.get("token", None)
                if user_id and token:
                    if await conns.authenticate(user_id, token):
                        conns.add_connection(user_id, websocket)


async def producer_handler(websocket, path, conns, q):
    """
    This is for sending messages FROM the weboscket server
  """
    while True:
        msg = await q.get()
        user_id = msg.get("user", None)
        if user_id:
            await conns.send_data_to_user(user_id, json.dumps(msg))


async def handler(websocket, path):
    """
    The server combines two functionalities
     - listening to incoming messages
     - sending messages to clients
  """
    conns = Connections()
    q = asyncio.Queue()
    consumer_task = asyncio.ensure_future(consumer_handler(websocket, path, conns, q))
    producer_task = asyncio.ensure_future(producer_handler(websocket, path, conns, q))
    done, pending = await asyncio.wait(
        [consumer_task, producer_task], return_when=asyncio.FIRST_COMPLETED,
    )
    await q.join()
    for task in pending:
        task.cancel()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-p", "--port", help="port to start the server on", default=8675
    )
    parser.add_argument(
        "-H", "--host", help="host to start the server on", default="0.0.0.0"
    )
    parser.add_argument(
        # doesn't work for now
        "-v",
        "--verbose",
        help="log verbosity (debug/info)",
        action="store_true",
    )
    args = parser.parse_args()
    logger.info(f"Starting websocket server on {args.host}:{args.port}")
    start_server = websockets.serve(handler, host=args.host, port=args.port)
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()
