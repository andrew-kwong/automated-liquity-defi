from dataclasses import dataclass
from enum import Enum

from web3.contract import Contract

from automated_defi.protocol.chain import ETHChain


class ContractType(str, Enum):
    abi: str

    def __new__(cls, value, abi=None):
        obj = str.__new__(cls, [value])
        obj._value_ = value
        obj.abi = abi or value
        return obj

    CTOKEN = "ctoken"
    TOKEN = "token"
    COMPTROLLER = "comptroller"
    COMPTROLLER_IMPL = "comptroller_impl"
    COMPOUND_LENS = "compound_lens"
    PRICE_FEED = "price_feed"
    PRICE_ORACLE_PROXY = "price_oracle_proxy"
    PRICE_ORACLE = "price_oracle"
    UNISWAP_ANCHORED_VIEW = "uniswap_anchored_view"
    WRAPPED_ETH = "WETH"
    # Liquity Functions
    POOL = "stability_pool"
    COMMUNITY = "community_issuance"


@dataclass
class ContractSpec:
    name: str
    type: ContractType
    address: str


@dataclass
class BaseContract:
    name: str
    type: ContractType
    chain: ETHChain
    contract: Contract

    @property
    def address(self):
        return self.contract.address

    def __str__(self) -> str:
        return f"{self.name}"
