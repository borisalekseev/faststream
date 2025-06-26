import warnings
from typing import TYPE_CHECKING, TypeAlias, Union

from faststream._internal.constants import EMPTY
from faststream._internal.endpoint.subscriber.call_item import (
    CallsCollection,
)
from faststream.exceptions import SetupError
from faststream.middlewares import AckPolicy
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
    StreamBatchSubscriber,
    StreamConcurrentSubscriber,
    StreamSubscriber,
)

if TYPE_CHECKING:
    from faststream.redis.configs import RedisBrokerConfig

SubsciberType: TypeAlias = (
    ChannelSubscriber
    | StreamBatchSubscriber
    | StreamSubscriber
    | ListBatchSubscriber
    | ListSubscriber
    | ChannelConcurrentSubscriber
    | ListConcurrentSubscriber
    | StreamConcurrentSubscriber
)


def create_subscriber(
    *,
    channel: Union["PubSub", str, None],
    list: Union["ListSub", str, None],
    stream: Union["StreamSub", str, None],
    # Subscriber args
    ack_policy: "AckPolicy",
    no_ack: bool,
    config: "RedisBrokerConfig",
    no_reply: bool = False,
    # AsyncAPI args
    title_: str | None = None,
    description_: str | None = None,
    include_in_schema: bool = True,
    max_workers: int = 1,
) -> SubsciberType:
    _validate_input_for_misconfigure(
        channel=channel,
        list=list,
        stream=stream,
        ack_policy=ack_policy,
        no_ack=no_ack,
        max_workers=max_workers,
    )

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

    calls = CallsCollection()

    specification: RedisSubscriberSpecification
    if subscriber_config.channel_sub:
        specification = ChannelSubscriberSpecification(
            config, specification_config, calls, channel=subscriber_config.channel_sub,
        )

        subscriber_config._ack_policy = AckPolicy.DO_NOTHING

        if max_workers > 1:
            return ChannelConcurrentSubscriber(
                subscriber_config,
                specification, calls,
                max_workers=max_workers,
            )

        return ChannelSubscriber(subscriber_config,
                specification, calls)

    if subscriber_config.stream_sub:
        specification = StreamSubscriberSpecification(
            config, specification_config, calls, stream_sub=subscriber_config.stream_sub
        )

        if subscriber_config.stream_sub.batch:
            return StreamBatchSubscriber(subscriber_config,
                specification, calls)

        if max_workers > 1:
            return StreamConcurrentSubscriber(
                subscriber_config,
                specification, calls,
                max_workers=max_workers,
            )

        return StreamSubscriber(subscriber_config,
                specification, calls)

    if subscriber_config.list_sub:
        specification = ListSubscriberSpecification(
            config, specification_config, calls, list_sub=subscriber_config.list_sub
        )

        if subscriber_config.list_sub.batch:
            return ListBatchSubscriber(subscriber_config,
                specification, calls)

        if max_workers > 1:
            return ListConcurrentSubscriber(
                subscriber_config,
                specification, calls,
                max_workers=max_workers,
            )

        return ListSubscriber(subscriber_config,
                specification, calls)

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
            "`no_ack` option was deprecated in prior to `ack_policy=AckPolicy.DO_NOTHING`. Scheduled to remove in 0.7.0",
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
