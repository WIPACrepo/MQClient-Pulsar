"""A worker processes messages from one queue, and sends results on a second
queue."""

import subprocess

from mqclient_pulsar import Queue


def worker(recv_queue: Queue, send_queue: Queue) -> None:
    """Demo example worker."""
    with recv_queue.recv() as stream:
        for data in stream:
            cmd = data["cmd"]
            out = subprocess.check_output(cmd, shell=True)
            data["out"] = out.decode("utf-8")
            send_queue.send(data)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Worker")
    parser.add_argument("--address", default="localhost", help="queue address")
    parser.add_argument("--in-queue", default="queue1", help="input queue")
    parser.add_argument("--out-queue", default="queue2", help="output queue")
    parser.add_argument("--prefetch", type=int, default=10, help="input queue prefetch")
    args = parser.parse_args()

    inq = Queue(address=args.address, name=args.in_queue, prefetch=args.prefetch)
    outq = Queue(address=args.address, name=args.out_queue)

    worker(inq, outq)
