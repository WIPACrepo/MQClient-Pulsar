"""Run integration tests for Pulsar backend."""

import logging

from mqclient.abstract_backend_tests import integrate_backend_interface, integrate_queue
from mqclient.abstract_backend_tests.utils import (  # pytest.fixture # noqa: F401 # pylint: disable=W0611
    queue_name,
)
from mqclient_pulsar.apachepulsar import Backend

logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger("flake8").setLevel(logging.WARNING)


class TestPulsarQueue(integrate_queue.PubSubQueue):
    """Run PubSubQueue integration tests with Pulsar backend."""

    backend = Backend()


class TestPulsarBackend(integrate_backend_interface.PubSubBackendInterface):
    """Run PubSubBackendInterface integration tests with Pulsar backend."""

    backend = Backend()
