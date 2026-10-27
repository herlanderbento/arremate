from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from shared.domain.value_objects import ValueObject


@dataclass(slots=True)
class Entity(ABC):
    @property
    @abstractmethod
    def entity_id(self) -> ValueObject:
        raise NotImplementedError()

    def equals(self, other: Any):
        if not isinstance(other, self.__class__):
            return False
        return self.entity_id == other.entity_id


@dataclass(slots=True)
class AggregateRoot(Entity):
    pass
