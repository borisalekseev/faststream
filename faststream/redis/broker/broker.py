import logging
from collections.abc import Iterable, Mapping, Sequence
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Optional,
    TypeAlias,
    Union,
)
from urllib.parse import urlparse

import anyio
from anyio import move_on_after
from redis.asyncio.connection import (
    Connection,
    DefaultParser,
    Encoder,
    parse_url,
)
from redis.exceptions import ConnectionError
from typing_extensions import Doc, overload, override

from faststream._internal.broker import BrokerUsecase
from faststream._internal.constants import EMPTY
from faststream._internal.di import FastDependsConfig
from faststream.message import gen_cor_id
from faststream.redis.configs import ConnectionState, RedisBrokerConfig
from faststream.redis.message import UnifyRedisDict
from faststream.redis.publisher.producer import RedisFastProducer
from faststream.redis.response import RedisPublishCommand
from faststream.redis.security import parse_security
from faststream.response.publish_type import PublishType
from faststream.specification.schema import BrokerSpec

from .logging import make_redis_logger_state
from .registrator import RedisRegistrator

if TYPE_CHECKING:
    from types import TracebackType

    from fast_depends.dependencies import Dependant
    from fast_depends.library.serializer import SerializerProto
    from redis.asyncio.client import Pipeline, Redis
    from redis.asyncio.connection import BaseParser
    from typing_extensions import TypedDict

    from faststream._internal.basic_types import (
        AnyDict,
        LoggerProto,
        SendableMessage,
    )
    from faststream._internal.broker.abc_broker import Registrator
    from faststream._internal.types import (
        BrokerMiddleware,
        CustomCallable,
    )
    from faststream.redis.message import BaseMessage, RedisMessage
    from faststream.security import BaseSecurity
    from faststream.specification.schema.extra import Tag, TagDict

    class RedisInitKwargs(TypedDict, total=False):
        host: str | None
        port: str | int | None
        db: str | int | None
        client_name: str | None
        health_check_interval: float | None
        max_connections: int | None
        socket_timeout: float | None
        socket_connect_timeout: float | None
        socket_read_size: int | None
        socket_keepalive: bool | None
        socket_keepalive_options: Mapping[int, int | bytes] | None
        socket_type: int | None
        retry_on_timeout: bool | None
        encoding: str | None
        encoding_errors: str | None
        parser_class: type["BaseParser"] | None
        connection_class: type["Connection"] | None
        encoder_class: type["Encoder"] | None


Channel: TypeAlias = str


