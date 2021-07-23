"""A server sends work out on one queue, and receives results on another."""

import typing

from mqclient_pulsar import Queue


def server(work_queue: Queue, result_queue: Queue) -> None:
    """Demo example server."""
    for i in range(100):
        work_queue.send({"id": i, "cmd": f'echo "{i}"'})

    results = {}
    result_queue.timeout = 5
    with result_queue.recv() as stream:
        for data in stream:
            assert isinstance(data, dict)
            results[typing.cast(int, data["id"])] = typing.cast(str, data["out"])

    print(results)
    assert len(results) == 100
    for i in results:
        assert results[i].strip() == str(i)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Worker")
    parser.add_argument("--address", default="localhost", help="queue address")
    parser.add_argument("--work-queue", default="queue1", help="work queue")
    parser.add_argument("--result-queue", default="queue2", help="result queue")
    parser.add_argument(
        "--prefetch", type=int, default=10, help="result queue prefetch"
    )
    args = parser.parse_args()

    workq = Queue(address=args.address, name=args.work_queue)
    resultq = Queue(
        address=args.address, name=args.result_queue, prefetch=args.prefetch
    )

    server(workq, resultq)
