from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import Dict

from requests import Session

from automated_defi.api_utils import mount_timeout_and_retries
from automated_defi.errors import APIError
from automated_defi.utils import DataclassEncoderMixin


@dataclass
class ApproveParams(DataclassEncoderMixin):
    tokenAddress: str
    """Token address you want to exchange"""


@dataclass
class QuoteParams(DataclassEncoderMixin):
    fromTokenAddress: str
    """Contract address of a token to sell."""
    toTokenAddress: str
    """Contract address of a token to buy."""
    amount: int
    """Amount of a token to sell, set in minimal divisible units e.g.:
    1.00 DAI set as 1000000000000000000
    51.03 USDC set as 51030000
    """


@dataclass
class QuoteResponse:
    """
    The response to a quote request.
    """

    from_amount: int
    """Input amount of fromToken in minimal divisible units."""
    to_amount: int
    """Result amount of toToken in minimal divisible units."""
    estimated_gas: int
    """Estimated amount of the gas limit. Do not use as the gas limit of a transaction."""

    @staticmethod
    def from_json(d: Dict) -> QuoteResponse:
        return QuoteResponse(
            from_amount=int(d["fromTokenAmount"]),
            to_amount=int(d["toTokenAmount"]),
            estimated_gas=int(d["estimatedGas"]),
        )


@dataclass
class SwapParams(DataclassEncoderMixin):
    fromTokenAddress: str
    """Contract address of a token to sell."""
    toTokenAddress: str
    """Contract address of a token to buy."""
    amount: int
    """Amount of a token to sell, set in minimal divisible units e.g.:
    1.00 DAI set as 1000000000000000000
    51.03 USDC set as 51030000
    """
    fromAddress: str
    """The address that calls the 1inch contract."""
    slippage: int
    """Tolerated slippage: min: 0, max: 50

    Limit of price slippage you are willing to accept in percentage, may be
    set with decimals. &slippage=0.5 means 0.5% slippage is acceptable. Low
    values increase chances that transaction will fail, high values increase
    chances of front running. Set values in the range from 0 to 50."""


@dataclass
class ApproveResponse:
    """
    The response of the approve API endpoint.
    """

    to_address: str
    """Transactions will be sent to our contract address."""
    data: str
    """Bytes of call data."""
    value: int
    """Amount of ETH (in wei) will be sent to the contract address."""
    gas_price: int
    """Gas price in wei."""

    @staticmethod
    def from_json(d: Dict) -> ApproveResponse:
        return ApproveResponse(
            to_address=d["to"],
            data=d["data"],
            value=int(d["value"]),
            gas_price=int(d["gasPrice"]),
        )


@dataclass
class SwapResponseTx:
    """
    The response part of interest, under response["tx"].

    Outdated docs (structure and some types found changed by inspecting real responses): https://docs.1inch.io/docs/aggregation-protocol/api/swap-params/#description-of-response-parameters
    """

    from_address: str
    """Transactions will be sent from this address."""
    to_address: str
    """Transactions will be sent to our contract address."""
    data: str
    """Bytes of call data."""
    value: int
    """Amount of ETH (in wei) will be sent to the contract address."""
    gas: int
    """Estimated amount of the gas limit, increase this value by 25%."""
    gas_price: int
    """Gas price in wei."""

    @staticmethod
    def from_json(d: Dict) -> SwapResponseTx:
        return SwapResponseTx(
            from_address=d["from"],
            to_address=d["to"],
            data=d["data"],
            value=int(d["value"]),
            gas=int(d["gas"]),
            gas_price=int(d["gasPrice"]),
        )


@dataclass
class SwapResponse:
    """
    The response.

    Outdated docs (structure and some types found changed by inspecting real responses): https://docs.1inch.io/docs/aggregation-protocol/api/swap-params/#description-of-response-parameters
    """

    tx: SwapResponseTx

    @staticmethod
    def from_json(d: Dict) -> SwapResponse:
        return SwapResponse(
            tx=SwapResponseTx.from_json(d["tx"]),
        )


class OneInchAPI:
    """1inch API

    API Docs: https://docs.1inch.io/docs/aggregation-protocol/api/swap-params/#
    """

    def __init__(self):
        self.api_url = "https://api.1inch.io/v4.0/1"
        self.headers = {
            "Accepts": "application/json",
        }
        self._client = mount_timeout_and_retries(Session())
        self._client.headers.update(self.headers)

    def approve(self, params: ApproveParams) -> ApproveResponse:
        url = f"{self.api_url}/approve/transaction"
        response = self._client.get(url, params=dataclasses.asdict(params))
        if response.status_code != 200:
            raise APIError(
                response.status_code, response.json().get("description", str(response))
            )

        return ApproveResponse.from_json(response.json())

    def quote(self, params: QuoteParams) -> QuoteResponse:
        url = f"{self.api_url}/quote"
        response = self._client.get(url, params=dataclasses.asdict(params))
        if response.status_code != 200:
            raise APIError(
                response.status_code, response.json().get("description", str(response))
            )

        return QuoteResponse.from_json(response.json())

    def swap(self, params: SwapParams) -> SwapResponse:
        url = f"{self.api_url}/swap"
        response = self._client.get(url, params=dataclasses.asdict(params))
        if response.status_code != 200:
            raise APIError(
                response.status_code, response.json().get("description", str(response))
            )

        return SwapResponse.from_json(response.json())
