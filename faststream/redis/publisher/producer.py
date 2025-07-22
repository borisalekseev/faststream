<<<<<<< HEAD
from typing import TYPE_CHECKING, Any, Optional, cast
=======
from typing import TYPE_CHECKING, Any, Optional, Type
>>>>>>> df6e51cc238d7ff01b2867aea52ed97faf3ac6f2

import anyio
from typing_extensions import override

from faststream._internal.endpoint.utils import resolve_custom_func
from faststream._internal.producer import ProducerProto
from faststream._internal.utils.nuid import NUID
from faststream.redis.message import DATA_KEY
<<<<<<< HEAD
from faststream.redis.parser import RawMessage, RedisPubSubParser
from faststream.redis.response import DestinationType, RedisPublishCommand
=======
from faststream.redis.parser import JSONMessageFormat, MessageFormat, RedisPubSubParser
from faststream.redis.schemas import INCORRECT_SETUP_MSG
from faststream.utils.functions import timeout_scope
from faststream.utils.nuid import NUID
>>>>>>> df6e51cc238d7ff01b2867aea52ed97faf3ac6f2

if TYPE_CHECKING:
    from fast_depends.library.serializer import SerializerProto

    from faststream._internal.types import AsyncCallable, CustomCallable
    from faststream.redis.configs import ConnectionState


class RedisFastProducer(ProducerProto[RedisPublishCommand]):
    """A class to represent a Redis producer."""

    _decoder: "AsyncCallable"
    _parser: "AsyncCallable"

    def __init__(
        self,
        connection: "ConnectionState",
        parser: Optional["CustomCallable"],
        decoder: Optional["CustomCallable"],
        message_format: Type["MessageFormat"] = JSONMessageFormat,
    ) -> None:
        self._connection = connection
<<<<<<< HEAD
        self.serializer: SerializerProto | None = None
=======
        self.message_format = message_format
>>>>>>> df6e51cc238d7ff01b2867aea52ed97faf3ac6f2

        default = RedisPubSubParser(message_format=message_format)
        self._parser = resolve_custom_func(
            parser,
            default.parse_message,
        )
        self._decoder = resolve_custom_func(
            decoder,
            default.decode_message,
        )

    @override
<<<<<<< HEAD
    async def publish(self, cmd: "RedisPublishCommand") -> int | bytes:
        msg = RawMessage.encode(
            message=cmd.body,
            reply_to=cmd.reply_to,
            headers=cmd.headers,
            correlation_id=cmd.correlation_id or "",
            serializer=self.serializer,
=======
    async def publish(  # type: ignore[override]
        self,
        message: "SendableMessage",
        *,
        correlation_id: str,
        channel: Optional[str] = None,
        list: Optional[str] = None,
        stream: Optional[str] = None,
        maxlen: Optional[int] = None,
        headers: Optional["AnyDict"] = None,
        reply_to: str = "",
        rpc: bool = False,
        rpc_timeout: Optional[float] = 30.0,
        raise_timeout: bool = False,
        pipeline: Optional["Pipeline[bytes]"] = None,
        message_format: Optional[Type["MessageFormat"]] = None,
    ) -> Optional[Any]:
        if not any((channel, list, stream)):
            raise SetupError(INCORRECT_SETUP_MSG)

        if pipeline is not None and rpc is True:
            raise RuntimeError(
                "You cannot use both rpc and pipeline arguments at the same time: "
                "select only one delivery mechanism."
            )

        psub: Optional[PubSub] = None
        if rpc:
            if reply_to:
                raise WRONG_PUBLISH_ARGS
            nuid = NUID()
            rpc_nuid = str(nuid.next(), "utf-8")
            reply_to = rpc_nuid
            psub = self._connection.pubsub()
            await psub.subscribe(reply_to)

        msg = (message_format or self.message_format).encode(
            message=message,
            reply_to=reply_to,
            headers=headers,
            correlation_id=correlation_id,
>>>>>>> df6e51cc238d7ff01b2867aea52ed97faf3ac6f2
        )

        return await self.__publish(msg, cmd)

    @override
<<<<<<< HEAD
    async def request(self, cmd: "RedisPublishCommand") -> "Any":
=======
    async def request(  # type: ignore[override]
        self,
        message: "SendableMessage",
        *,
        correlation_id: str,
        channel: Optional[str] = None,
        list: Optional[str] = None,
        stream: Optional[str] = None,
        maxlen: Optional[int] = None,
        headers: Optional["AnyDict"] = None,
        timeout: Optional[float] = 30.0,
        message_format: Optional[Type["MessageFormat"]] = None,
    ) -> "Any":
        if not any((channel, list, stream)):
            raise SetupError(INCORRECT_SETUP_MSG)

>>>>>>> df6e51cc238d7ff01b2867aea52ed97faf3ac6f2
        nuid = NUID()
        reply_to = str(nuid.next(), "utf-8")
        psub = self._connection.client.pubsub()
        await psub.subscribe(reply_to)

<<<<<<< HEAD
        msg = RawMessage.encode(
            message=cmd.body,
=======
        msg = (message_format or self.message_format).encode(
            message=message,
>>>>>>> df6e51cc238d7ff01b2867aea52ed97faf3ac6f2
            reply_to=reply_to,
            headers=cmd.headers,
            correlation_id=cmd.correlation_id or "",
            serializer=self.serializer,
        )

        await self.__publish(msg, cmd)

        with anyio.fail_after(cmd.timeout) as scope:
            # skip subscribe message
            await psub.get_message(
                ignore_subscribe_messages=True,
                timeout=cmd.timeout or 0.0,
            )

            # get real response
            response_msg = await psub.get_message(
                ignore_subscribe_messages=True,
                timeout=cmd.timeout or 0.0,
            )

        await psub.unsubscribe()
        await psub.aclose()  # type: ignore[attr-defined]

        if scope.cancel_called:
            raise TimeoutError

        return response_msg

<<<<<<< HEAD
    @override
    async def publish_batch(self, cmd: "RedisPublishCommand") -> int:
        batch = [
            RawMessage.encode(
=======
    async def publish_batch(
        self,
        *msgs: "SendableMessage",
        list: str,
        correlation_id: str,
        headers: Optional["AnyDict"] = None,
        pipeline: Optional["Pipeline[bytes]"] = None,
        message_format: Optional[Type["MessageFormat"]] = None,
    ) -> None:
        mf = message_format or self.message_format
        batch = (
            mf.encode(
>>>>>>> df6e51cc238d7ff01b2867aea52ed97faf3ac6f2
                message=msg,
                correlation_id=cmd.correlation_id or "",
                reply_to=cmd.reply_to,
                headers=cmd.headers,
                serializer=self.serializer,
            )
            for msg in cmd.batch_bodies
        ]

        connection = cmd.pipeline or self._connection.client
        return await connection.rpush(cmd.destination, *batch)

    async def __publish(
        self,
        msg: bytes,
        cmd: "RedisPublishCommand",
    ) -> int | bytes:
        connection = cmd.pipeline or self._connection.client

        if cmd.destination_type is DestinationType.Channel:
            return await connection.publish(cmd.destination, msg)

        if cmd.destination_type is DestinationType.List:
            return await connection.rpush(cmd.destination, msg)

        if cmd.destination_type is DestinationType.Stream:
            return cast(
                "bytes",
                await connection.xadd(
                    name=cmd.destination,
                    fields={DATA_KEY: msg},
                    maxlen=cmd.maxlen,
                ),
            )

        error_msg = "unreachable"
        raise AssertionError(error_msg)

    def connect(self, serializer: Optional["SerializerProto"] = None) -> None:
        self.serializer = serializer
