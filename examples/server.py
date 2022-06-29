"""A server sends work out on one queue, and receives results on another."""

import argparse
import asyncio
import logging
import typing

import coloredlogs  # type: ignore[import]
from mqclient_pulsar import Queue


async def server(work_queue: Queue, result_queue: Queue) -> None:
    """Demo example server."""
    async with work_queue.open_pub() as p:
        for i in range(100):
            await p.send({"id": i, "cmd": f'echo "{i}"'})

    results = {}
    result_queue.timeout = 5
    async with result_queue.open_sub() as stream:
        async for data in stream:
            assert isinstance(data, dict)
            results[typing.cast(int, data["id"])] = typing.cast(str, data["out"])

    print(results)
    assert len(results) == 100
    for i in results:
        assert results[i].strip() == str(i)


if __name__ == "__main__":
    coloredlogs.install(level=logging.DEBUG)

    parser = argparse.ArgumentParser(
        description="Worker",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--address",
        default="localhost",
        help="queue address",
    )
    parser.add_argument(
        "--work-queue",
        default="example-queue-1",
        help="work queue",
    )
    parser.add_argument(
        "--result-queue",
        default="example-queue-2",
        help="result queue",
    )
    parser.add_argument(
        "--prefetch",
        type=int,
        default=10,
        help="result queue prefetch",
    )
    parser.add_argument(
        "--auth",
        default="",
        help="auth token for MQ server",
    )
    args = parser.parse_args()

    workq = Queue(
        address=args.address,
        name=args.work_queue,
        auth_token=args.auth,
    )
    resultq = Queue(
        address=args.address,
        name=args.result_queue,
        prefetch=args.prefetch,
        auth_token=args.auth,
    )

    asyncio.get_event_loop().run_until_complete(server(workq, resultq))
