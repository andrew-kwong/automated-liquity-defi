import importlib.resources as pkg_resources
import json

import pytest

from . import __testdata__
from .one_inch import SwapParams, SwapResponse


class TestSwapParams:
    testcases = [
        SwapParams(
            fromTokenAddress="0x949D48EcA67b17269629c7194F4b727d4Ef9E5d6",
            toTokenAddress="0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
            amount=3000000000000000000,
            fromAddress="0x8b187EA19C93091a4D6B426b71871648182b5Fac",
            slippage=10,
        ),
    ]

    @pytest.mark.parametrize("case", testcases, ids=lambda case: str(case))
    def test_print_pipeline(self, case: SwapParams, snapshot):
        assert case.json() == snapshot


class TestSwapResponse:
    testcases = [
        "swap_response.json",
    ]

    @pytest.mark.parametrize("case", testcases, ids=lambda case: str(case))
    def test_print_pipeline(self, case: str, snapshot):
        lines = json.loads(pkg_resources.read_text(__testdata__, case))
        assert SwapResponse.from_json(lines) == snapshot
