from decimal import Decimal
from typing import NamedTuple

import pytest

from automated_defi.decimal_utils import fmt


class Case(NamedTuple):
    inp: Decimal
    exp: str


testcases = [
    Case(
        inp=Decimal("0.000"),
        exp="0.000",
    ),
    Case(
        inp=Decimal("00.000"),
        exp="0.000",
    ),
    Case(
        inp=Decimal("1.2345"),
        exp="1.2345",
    ),
    Case(
        inp=Decimal("1.550") + Decimal("1.45"),
        exp="3.000",
    ),
    Case(
        inp=Decimal("2.00") * Decimal("6.00"),
        exp="12.0000",
    ),
    Case(
        inp=Decimal("100_000.000"),
        exp="100000.000",
    ),
]


@pytest.mark.parametrize("case", testcases, ids=lambda case: str(case))
def test_fmt(case: Case):
    formatted = fmt(case.inp)
    assert formatted == case.exp
    assert Decimal(formatted) == case.inp
