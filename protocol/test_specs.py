import json
from typing import NamedTuple

import pytest

from automated_defi.protocol.specs import Protocols

protocols = Protocols()


class Case(NamedTuple):
    routing_key: str

    def __str__(self) -> str:
        return self.routing_key


testcases = [
    Case(
        routing_key="eth.balance.1",
    ),
    Case(
        routing_key="eth.transfer.1",
    ),
]


@pytest.mark.parametrize("case", testcases, ids=lambda case: str(case))
def test_json(case: Case, snapshot):
    protocol = protocols.by_routing_key[case.routing_key]
    output = protocol.json()
    loaded_dict = json.loads(output)
    assert loaded_dict == snapshot
