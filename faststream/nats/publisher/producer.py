import asyncio
from typing import TYPE_CHECKING, Optional

import anyio
import nats
from typing_extensions import override

from faststream._internal.endpoint.utils import resolve_custom_func
from faststream._internal.producer import ProducerProto
from faststream.exceptions import FeatureNotSupportedException
from faststream.message import encode_message
from faststream.nats.helpers.state import (
    ConnectedState,
    ConnectionState,
    EmptyConnectionState,
)
from faststream.nats.parser import NatsParser

if TYPE_CHECKING:
    from fast_depends.library.serializer import SerializerProto
    from nats.aio.client import Client
    from nats.aio.msg import Msg
    from nats.js import JetStreamContext

    from faststream._internal.types import (
        AsyncCallable,
        CustomCallable,
    )
    from faststream.nats.response import NatsPublishCommand
    from faststream.nats.schemas import PubAck


class NatsFastProducer(ProducerProto):
    def connect(
        self, connection: "Client", serializer: Optional["SerializerProto"]
    ) -> None: ...

    def disconnect(self) -> None: ...

    @override
    async def publish(  # type: ignore[override]
        self,
        cmd: "NatsPublishCommand",
    ) -> None: ...

    @override
    async def request(  # type: ignore[override]
        self,
        cmd: "NatsPublishCommand",
    ) -> "Msg": ...

    @override
    async def publish_batch(
        self,
        cmd: "NatsPublishCommand",
    ) -> None: ...


class NatsFastProducerImpl(NatsFastProducer):
    """A class to represent a NATS producer."""

    _decoder: "AsyncCallable"
    _parser: "AsyncCallable"

    def __init__(
        self,
        parser: Optional["CustomCallable"],
        decoder: Optional["CustomCallable"],
    ) -> None:
        self.serializer: SerializerProto | None = None

        default = NatsParser(pattern="", is_ack_disabled=True)
        self._parser = resolve_custom_func(parser, default.parse_message)
        self._decoder = resolve_custom_func(decoder, default.decode_message)

        self.__state: ConnectionState[Client] = EmptyConnectionState()

    def connect(
        self, connection: "Client", serializer: Optional["SerializerProto"]
    ) -> None:
        self.serializer = serializer
        self.__state = ConnectedState(connection)

    def disconnect(self) -> None:
        self.__state = EmptyConnectionState()

    @override
    async def publish(  # type: ignore[override]
        self,
        cmd: "NatsPublishCommand",
    ) -> None:
        payload, content_type = encode_message(cmd.body, self.serializer)

        headers_to_send = {
            "content-type": content_type or "",
            **cmd.headers_to_publish(),
        }

        return await self.__state.connection.publish(
            subject=cmd.destination,
            payload=payload,
            reply=cmd.reply_to,
            headers=headers_to_send,
        )

    @override
    async def request(  # type: ignore[override]
        self,
        cmd: "NatsPublishCommand",
    ) -> "Msg":
        payload, content_type = encode_message(cmd.body, self.serializer)

        headers_to_send = {
            "content-type": content_type or "",
            **cmd.headers_to_publish(),
        }

        return await self.__state.connection.request(
            subject=cmd.destination,
            payload=payload,
            headers=headers_to_send,
            timeout=cmd.timeout,
        )

    @override
    async def publish_batch(
        self,
        cmd: "NatsPublishCommand",
    ) -> None:
        msg = "NATS doesn't support publishing in batches."
        raise FeatureNotSupportedException(msg)


class NatsJSFastProducer(NatsFastProducer):
    """A class to represent a NATS JetStream producer."""

    _decoder: "AsyncCallable"
    _parser: "AsyncCallable"

    def __init__(
        self,
        *,
        parser: Optional["CustomCallable"],
        decoder: Optional["CustomCallable"],
    ) -> None:
        self.serializer: SerializerProto | None = None

        default = NatsParser(pattern="", is_ack_disabled=True)
        self._parser = resolve_custom_func(parser, default.parse_message)
        self._decoder = resolve_custom_func(decoder, default.decode_message)

        self.__state: ConnectionState[JetStreamContext] = EmptyConnectionState()

    def connect(
        self, connection: "JetStreamContext", serializer: Optional["SerializerProto"]
    ) -> None:
        self.serializer = serializer
        self.__state = ConnectedState(connection)

    def disconnect(self) -> None:
        self.__state = EmptyConnectionState()

    @override
    async def publish(  # type: ignore[override]
        self,
        cmd: "NatsPublishCommand",
    ) -> "PubAck":
        payload, content_type = encode_message(cmd.body, self.serializer)

        headers_to_send = {
            "content-type": content_type or "",
            **cmd.headers_to_publish(js=True),
        }

        return await self.__state.connection.publish(
            subject=cmd.destination,
            payload=payload,
            headers=headers_to_send,
            stream=cmd.stream,
            timeout=cmd.timeout,
        )

    @override
    async def request(  # type: ignore[override]
        self,
        cmd: "NatsPublishCommand",
    ) -> "Msg":
        payload, content_type = encode_message(cmd.body, self.serializer)

        reply_to = self.__state.connection._nc.new_inbox()
        future: asyncio.Future[Msg] = asyncio.Future()
        sub = await self.__state.connection._nc.subscribe(
            reply_to, future=future, max_msgs=1
        )
        await sub.unsubscribe(limit=1)

        headers_to_send = {
            "content-type": content_type or "",
            "reply_to": reply_to,
            **cmd.headers_to_publish(js=False),
        }

        with anyio.fail_after(cmd.timeout):
            await self.__state.connection.publish(
                subject=cmd.destination,
                payload=payload,
                headers=headers_to_send,
                stream=cmd.stream,
                timeout=cmd.timeout,
            )

            msg = await future

            if (  # pragma: no cover
                msg.headers
                and (
                    msg.headers.get(nats.js.api.Header.STATUS)
                    == nats.aio.client.NO_RESPONDERS_STATUS
                )
            ):
                raise nats.errors.NoRespondersError

            return msg

    @override
    async def publish_batch(
        self,
        cmd: "NatsPublishCommand",
    ) -> None:
        msg = "NATS doesn't support publishing in batches."
        raise FeatureNotSupportedException(msg)


class FakeNatsFastProducer(ProducerProto):
    def connect(self, connection: "Client") -> None:
        raise NotImplementedError

    def disconnect(self) -> None:
        raise NotImplementedError

    @override
    async def publish(  # type: ignore[override]
        self,
        cmd: "NatsPublishCommand",
    ) -> None:
        raise NotImplementedError

    @override
    async def request(  # type: ignore[override]
        self,
        cmd: "NatsPublishCommand",
    ) -> "Msg":
        raise NotImplementedError

    @override
    async def publish_batch(
        self,
        cmd: "NatsPublishCommand",
    ) -> None:
        raise NotImplementedError
