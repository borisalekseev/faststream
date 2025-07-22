import warnings
<<<<<<< HEAD
from typing import TYPE_CHECKING, Any, TypeAlias, Union
=======
from typing import TYPE_CHECKING, Iterable, Optional, Sequence, Type, Union

from typing_extensions import TypeAlias
>>>>>>> df6e51cc238d7ff01b2867aea52ed97faf3ac6f2

from faststream._internal.constants import EMPTY
from faststream._internal.endpoint.subscriber.call_item import CallsCollection
from faststream.exceptions import SetupError
<<<<<<< HEAD
from faststream.middlewares import AckPolicy
=======
from faststream.redis.parser import JSONMessageFormat
>>>>>>> df6e51cc238d7ff01b2867aea52ed97faf3ac6f2
from faststream.redis.schemas import INCORRECT_SETUP_MSG, ListSub, PubSub, StreamSub
from faststream.redis.schemas.proto import validate_options

from .config import RedisSubscriberConfig, RedisSubscriberSpecificationConfig
from .specification import (
    ChannelSubscriberSpecification,
    ListSubscriberSpecification,
    RedisSubscriberSpecification,
    StreamSubscriberSpecification,
)
from .usecases import (
    ChannelConcurrentSubscriber,
    ChannelSubscriber,
    ListBatchSubscriber,
    ListConcurrentSubscriber,
    ListSubscriber,
    LogicSubscriber,
    StreamBatchSubscriber,
    StreamConcurrentSubscriber,
    StreamSubscriber,
)

if TYPE_CHECKING:
    from faststream.redis.configs import RedisBrokerConfig

<<<<<<< HEAD
SubscriberType: TypeAlias = LogicSubscriber
=======
    from faststream.broker.types import BrokerMiddleware
    from faststream.redis.message import UnifyRedisDict
    from faststream.redis.parser import MessageFormat

SubsciberType: TypeAlias = Union[
    "AsyncAPIChannelSubscriber",
    "AsyncAPIStreamBatchSubscriber",
    "AsyncAPIStreamSubscriber",
    "AsyncAPIListBatchSubscriber",
    "AsyncAPIListSubscriber",
]
>>>>>>> df6e51cc238d7ff01b2867aea52ed97faf3ac6f2


def create_subscriber(
    *,
    channel: Union["PubSub", str, None],
    list: Union["ListSub", str, None],
    stream: Union["StreamSub", str, None],
    # Subscriber args
<<<<<<< HEAD
    ack_policy: "AckPolicy",
    no_ack: bool,
    config: "RedisBrokerConfig",
=======
    message_format: Type["MessageFormat"],
    no_ack: bool = False,
>>>>>>> df6e51cc238d7ff01b2867aea52ed97faf3ac6f2
    no_reply: bool = False,
    # AsyncAPI args
    title_: str | None = None,
    description_: str | None = None,
    include_in_schema: bool = True,
    max_workers: int = 1,
) -> SubscriberType:
    _validate_input_for_misconfigure(
        channel=channel,
        list=list,
        stream=stream,
        ack_policy=ack_policy,
        no_ack=no_ack,
        max_workers=max_workers,
    )

