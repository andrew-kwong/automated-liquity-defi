import importlib.resources as pkg_resources
import json
from collections import defaultdict
from functools import cached_property
from typing import Dict, List, Set, Tuple

from eth_typing import ChecksumAddress

from automated_defi.eth import abi
from automated_defi.eth.contract import BaseContract, ContractSpec, ContractType
from automated_defi.eth.contracts import (
    CommunityIssuanceContract,
    CompoundLensContract,
    ComptrollerContract,
    CTokenContract,
    ERC20Contract,
    PriceFeedContract,
    PriceOracleContract,
    PriceOracleProxyContract,
    StabilityPoolContract,
    TokenContract,
    UniswapAnchoredViewContract,
    WrappedEtherContract,
)
from automated_defi.protocol.chain import ETHChain


class Contracts:
    def __init__(self, chain: ETHChain, specs: list[ContractSpec]) -> None:
        self.specs = specs

        self.derived_specs = specs.copy()
        self._contracts: Dict[str, BaseContract] = {}

        # load specs
        spec_names: Set[str] = set([spec.name for spec in self.specs])
        for spec in self.derived_specs:
            # keep track of loaded specs
            spec_names.add(spec.name)

            # use pkg_resources to bundle resources with published package
            lines = pkg_resources.read_text(abi, f"{spec.type.abi}.{chain.slug}.json")

            # loading as json is not strictly necessary
            lines = json.loads(lines)
            contract = chain.w3.eth.contract(
                address=chain.w3.toChecksumAddress(spec.address), abi=lines
            )

            if spec.type == ContractType.TOKEN:
                self._contracts[contract.address] = TokenContract(
                    name=spec.name,
                    type=spec.type,
                    chain=chain,
                    contract=contract,
                    decimals=contract.functions.decimals().call(),
                    symbol=contract.functions.symbol().call(),
                )
            elif spec.type == ContractType.CTOKEN:
                underlying_asset_address = None
                if spec.name != "cETH":
                    underlying_asset_address = contract.functions.underlying().call()
                self._contracts[contract.address] = CTokenContract(
                    name=spec.name,
                    type=spec.type,
                    chain=chain,
                    contract=contract,
                    decimals=contract.functions.decimals().call(),
                    symbol=contract.functions.symbol().call(),
                    comptroller_address=contract.functions.comptroller().call(),
                    underlying_asset_address=underlying_asset_address,
                )
                if underlying_asset_address:
                    self.derived_specs.append(
                        ContractSpec(
                            name=spec.name[1:]
                            if spec.name.startswith("c")
                            else (spec.name + "_token"),
                            type=ContractType.TOKEN,
                            address=underlying_asset_address,
                        )
                    )
            elif spec.type == ContractType.COMPTROLLER:
                self._contracts[contract.address] = ComptrollerContract(
                    name=spec.name,
                    type=spec.type,
                    chain=chain,
                    contract=contract,
                )
                if "COMP" not in [spec.name for spec in self.specs] and hasattr(
                    contract.functions, "getCompAddress"
                ):
                    self.derived_specs.append(
                        ContractSpec(
                            name=("COMP"),
                            type=ContractType.TOKEN,
                            address=contract.functions.getCompAddress().call(),
                        )
                    )
            elif spec.type == ContractType.PRICE_ORACLE_PROXY:
                self._contracts[contract.address] = PriceOracleProxyContract(
                    name=spec.name,
                    type=spec.type,
                    chain=chain,
                    contract=contract,
                )
            elif spec.type == ContractType.COMPOUND_LENS:
                self._contracts[contract.address] = CompoundLensContract(
                    name=spec.name,
                    type=spec.type,
                    chain=chain,
                    contract=contract,
                )
            elif spec.type == ContractType.PRICE_FEED:
                self._contracts[contract.address] = PriceFeedContract(
                    name=spec.name,
                    type=spec.type,
                    chain=chain,
                    contract=contract,
                )
            elif spec.type == ContractType.COMPTROLLER_IMPL:
                self._contracts[contract.address] = ComptrollerContract(
                    name=spec.name,
                    type=spec.type,
                    chain=chain,
                    contract=contract,
                )
            elif spec.type == ContractType.PRICE_ORACLE:
                self._contracts[contract.address] = PriceOracleContract(
                    name=spec.name,
                    type=spec.type,
                    chain=chain,
                    contract=contract,
                )
            elif spec.type == ContractType.UNISWAP_ANCHORED_VIEW:
                self._contracts[contract.address] = UniswapAnchoredViewContract(
                    name=spec.name,
                    type=spec.type,
                    chain=chain,
                    contract=contract,
                )
            elif spec.type == ContractType.WRAPPED_ETH:
                self._contracts[contract.address] = WrappedEtherContract(
                    name=spec.name,
                    type=spec.type,
                    chain=chain,
                    contract=contract,
                    decimals=contract.functions.decimals().call(),
                    symbol=contract.functions.symbol().call(),
                )
            # Liquity Functions
            elif spec.type == ContractType.POOL:
                self._contracts[contract.address] = StabilityPoolContract(
                    name=spec.name,
                    type=spec.type,
                    chain=chain,
                    contract=contract,
                )
            # Not executable on Testnet - this is for Mainnet
            elif spec.type == ContractType.COMMUNITY:
                self._contracts[contract.address] = CommunityIssuanceContract(
                    name=spec.name,
                    type=spec.type,
                    chain=chain,
                    contract=contract,
                )

    @cached_property
    def by_name(self) -> dict[str, BaseContract]:
        return {c.name: c for c in self._contracts.values()}

    @cached_property
    def by_address(self) -> dict[str, BaseContract]:
        return self._contracts

    @cached_property
    def by_type(self) -> dict[ContractType, List[BaseContract]]:
        d = defaultdict(list)
        for c in self._contracts.values():
            d[c.type].append(c)
        return dict(d)

    def recognize_assets(
        self,
        addresses: List[ChecksumAddress],
    ) -> Tuple[List[ERC20Contract], List[ChecksumAddress]]:
        """Recognize c-token contract addresses."""
        recognized: List[ERC20Contract] = []
        unrecognized: List[ChecksumAddress] = []
        for a in addresses:
            if a in self.by_address:
                recognized.append(self[a])
            else:
                unrecognized.append(a)
        return recognized, unrecognized

    def __getitem__(self, key):
        try:
            return self.by_address[key]
        except KeyError:
            return self.by_name[key]

    def __iter__(self):
        return self._contracts.values().__iter__()

    def __next__(self):

        return self._contracts.values().__next__()
