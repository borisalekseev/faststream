from dataclasses import dataclass, field

from faststream._internal.configs import (
    SubscriberSpecificationConfig,
    SubscriberUsecaseConfig,
)
from faststream._internal.constants import EMPTY
from faststream.middlewares.acknowledgement.conf import AckPolicy
from faststream.redis.configs import RedisBrokerConfig
from faststream.redis.schemas import ListSub, PubSub, StreamSub


class RedisSubscriberSpecificationConfig(SubscriberSpecificationConfig):
    pass


@dataclass(kw_only=True)
class RedisSubscriberConfig(SubscriberUsecaseConfig):
    _outer_config: RedisBrokerConfig

    list_sub: ListSub | None = field(default=None, repr=False)
    channel_sub: PubSub | None = field(default=None, repr=False)
    stream_sub: StreamSub | None = field(default=None, repr=False)

    _no_ack: bool = field(default_factory=lambda: EMPTY, repr=False)

    @property
    def ack_policy(self) -> AckPolicy:
        if self._no_ack is not EMPTY and self._no_ack:
            return AckPolicy.DO_NOTHING

        if self.list_sub:
            return AckPolicy.DO_NOTHING

        if self.channel_sub:
            return AckPolicy.DO_NOTHING

        if self.stream_sub and (self.stream_sub.no_ack or not self.stream_sub.group):
            return AckPolicy.DO_NOTHING

        if self._ack_policy is EMPTY:
            return AckPolicy.REJECT_ON_ERROR

        return self._ack_policy
