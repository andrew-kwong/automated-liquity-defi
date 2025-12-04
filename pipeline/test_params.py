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
    Case(
        routing_key="eth-rinkeby.compound.2",
    ),
    Case(
        routing_key="eth-rinkeby.compound-reverse.2",
    ),
    Case(
        routing_key="eth-rinkeby.liquity.1",
    ),
    Case(
        routing_key="eth-rinkeby.liquity-exit.1",
    ),
]


@pytest.mark.parametrize("case", testcases, ids=lambda case: str(case))
def test_params(case: Case, snapshot):
    protocol = protocols.by_routing_key[case.routing_key]
    actual = protocol.pipeline.initial_params_json
    assert actual == snapshot
