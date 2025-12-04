from dataclasses import dataclass
from typing import Generic, Optional, Type, TypeVar, Union

from automated_defi.eth import assets
from automated_defi.utils import DataclassEncoderMixin

# allow only types supported by both JSON and Python (named after Python equivalent type)
# exclude float to avoid problems with precision
T = TypeVar("T", bound=Union[str, int, bool, assets.Asset])


@dataclass
class Param(DataclassEncoderMixin, Generic[T]):
    """A variable parameter to a step of a strategy, later provided by the user or left at the default value."""

    type: Type[T]
    """The represented type of this parameter, e.g. `assets.CToken`. Parameters might support parsing from different types into the represented type."""
    key: str
    """the unique key"""
    name: str = ""
    """human readable name"""
    required: bool = True
    default: Optional[T] = None

    @property
    def initial(self) -> Optional[T]:
        return (self.default or self.type()) if self.required else None


@dataclass
class Ref(DataclassEncoderMixin, Generic[T]):
    """A reference to a variable from state to use in a step of a strategy."""

    key: str
    """the state key to use for looking up the value"""
    required: bool = False  # TODO make the default True
    default: Optional[T] = None
    """the default value to use in case the key does not exist in state used for lookup"""
