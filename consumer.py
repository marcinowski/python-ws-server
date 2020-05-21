#!/usr/bin/env python

import aio_pika
import asyncio
import json
import os
import websockets

from logger import logger

BROKER_LOGIN = os.getenv("RABBITMQ_USER")
BROKER_PASS = os.getenv("RABBITMQ_PASS")
BROKER_HOST = os.getenv("RABBITMQ_HOST")
BROKER_PORT = os.getenv("RABBITMQ_TCP_PORT")
NOTIFICATIONS_HOST = os.getenv("NOTIFICATIONS_HOST")
NOTIFICATIONS_PORT = os.getenv("NOTIFICATIONS_PORT")


async def producer(loop: asyncio.AbstractEventLoop,) -> None:
    connection = await aio_pika.connect_robust(
        f"amqp://{BROKER_LOGIN}:{BROKER_PASS}@{BROKER_HOST}:{BROKER_PORT}", loop=loop
    )  # type aio_pika.Connection
    async with connection, websockets.connect(
        f"ws://{NOTIFICATIONS_HOST}:{NOTIFICATIONS_PORT}"
    ) as websocket:
        logger.info("Connected to rabbit and websocket servers.")
        channel = await connection.channel()  # type: aio_pika.Channel
        exchange = await channel.declare_exchange(
            "notifications", aio_pika.ExchangeType.FANOUT
        )  # type: aio_pika.Exchange
        queue = await channel.declare_queue(exclusive=True)  # type: aio_pika.Queue
        await queue.bind(exchange)

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    body = json.loads(
                        message.body.decode()
                    )  # we except json responses from the queue
                    msg = json.dumps(
                        {"propagate": body}
                    )  # hacky, so that ws server knows it's us
                    await websocket.send(msg)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(producer(loop))
    loop.close()
