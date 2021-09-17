"""Back-end using Apache Pulsar."""

import logging
import time
from typing import Generator, Optional

import pulsar  # type: ignore
from mqclient import backend_interface, log_msgs
from mqclient.backend_interface import (
    RETRY_DELAY,
    TIMEOUT_MILLIS_DEFAULT,
    TRY_ATTEMPTS,
    AlreadyClosedExcpetion,
    ClosingFailedExcpetion,
    Message,
    Pub,
    RawQueue,
    Sub,
)


class Pulsar(RawQueue):
    """Base Pulsar wrapper.

    Extends:
        RawQueue
    """

    def __init__(self, address: str, topic: str, auth_token: str = "") -> None:
        """Set address, topic, and client.

        Arguments:
            address {str} -- the pulsar server address, if address doesn't start with 'pulsar', append 'pulsar://'
            topic {str} -- the name of the topic
            auth_token {str} -- the (jwt) authentication token
        """
        super().__init__()
        self.address = address
        if not self.address.startswith("pulsar"):
            self.address = "pulsar://" + self.address
        self.topic = topic
        self.client = None  # type: pulsar.Client
        self.auth = pulsar.AuthenticationToken(auth_token) if auth_token else None

    def connect(self) -> None:
        """Set up client."""
        super().connect()
        self.client = pulsar.Client(self.address, authentication=self.auth)

    def close(self) -> None:
        """Close client."""
        super().close()
        if not self.client:
            raise ClosingFailedExcpetion("No client to close.")
        try:
            self.client.close()
        except Exception as e:
            # https://github.com/apache/pulsar/issues/3127
            if str(e) == "Pulsar error: AlreadyClosed":
                raise AlreadyClosedExcpetion(str(e)) from e
            raise ClosingFailedExcpetion(str(e)) from e


class PulsarPub(Pulsar, Pub):
    """Wrapper around pulsar.Producer.

    Extends:
        Pulsar
        Pub
    """

    def __init__(self, address: str, topic: str, auth_token: str = "") -> None:
        logging.debug(f"{log_msgs.INIT_PUB} ({address}; {topic})")
        super().__init__(address, topic, auth_token)
        self.producer = None  # type: pulsar.Producer

    def connect(self) -> None:
        """Connect to producer."""
        logging.debug(log_msgs.CONNECTING_PUB)
        super().connect()

        self.producer = self.client.create_producer(self.topic)
        logging.debug(log_msgs.CONNECTED_PUB)

    def close(self) -> None:
        """Close connection."""
        logging.debug(log_msgs.CLOSING_PUB)
        super().close()
        if not self.producer:
            raise ClosingFailedExcpetion("No producer to sub.")
        logging.debug(log_msgs.CLOSED_PUB)

    def send_message(self, msg: bytes) -> None:
        """Send a message on a queue."""
        logging.debug(log_msgs.SENDING_MESSAGE)
        if not self.producer:
            raise RuntimeError("queue is not connected")

        self.producer.send(msg)
        logging.debug(log_msgs.SENT_MESSAGE)


