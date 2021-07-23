"""Queue class encapsulating a pub-sub messaging system with Pulsar."""


from typing import Any, cast

import mqclient

from . import apachepulsar


class Queue(mqclient.queue.Queue):
    __doc__ = mqclient.queue.Queue.__doc__

    def __init__(self, *args: Any, **kargs: Any) -> None:
        super().__init__(
            cast(  # mypy is very picky
                mqclient.backend_interface.Backend, apachepulsar.Backend
            ),
            *args,
            **kargs
        )