<<<<<<< HEAD
    subscriber_config = RedisSubscriberConfig(
        channel_sub=PubSub.validate(channel),
        list_sub=ListSub.validate(list),
        stream_sub=StreamSub.validate(stream),
        no_reply=no_reply,
        _outer_config=config,
        _ack_policy=ack_policy,
    )

    specification_config = RedisSubscriberSpecificationConfig(
        title_=title_,
        description_=description_,
        include_in_schema=include_in_schema,
    )

    calls = CallsCollection[Any]()

    specification: RedisSubscriberSpecification
    if subscriber_config.channel_sub:
        specification = ChannelSubscriberSpecification(
            config,
            specification_config,
            calls,
            channel=subscriber_config.channel_sub,
        )

        subscriber_config._ack_policy = AckPolicy.MANUAL

        if max_workers > 1:
            return ChannelConcurrentSubscriber(
                subscriber_config,
                specification,
                calls,
                max_workers=max_workers,
            )

        return ChannelSubscriber(subscriber_config, specification, calls)

    if subscriber_config.stream_sub:
        specification = StreamSubscriberSpecification(
            config,
            specification_config,
            calls,
            stream_sub=subscriber_config.stream_sub,
        )

        if subscriber_config.stream_sub.batch:
            return StreamBatchSubscriber(subscriber_config, specification, calls)

        if max_workers > 1:
            return StreamConcurrentSubscriber(
                subscriber_config,
                specification,
                calls,
                max_workers=max_workers,
=======
    if message_format == JSONMessageFormat:
        warnings.warn(
            "JSONMessageFormat has been deprecated and will be removed in version 0.7.0 "
            "Instead, use BinaryMessageFormatV1 when creating subscriber",
            category=DeprecationWarning,
            stacklevel=3,
        )

    if (channel_sub := PubSub.validate(channel)) is not None:
        return AsyncAPIChannelSubscriber(
            channel=channel_sub,
            # basic args
            message_format=message_format,
            no_ack=no_ack,
            no_reply=no_reply,
            retry=retry,
            broker_dependencies=broker_dependencies,
            broker_middlewares=broker_middlewares,
            # AsyncAPI args
            title_=title_,
            description_=description_,
            include_in_schema=include_in_schema,
        )

    elif (stream_sub := StreamSub.validate(stream)) is not None:
        if stream_sub.batch:
            return AsyncAPIStreamBatchSubscriber(
                stream=stream_sub,
                # basic args
                message_format=message_format,
                no_ack=no_ack,
                no_reply=no_reply,
                retry=retry,
                broker_dependencies=broker_dependencies,
                broker_middlewares=broker_middlewares,
                # AsyncAPI args
                title_=title_,
                description_=description_,
                include_in_schema=include_in_schema,
            )
        else:
            return AsyncAPIStreamSubscriber(
                stream=stream_sub,
                # basic args
                message_format=message_format,
                no_ack=no_ack,
                no_reply=no_reply,
                retry=retry,
                broker_dependencies=broker_dependencies,
                broker_middlewares=broker_middlewares,
                # AsyncAPI args
                title_=title_,
                description_=description_,
                include_in_schema=include_in_schema,
            )

    elif (list_sub := ListSub.validate(list)) is not None:
        if list_sub.batch:
            return AsyncAPIListBatchSubscriber(
                list=list_sub,
                # basic args
                message_format=message_format,
                no_ack=no_ack,
                no_reply=no_reply,
                retry=retry,
                broker_dependencies=broker_dependencies,
                broker_middlewares=broker_middlewares,
                # AsyncAPI args
                title_=title_,
                description_=description_,
                include_in_schema=include_in_schema,
            )
        else:
            return AsyncAPIListSubscriber(
                list=list_sub,
                # basic args
                message_format=message_format,
                no_ack=no_ack,
                no_reply=no_reply,
                retry=retry,
                broker_dependencies=broker_dependencies,
                broker_middlewares=broker_middlewares,
                # AsyncAPI args
                title_=title_,
                description_=description_,
                include_in_schema=include_in_schema,
>>>>>>> df6e51cc238d7ff01b2867aea52ed97faf3ac6f2
            )

        return StreamSubscriber(subscriber_config, specification, calls)

    if subscriber_config.list_sub:
        specification = ListSubscriberSpecification(
            config,
            specification_config,
            calls,
            list_sub=subscriber_config.list_sub,
        )

        if subscriber_config.list_sub.batch:
            return ListBatchSubscriber(subscriber_config, specification, calls)

        if max_workers > 1:
            return ListConcurrentSubscriber(
                subscriber_config,
                specification,
                calls,
                max_workers=max_workers,
            )

        return ListSubscriber(subscriber_config, specification, calls)

    raise SetupError(INCORRECT_SETUP_MSG)


def _validate_input_for_misconfigure(
    *,
    channel: Union["PubSub", str, None],
    list: Union["ListSub", str, None],
    stream: Union["StreamSub", str, None],
    ack_policy: AckPolicy,
    no_ack: bool,
    max_workers: int,
) -> None:
    validate_options(channel=channel, list=list, stream=stream)

    if no_ack is not EMPTY:
        warnings.warn(
            "`no_ack` option was deprecated in prior to `ack_policy=AckPolicy.MANUAL`. Scheduled to remove in 0.7.0",
            category=DeprecationWarning,
            stacklevel=4,
        )

        if ack_policy is not EMPTY:
            msg = "You can't use deprecated `no_ack` and `ack_policy` simultaneously. Please, use `ack_policy` only."
            raise SetupError(msg)

    if stream and no_ack and max_workers > 1:
        msg = "Max workers not work with manual no_ack mode."
        raise SetupError(msg)

    if ack_policy is not EMPTY:
        if channel:
            warnings.warn(
                "You can't use acknowledgement policy with PubSub subscriber.",
                RuntimeWarning,
                stacklevel=4,
            )

        if list:
            warnings.warn(
                "You can't use acknowledgement policy with List subscriber.",
                RuntimeWarning,
                stacklevel=4,
            )