class PulsarSub(Pulsar, Sub):
    """Wrapper around pulsar.Consumer.

    Extends:
        Pulsar
        Sub
    """

    def __init__(
        self, address: str, topic: str, subscription_name: str, auth_token: str = ""
    ) -> None:
        logging.debug(f"{log_msgs.INIT_SUB} ({address}; {topic})")
        super().__init__(address, topic, auth_token=auth_token)
        self.consumer = None  # type: pulsar.Consumer
        self.subscription_name = subscription_name
        self.prefetch = 1

    def connect(self) -> None:
        """Connect to subscriber."""
        logging.debug(log_msgs.CONNECTING_SUB)
        super().connect()

        self.consumer = self.client.subscribe(
            self.topic,
            self.subscription_name,
            receiver_queue_size=self.prefetch,
            consumer_type=pulsar.ConsumerType.Shared,
            initial_position=pulsar.InitialPosition.Earliest,
            negative_ack_redelivery_delay_ms=0,
        )
        logging.debug(log_msgs.CONNECTED_SUB)

    def close(self) -> None:
        """Close client and redeliver any unacknowledged messages."""
        logging.debug(log_msgs.CLOSING_SUB)
        if not self.consumer:
            raise ClosingFailedExcpetion("No consumer to close.")
        self.consumer.redeliver_unacknowledged_messages()
        super().close()
        logging.debug(log_msgs.CLOSED_SUB)

    @staticmethod
    def _to_message(  # type: ignore[override]  # noqa: F821 # pylint: disable=W0221
        msg: pulsar.Message,
    ) -> Optional[Message]:
        """Transform Puslar-Message to Message type."""
        id_, data = msg.message_id(), msg.data()

        if id_ is None or data is None:  # message_id may be 0; data may be b''
            return None

        # Need to serialize id? (message_id.serialize() -> bytes)
        if isinstance(id_, pulsar._pulsar.MessageId):  # pylint: disable=I1101,W0212
            return Message(id_.serialize(), data)
        # Send original data
        else:
            return Message(id_, data)

    def get_message(
        self, timeout_millis: Optional[int] = TIMEOUT_MILLIS_DEFAULT
    ) -> Optional[Message]:
        """Get a single message from a queue.

        To endlessly block until a message is available, set
        `timeout_millis=None`.
        """
        logging.debug(log_msgs.GETMSG_RECEIVE_MESSAGE)
        if not self.consumer:
            raise RuntimeError("queue is not connected")

        for i in range(TRY_ATTEMPTS):
            if i > 0:
                logging.debug(
                    f"{log_msgs.GETMSG_CONNECTION_ERROR_TRY_AGAIN} (attempt #{i+1})..."
                )

            try:
                recvd = self.consumer.receive(timeout_millis=timeout_millis)
                msg = PulsarSub._to_message(recvd)
                if msg:
                    logging.debug(
                        f"{log_msgs.GETMSG_RECEIVED_MESSAGE} ({msg.msg_id!r})."
                    )
                    return msg
                else:
                    logging.debug(log_msgs.GETMSG_NO_MESSAGE)
                    return None

            except Exception as e:
                # https://github.com/apache/pulsar/issues/3127
                if str(e) == "Pulsar error: TimeOut":
                    logging.debug(log_msgs.GETMSG_TIMEOUT_ERROR)
                    return None
                # https://github.com/apache/pulsar/issues/3127
                if str(e) == "Pulsar error: AlreadyClosed":
                    self.close()
                    time.sleep(RETRY_DELAY)
                    self.connect()
                    continue
                logging.debug(
                    f"{log_msgs.GETMSG_RAISE_OTHER_ERROR} ({e.__class__.__name__})."
                )
                raise

        logging.debug(log_msgs.GETMSG_CONNECTION_ERROR_MAX_RETRIES)
        raise Exception("Pulsar connection error")

    def ack_message(self, msg: Message) -> None:
        """Ack a message from the queue."""
        logging.debug(log_msgs.ACKING_MESSAGE)
        if not self.consumer:
            raise RuntimeError("queue is not connected")

        if isinstance(msg.msg_id, bytes):
            self.consumer.acknowledge(pulsar.MessageId.deserialize(msg.msg_id))
        else:
            self.consumer.acknowledge(msg.msg_id)

        msg.ack_status = Message.AckStatus.ACKED
        logging.debug(f"{log_msgs.ACKED_MESSAGE} ({msg.msg_id!r}).")

    def reject_message(self, msg: Message) -> None:
        """Reject (nack) a message from the queue."""
        logging.debug(log_msgs.NACKING_MESSAGE)
        if not self.consumer:
            raise RuntimeError("queue is not connected")

        if isinstance(msg.msg_id, bytes):
            self.consumer.negative_acknowledge(pulsar.MessageId.deserialize(msg.msg_id))
        else:
            self.consumer.negative_acknowledge(msg.msg_id)

        msg.ack_status = Message.AckStatus.NACKED
        logging.debug(f"{log_msgs.NACKED_MESSAGE} ({msg.msg_id!r}).")

    def message_generator(
        self, timeout: int = 60, propagate_error: bool = True
    ) -> Generator[Optional[Message], None, None]:
        """Yield Messages.

        Generate messages with variable timeout.
        Yield `None` on `throw()`.

        Keyword Arguments:
            timeout {int} -- timeout in seconds for inactivity (default: {60})
            propagate_error {bool} -- should errors from downstream code kill the generator? (default: {True})
        """
        logging.debug(log_msgs.MSGGEN_ENTERED)
        if not self.consumer:
            raise RuntimeError("queue is not connected")

        msg = None
        try:
            while True:
                # get message
                logging.debug(log_msgs.MSGGEN_GET_NEW_MESSAGE)
                msg = self.get_message(timeout_millis=timeout * 1000)
                if msg is None:
                    logging.info(log_msgs.MSGGEN_NO_MESSAGE_LOOK_BACK_IN_QUEUE)
                    break

                # yield message to consumer
                try:
                    logging.debug(f"{log_msgs.MSGGEN_YIELDING_MESSAGE} [{msg}]")
                    yield msg
                # consumer throws Exception...
                except Exception as e:  # pylint: disable=W0703
                    logging.debug(log_msgs.MSGGEN_DOWNSTREAM_ERROR)
                    if propagate_error:
                        logging.debug(log_msgs.MSGGEN_PROPAGATING_ERROR)
                        raise
                    logging.warning(
                        f"{log_msgs.MSGGEN_EXCEPTED_DOWNSTREAM_ERROR} {e}.",
                        exc_info=True,
                    )
                    yield None  # hand back to consumer
                # consumer requests again, aka next()
                else:
                    pass

        # generator exit (explicit close(), or break in consumer's loop)
        except GeneratorExit:
            logging.debug(log_msgs.MSGGEN_GENERATOR_EXITING)
            logging.debug(log_msgs.MSGGEN_GENERATOR_EXITED)


class Backend(backend_interface.Backend):
    """Pulsar Pub-Sub Backend Factory.

    Extends:
        Backend
    """

    # NOTE - use single shared subscription
    # (making multiple unique subscription names would create independent subscriptions)
    SUBSCRIPTION_NAME = "i3-pulsar-sub"

    @staticmethod
    def create_pub_queue(address: str, name: str, auth_token: str = "") -> PulsarPub:
        """Create a publishing queue."""
        q = PulsarPub(  # pylint: disable=invalid-name
            address, name, auth_token=auth_token
        )
        q.connect()
        return q

    @staticmethod
    def create_sub_queue(
        address: str, name: str, prefetch: int = 1, auth_token: str = ""
    ) -> PulsarSub:
        """Create a subscription queue."""
        # pylint: disable=invalid-name
        q = PulsarSub(address, name, Backend.SUBSCRIPTION_NAME, auth_token=auth_token)
        q.prefetch = prefetch
        q.connect()
        return q
