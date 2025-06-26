from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from faststream._internal.configs import (
    SubscriberSpecificationConfig,
    SubscriberUsecaseConfig,
)
from faststream._internal.constants import EMPTY
from faststream.middlewares import AckPolicy
from faststream.rabbit.configs.base import RabbitConfig, RabbitEndpointConfig

if TYPE_CHECKING:
    from faststream._internal.basic_types import AnyDict
    from faststream.rabbit.schemas import Channel


@dataclass(kw_only=True)
class RabbitSubscriberSpecificationConfig(
    RabbitConfig,
    SubscriberSpecificationConfig,
):
    pass


@dataclass(kw_only=True)
class RabbitSubscriberConfig(RabbitEndpointConfig, SubscriberUsecaseConfig):
    consume_args: Optional["AnyDict"] = None
    channel: Optional["Channel"] = None

    _no_ack: bool = field(default_factory=lambda: EMPTY, repr=False)

    @property
    def ack_first(self) -> bool:
        return self.__ack_policy is AckPolicy.ACK_FIRST

    @property
    def ack_policy(self) -> AckPolicy:
        if (policy := self.__ack_policy) is AckPolicy.ACK_FIRST:
            return AckPolicy.DO_NOTHING

        return policy

    @property
    def __ack_policy(self) -> AckPolicy:
        if self._no_ack is not EMPTY and self._no_ack:
            return AckPolicy.DO_NOTHING

        if self._ack_policy is EMPTY:
            return AckPolicy.REJECT_ON_ERROR

        return self._ack_policy
