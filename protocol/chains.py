import os
from dataclasses import dataclass
from functools import cached_property
from typing import List, Tuple

from web3 import Web3

from automated_defi.eth.contract import ContractSpec, ContractType
from automated_defi.eth.contract_index import Contracts
from automated_defi.protocol import chain


@dataclass
class ETHUnittest(chain.ETHChain):
    name: str = "Ethereum (Unittest)"
    slug: str = "eth-unittest"
    id: int = 5
    is_testnet: bool = False

    @staticmethod
    def node_url():
        return ""

    @staticmethod
    def etherscan_url(txn_hash):
        return ""

    @cached_property
    def w3(self):
        return Web3(Web3.EthereumTesterProvider())

    @cached_property
    def contracts(self) -> Contracts:
        # TODO add contracts or derive this class form ETHMainnet?
        return Contracts(self, [])


@dataclass
class ETHMainnet(chain.ETHChain):
    name: str = "Ethereum"
    slug: str = "eth"
    id: int = 1
    is_testnet: bool = False

    @cached_property
    def contracts(self) -> Contracts:
        return Contracts(
            self,
            [
                ContractSpec(
                    name="cUSDC",
                    type=ContractType.CTOKEN,
                    address="0x39aa39c021dfbae8fac545936693ac917d5e7563",
                ),
                ContractSpec(
                    name="cDAI",
                    type=ContractType.CTOKEN,
                    address="0x5d3a536e4d6dbd6114cc1ead35777bab948e3643",
                ),
                ContractSpec(
                    name="cETH",
                    type=ContractType.CTOKEN,
                    address="0x4ddc2d193948926d02f9b1fe9e1daa0718270ed5",
                ),
                ContractSpec(
                    name="comptroller",
                    type=ContractType.COMPTROLLER,
                    address="0x3d9819210a31b4961b30ef54be2aed79b9c9cd3b",
                ),
                ContractSpec(
                    name="price_feed",
                    type=ContractType.PRICE_FEED,
                    address="0x6D2299C48a8dD07a872FDd0F8233924872Ad1071",
                ),
                ContractSpec(
                    name="compound_lens",
                    type=ContractType.COMPOUND_LENS,
                    address="0xdCbDb7306c6Ff46f77B349188dC18cEd9DF30299",
                ),
                ContractSpec(
                    name="price_oracle_proxy",
                    type=ContractType.PRICE_ORACLE_PROXY,
                    address="0xDDc46a3B076aec7ab3Fc37420A8eDd2959764Ec4",
                ),
                ContractSpec(
                    name="price_oracle",
                    type=ContractType.PRICE_ORACLE,
                    address="0x02557a5e05defeffd4cae6d83ea3d173b272c904",
                ),
                ContractSpec(
                    name="uniswap_anchored_view",
                    type=ContractType.UNISWAP_ANCHORED_VIEW,
                    address="0x65c816077C29b557BEE980ae3cC2dCE80204A0C5",
                ),
                # Liquity Mainnet Contract Addresses
                ContractSpec(
                    name="LUSD",
                    # NOTE: we currently use the generic ABI `token.CHAIN.json` despite some deviations of the LUSD token contract
                    type=ContractType.TOKEN,
                    address="0x5f98805A4E8be255a32880FDeC7F6728C6568bA0",
                ),
                ContractSpec(
                    name="LQTY",
                    # NOTE: we currently use the generic ABI `token.CHAIN.json` despite some deviations of the LQTY token contract
                    type=ContractType.TOKEN,
                    address="0x6DEA81C8171D0bA574754EF6F8b412F2Ed88c54D",
                ),
                ContractSpec(
                    name="stability_pool",
                    type=ContractType.POOL,
                    address="0x66017D22b0f8556afDd19FC67041899Eb65a21bb",
                ),
                ContractSpec(
                    name="community_issuance",
                    type=ContractType.COMMUNITY,
                    address="0xD8c9D9071123a059C6E0A945cF0e0c82b508d816",
                ),
                ContractSpec(
                    name="WETH",
                    type=ContractType.WRAPPED_ETH,
                    address="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                ),
            ],
        )

    @staticmethod
    def node_url():
        return f'https://mainnet.infura.io/v3/{os.environ["API_KEY"]}'

    @staticmethod
    def etherscan_url(txn_hash):
        return f"https://etherscan.io/tx/{txn_hash}"


@dataclass
class ETHGoerli(chain.ETHChain):
    name: str = "Ethereum (Goerli)"
    slug: str = "eth-goerli"
    id: int = 5
    is_testnet: bool = True

    @cached_property
    def contracts(self) -> Contracts:
        return Contracts(
            self,
            [
                # compound contract (for multiple assets) with docs on mainnet: https://etherscan.io/token/0xc00e94cb662c3520282e6f5717214004a7f26888#readContract
                # from https://compound.finance/docs
                # analogous contract with docs on mainnet: https://etherscan.io/token/0x39aa39c021dfbae8fac545936693ac917d5e7563#readContract
                ContractSpec(
                    name="cUSDC",
                    type=ContractType.CTOKEN,
                    address="0xCEC4a43eBB02f9B80916F1c718338169d6d5C1F0",
                ),
                ContractSpec(
                    name="cDAI",
                    type=ContractType.CTOKEN,
                    address="0x822397d9a55d0fefd20F5c4bCaB33C5F65bd28Eb",
                ),
                ContractSpec(
                    name="cETH",
                    type=ContractType.CTOKEN,
                    address="0x20572e4c090f15667cf7378e16fad2ea0e2f3eff",
                ),
                # analogous contract with docs on mainnet: https://etherscan.io/address/0x3d9819210a31b4961b30ef54be2aed79b9c9cd3b#readProxyContract
                # read https://compound.finance/docs/comptroller
                ContractSpec(
                    name="comptroller",
                    type=ContractType.COMPTROLLER,
                    address="0x627EA49279FD0dE89186A58b8758aD02B6Be2867",
                ),
            ],
        )

    @staticmethod
    def node_url():
        # TODO inject api key and do not read from environment
        return f'https://goerli.infura.io/v3/{os.environ["API_KEY"]}'

    @staticmethod
    def etherscan_url(txn_hash):
        return f"https://goerli.etherscan.io/tx/{txn_hash}"


@dataclass
class ETHRopsten(chain.ETHChain):
    name: str = "Ethereum (Ropsten)"
    slug: str = "eth-ropsten"
    id: int = 3
    is_testnet: bool = True

    @cached_property
    def contracts(self) -> Contracts:
        return Contracts(
            self,
            [
                ContractSpec(
                    name="cUSDC",
                    type=ContractType.CTOKEN,
                    address="0x2973e69b20563bcc66dc63bde153072c33ef37fe",
                ),
                ContractSpec(
                    name="cDAI",
                    type=ContractType.CTOKEN,
                    address="0xbc689667c13fb2a04f09272753760e38a95b998c",
                ),
                ContractSpec(
                    name="cETH",
                    type=ContractType.CTOKEN,
                    address="0x859e9d8a4edadfedb5a2ff311243af80f85a91b8",
                ),
                # analogous contract with docs on mainnet: https://etherscan.io/address/0x3d9819210a31b4961b30ef54be2aed79b9c9cd3b#readProxyContract
                # read https://compound.finance/docs/comptroller
                ContractSpec(
                    name="comptroller",
                    type=ContractType.COMPTROLLER,
                    address="0xcfa7b0e37f5ac60f3ae25226f5e39ec59ad26152",
                ),
            ],
        )

    @staticmethod
    def node_url():
        # TODO inject api key and do not read from environment
        return f'https://ropsten.infura.io/v3/{os.environ["API_KEY"]}'

    @staticmethod
    def etherscan_url(txn_hash):
        return f"https://ropsten.etherscan.io/tx/{txn_hash}"


@dataclass
class ETHRinkeby(chain.ETHChain):
    name: str = "Ethereum (Rinkeby)"
    slug: str = "eth-rinkeby"
    id: int = 4
    is_testnet: bool = True

    @cached_property
    def contracts(self) -> Contracts:
        return Contracts(
            self,
            [
                ContractSpec(
                    name="cUSDC",
                    type=ContractType.CTOKEN,
                    address="0x5b281a6dda0b271e91ae35de655ad301c976edb1",
                ),
                ContractSpec(
                    name="cDAI",
                    type=ContractType.CTOKEN,
                    address="0x6d7f0754ffeb405d23c51ce938289d4835be3b14",
                ),
                ContractSpec(
                    name="cETH",
                    type=ContractType.CTOKEN,
                    address="0xd6801a1dffcd0a410336ef88def4320d6df1883e",
                ),
                # NOTE Manually specify COMP token because ABI has no getCompAddress function on Rinkeby
                ContractSpec(
                    name="COMP",
                    type=ContractType.TOKEN,
                    address="0xbbEB7c67fa3cfb40069D19E598713239497A3CA5",
                ),
                # analogous contract with docs on mainnet: https://etherscan.io/address/0x3d9819210a31b4961b30ef54be2aed79b9c9cd3b#readProxyContract
                # read https://compound.finance/docs/comptroller
                ContractSpec(
                    name="comptroller",
                    type=ContractType.COMPTROLLER,
                    address="0x2eaa9d77ae4d8f9cdd9faacd44016e746485bddb",
                ),
                ContractSpec(
                    name="compound_lens",
                    type=ContractType.COMPOUND_LENS,
                    address="0x04EC9f6Ce8ca39Ee5c7ADE95C69e38ddcaA8CbB7",
                ),
                ContractSpec(
                    name="price_oracle_proxy",
                    type=ContractType.PRICE_ORACLE_PROXY,
                    address="0x5722A3F60fa4F0EC5120DCD6C386289A4758D1b2",
                ),
                ContractSpec(
                    name="price_oracle",
                    type=ContractType.PRICE_ORACLE,
                    address="0xD2B1eCa822550d9358e97e72c6C1a93AE28408d0",
                ),
                ContractSpec(
                    name="uniswap_anchored_view",
                    type=ContractType.UNISWAP_ANCHORED_VIEW,
                    address="0xE3535db98FE41b6Df5325B8Dd3c5c3a5e289b2Da",
                ),
                ContractSpec(
                    name="WETH",
                    type=ContractType.WRAPPED_ETH,
                    address="0xDf032Bc4B9dC2782Bb09352007D4C57B75160B15",
                ),
                # Liquity Testnet Contract Addresses
                ContractSpec(
                    name="LUSD",
                    type=ContractType.TOKEN,
                    address="0x9C5AE6852622ddE455B6Fca4C1551FC0352531a3",
                ),
                ContractSpec(
                    name="LQTY",
                    type=ContractType.TOKEN,
                    address="0xF74dcAbeA0954AeB6903c8a71d41e468a6B77357",
                ),
                ContractSpec(
                    name="stability_pool",
                    type=ContractType.POOL,
                    address="0xB8eb11f9eFF55378dfB692296C32DF020f5CC7fF",
                ),
            ],
        )

    @staticmethod
    def node_url():
        # TODO inject api key and do not read from environment
        return f'https://rinkeby.infura.io/v3/{os.environ["API_KEY"]}'

    @staticmethod
    def etherscan_url(txn_hash):
        return f"https://rinkeby.etherscan.io/tx/{txn_hash}"


class Chains:
    # Ethereum main net
    ETH_MAINNET = ETHMainnet()
    ETH_GOERLI = ETHGoerli()
    ETH_ROPSTEN = ETHRopsten()
    ETH_RINKEBY = ETHRinkeby()
    ETH_UNITTEST = ETHUnittest()

    ALL = [
        ETH_MAINNET,
        ETH_GOERLI,
        ETH_ROPSTEN,
        ETH_RINKEBY,
    ]  # intentionally exclude ETH_UNITTEST

    @cached_property
    def by_slug(self) -> dict[str, chain.Chain]:
        return {c.slug: c for c in Chains.ALL}

    @cached_property
    def choices(self) -> List[Tuple[str, str]]:
        """Choices returns list of tuples to use for a Django choices field.

        Typical usage example:

            chains = Chains()
            chain = models.CharField(
            max_length=64,
                choices=chains.choices,
                default=chains.ETH_CHAIN,
                db_index=True,
            )
        """
        return [(chain.slug, str(chain)) for chain in Chains.ALL]
