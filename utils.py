import dataclasses
import json
import re
from datetime import datetime
from decimal import Decimal
from typing import Callable, Iterable, Optional

from hexbytes import HexBytes
from web3.datastructures import AttributeDict

from automated_defi.decimal_utils import fmt


class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if dataclasses.is_dataclass(o):
            return {
                f.metadata.get("key", f.name): getattr(o, f.name)
                for f in dataclasses.fields(o)
            }
        elif isinstance(o, Callable):
            return o.__name__
        elif isinstance(o, Decimal):
            return fmt(o)
        elif isinstance(o, datetime):
            return o.isoformat()
        elif isinstance(o, AttributeDict):
            return o.__dict__
        elif isinstance(o, HexBytes):
            return str(o.hex())
        return super().default(o)


class DataclassEncoderMixin:
    def json(self) -> str:
        return json.dumps(self, cls=EnhancedJSONEncoder)


_first1 = re.compile(r"(.)([A-Z][a-z]+)")
_all2 = re.compile("([a-z0-9])([A-Z])")


def camel_to_snake(name: str) -> str:
    """Convert CamelCase to snake_case

    :param name: name in CamelCase
    :return: name in snake_case
    """
    subbed = _first1.sub(r"\1_\2", name)
    return _all2.sub(r"\1_\2", subbed).lower()


def nested(d: dict, list_of_keys: Iterable):
    if d is None:
        d = {}
    for k in list_of_keys:
        if k not in d:
            d[k] = {}
        d = d[k]
    return d


def merge_dict(
    base: Optional[dict],
    other: Optional[dict],
    merge_value=lambda left, right: right if right is not None else left,
    keep_extra_in_other=True,
) -> dict:
    """Recursively merges `other` into `base`. The hierarchy/nesting of dicts
    from `base` is kept whatever `other` looks like. On the other hand, for
    non-dict values in base (leafs of the hierarchy) values from `other`
    overwrite values in `base`.

    `base` is modified during merge, so pass a deepcopy of `base` if
    modification is undesired.

    Pass your custom `merge_value` function to define how values get merged.

    Set `keep_extra_in_other` to False to only keep keys that appear in `base`.
    """
    base = base or {}
    other = other or {}

    def _merge(base, other):
        for k, value in other.items():
            if k in base:
                if isinstance(base[k], dict) and isinstance(value, dict):
                    _merge(base[k], value)
                if not isinstance(base[k], dict) and not isinstance(value, dict):
                    base[k] = merge_value(base[k], value)
            elif keep_extra_in_other:
                base[k] = value

    _merge(base, other)
    return base


def merge_params(
    base: Optional[dict],
    other: Optional[dict],
) -> dict:
    return merge_dict(
        base,
        other,
        merge_value=lambda left, right: right if type(left) == type(right) else left,
        keep_extra_in_other=False,
    )