class RedisBroker(
    RedisRegistrator,
    BrokerUsecase[UnifyRedisDict, "Redis[bytes]"],
):
    """Redis broker."""

    url: str
    _producer: "RedisFastProducer"

    def __init__(
        self,
        url: str = "redis://localhost:6379",
        *,
        host: str = EMPTY,
        port: str | int = EMPTY,
        db: str | int = EMPTY,
        connection_class: type["Connection"] = EMPTY,
        client_name: str | None = None,
        health_check_interval: float = 0,
        max_connections: int | None = None,
        socket_timeout: float | None = None,
        socket_connect_timeout: float | None = None,
        socket_read_size: int = 65536,
        socket_keepalive: bool = False,
        socket_keepalive_options: Mapping[int, int | bytes] | None = None,
        socket_type: int = 0,
        retry_on_timeout: bool = False,
        encoding: str = "utf-8",
        encoding_errors: str = "strict",
        parser_class: type["BaseParser"] = DefaultParser,
        encoder_class: type["Encoder"] = Encoder,
        # broker args
        graceful_timeout: Annotated[
            float | None,
            Doc(
                "Graceful shutdown timeout. Broker waits for all running subscribers completion before shut down.",
            ),
        ] = 15.0,
        decoder: Annotated[
            Optional["CustomCallable"],
            Doc("Custom decoder object."),
        ] = None,
        parser: Annotated[
            Optional["CustomCallable"],
            Doc("Custom parser object."),
        ] = None,
        dependencies: Annotated[
            Iterable["Dependant"],
            Doc("Dependencies to apply to all broker subscribers."),
        ] = (),
        middlewares: Annotated[
            Sequence["BrokerMiddleware[BaseMessage]"],
            Doc("Middlewares to apply to all broker publishers/subscribers."),
        ] = (),
        routers: Annotated[
            Sequence["Registrator[BaseMessage]"],
            Doc("Routers to apply to broker."),
        ] = (),
        # AsyncAPI args
        security: Annotated[
            Optional["BaseSecurity"],
            Doc(
                "Security options to connect broker and generate AsyncAPI server security information.",
            ),
        ] = None,
        specification_url: Annotated[
            str | None,
            Doc("AsyncAPI hardcoded server addresses. Use `servers` if not specified."),
        ] = None,
        protocol: Annotated[
            str | None,
            Doc("AsyncAPI server protocol."),
        ] = None,
        protocol_version: Annotated[
            str | None,
            Doc("AsyncAPI server protocol version."),
        ] = "custom",
        description: Annotated[
            str | None,
            Doc("AsyncAPI server description."),
        ] = None,
        tags: Annotated[
            Iterable[Union["Tag", "TagDict"]],
            Doc("AsyncAPI server tags."),
        ] = (),
        # logging args
        logger: Annotated[
            Optional["LoggerProto"],
            Doc("User specified logger to pass into Context and log service messages."),
        ] = EMPTY,
        log_level: Annotated[
            int,
            Doc("Service messages log level."),
        ] = logging.INFO,
        # FastDepends args
        apply_types: Annotated[
            bool,
            Doc("Whether to use FastDepends or not."),
        ] = True,
        serializer: Optional["SerializerProto"] = EMPTY,
    ) -> None:
        if specification_url is None:
            specification_url = url

        if protocol is None:
            url_kwargs = urlparse(specification_url)
            protocol = url_kwargs.scheme

        connection_options = _resolve_url_options(
            url,
            security=security,
            host=host,
            port=port,
            db=db,
            client_name=client_name,
            health_check_interval=health_check_interval,
            max_connections=max_connections,
            socket_timeout=socket_timeout,
            socket_connect_timeout=socket_connect_timeout,
            socket_read_size=socket_read_size,
            socket_keepalive=socket_keepalive,
            socket_keepalive_options=socket_keepalive_options,
            socket_type=socket_type,
            retry_on_timeout=retry_on_timeout,
            encoding=encoding,
            encoding_errors=encoding_errors,
            parser_class=parser_class,
            connection_class=connection_class,
            encoder_class=encoder_class,
        )

        connection_state = ConnectionState(connection_options)

        super().__init__(
            **connection_options,
            routers=routers,
            config=RedisBrokerConfig(
                connection=connection_state,
                producer=RedisFastProducer(
                    connection=connection_state,
                    parser=parser,
                    decoder=decoder,
                ),
                # both args
                broker_middlewares=middlewares,
                broker_parser=parser,
                broker_decoder=decoder,
                logger=make_redis_logger_state(
                    logger=logger,
                    log_level=log_level,
                ),
                fd_config=FastDependsConfig(
                    use_fastdepends=apply_types,
                    serializer=serializer,
                ),
                # subscriber args
                broker_dependencies=dependencies,
                graceful_timeout=graceful_timeout,
                extra_context={
                    "broker": self,
                },
            ),
            specification=BrokerSpec(
                description=description,
                url=[specification_url],
                protocol=protocol,
                protocol_version=protocol_version,
                security=security,
                tags=tags,
            ),
        )

    @override
    async def _connect(self) -> "Redis[bytes]":
        await self.config.connect()
        return self.config.connection.client

    async def close(
        self,
        exc_type: type[BaseException] | None = None,
        exc_val: BaseException | None = None,
        exc_tb: Optional["TracebackType"] = None,
    ) -> None:
        await super().close(exc_type, exc_val, exc_tb)
        await self.config.disconnect()
        self._connection = None

    async def start(self) -> None:
        await self.connect()
        await super().start()

    @overload
    async def publish(
        self,
        message: "SendableMessage" = None,
        channel: str | None = None,
        *,
        reply_to: str = "",
        headers: Optional["AnyDict"] = None,
        correlation_id: str | None = None,
        list: str | None = None,
        stream: None = None,
        maxlen: int | None = None,
    ) -> int: ...

    @overload
    async def publish(
        self,
        message: "SendableMessage" = None,
        channel: str | None = None,
        *,
        reply_to: str = "",
        headers: Optional["AnyDict"] = None,
        correlation_id: str | None = None,
        list: str | None = None,
        stream: str,
        maxlen: int | None = None,
    ) -> bytes: ...

    @override
    async def publish(
        self,
        message: "SendableMessage" = None,
        channel: str | None = None,
        *,
        reply_to: str = "",
        headers: Optional["AnyDict"] = None,
        correlation_id: str | None = None,
        list: str | None = None,
        stream: str | None = None,
        maxlen: int | None = None,
        pipeline: Optional["Pipeline[bytes]"] = None,
    ) -> int | bytes:
        """Publish message directly.

        This method allows you to publish a message in a non-AsyncAPI-documented way.
        It can be used in other frameworks or to publish messages at specific intervals.

        Args:
            message:
                Message body to send.
            channel:
                Redis PubSub object name to send message.
            reply_to:
                Reply message destination PubSub object name.
            headers:
                Message headers to store metainformation.
            correlation_id:
                Manual message correlation_id setter. correlation_id is a useful option to trace messages.
            list:
                Redis List object name to send message.
            stream:
                Redis Stream object name to send message.
            maxlen:
                Redis Stream maxlen publish option. Remove eldest message if maxlen exceeded.
            pipeline:
                Redis pipeline to use for publishing messages.

        Returns:
            int: The result of the publish operation, typically the number of messages published.
        """
        cmd = RedisPublishCommand(
            message,
            correlation_id=correlation_id or gen_cor_id(),
            channel=channel,
            list=list,
            stream=stream,
            maxlen=maxlen,
            reply_to=reply_to,
            headers=headers,
            _publish_type=PublishType.PUBLISH,
            pipeline=pipeline,
        )

        return await super()._basic_publish(cmd, producer=self.config.producer)

    @override
    async def request(  # type: ignore[override]
        self,
        message: "SendableMessage",
        channel: str | None = None,
        *,
        list: str | None = None,
        stream: str | None = None,
        maxlen: int | None = None,
        correlation_id: str | None = None,
        headers: Optional["AnyDict"] = None,
        timeout: float | None = 30.0,
    ) -> "RedisMessage":
        cmd = RedisPublishCommand(
            message,
            correlation_id=correlation_id or gen_cor_id(),
            channel=channel,
            list=list,
            stream=stream,
            maxlen=maxlen,
            headers=headers,
            timeout=timeout,
            _publish_type=PublishType.REQUEST,
        )
        msg: RedisMessage = await super()._basic_request(
            cmd, producer=self.config.producer
        )
        return msg

    async def publish_batch(
        self,
        *messages: "SendableMessage",
        list: str,
        correlation_id: str | None = None,
        reply_to: str = "",
        headers: Optional["AnyDict"] = None,
        pipeline: Optional["Pipeline[bytes]"] = None,
    ) -> int:
        """Publish multiple messages to Redis List by one request.

        Args:
            *messages: Messages bodies to send.
            list: Redis List object name to send messages.
            correlation_id: Manual message **correlation_id** setter. **correlation_id** is a useful option to trace messages.
            reply_to: Reply message destination PubSub object name.
            headers: Message headers to store metainformation.
            pipeline: Redis pipeline to use for publishing messages.

        Returns:
            int: The result of the batch publish operation.
        """
        cmd = RedisPublishCommand(
            *messages,
            list=list,
            reply_to=reply_to,
            headers=headers,
            correlation_id=correlation_id or gen_cor_id(),
            _publish_type=PublishType.PUBLISH,
            pipeline=pipeline,
        )

        return await self._basic_publish_batch(cmd, producer=self.config.producer)

    @override
    async def ping(self, timeout: float | None) -> bool:
        sleep_time = (timeout or 10) / 10

        with move_on_after(timeout) as cancel_scope:
            if self._connection is None:
                return False

            while True:
                if cancel_scope.cancel_called:
                    return False

                try:
                    if await self._connection.ping():
                        return True

                except ConnectionError:
                    pass

                await anyio.sleep(sleep_time)

        return False


def _resolve_url_options(
    url: str,
    *,
    security: Optional["BaseSecurity"],
    **kwargs: Any,
) -> "AnyDict":
    return {
        **dict(parse_url(url)),
        **parse_security(security),
        **{k: v for k, v in kwargs.items() if v is not EMPTY},
    }
