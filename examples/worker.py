"""A worker processes messages from one queue, and sends results on a second
queue."""

import argparse
import asyncio
import logging
import subprocess

import coloredlogs  # type: ignore[import]
from mqclient_pulsar import Queue


async def worker(recv_queue: Queue, send_queue: Queue) -> None:
    """Demo example worker."""
    async with recv_queue.open_sub() as stream, send_queue.open_pub() as p:
        async for data in stream:
            cmd = data["cmd"]
            out = subprocess.check_output(cmd, shell=True)
            data["out"] = out.decode("utf-8")
            await p.send(data)


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
        "--in-queue",
        default="example-queue-1",
        help="input queue",
    )
    parser.add_argument(
        "--out-queue",
        default="example-queue-2",
        help="output queue",
    )
    parser.add_argument(
        "--prefetch",
        type=int,
        default=10,
        help="input queue prefetch",
    )
    parser.add_argument(
        "--auth",
        default="",
        help="auth token for MQ server",
    )
    args = parser.parse_args()

    inq = Queue(
        address=args.address,
        name=args.in_queue,
        prefetch=args.prefetch,
        auth_token=args.auth,
    )
    outq = Queue(
        address=args.address,
        name=args.out_queue,
        auth_token=args.auth,
    )

    asyncio.get_event_loop().run_until_complete(worker(inq, outq))
