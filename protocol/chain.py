from __future__ import annotations

import dataclasses
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from functools import cached_property
from typing import TYPE_CHECKING, Optional, Union

from eth_account import Account
from eth_typing import ChecksumAddress
from web3 import Web3
from web3._utils.threads import Timeout
from web3.exceptions import TimeExhausted
from web3.types import Nonce, TxParams, TxReceipt, Wei

from automated_defi.errors import PipelineExecutionError
from automated_defi.eth import assets

if TYPE_CHECKING:
    # avoid cyclic imports
    from automated_defi.eth.contract_index import Contracts


DEFAULT_PRIORITY_FEE = assets.GWEI(Decimal("3"))
DEFAULT_ESTIMATED_GAS_SURPLUS = 100_000


@dataclass
class BaseTxParams:
    """The most guaranteed way to have your transaction included in the block is
    to just specify a maxPriorityFeePerGas field (which is a tip).
    In this case, `add_tx_params` will look up the pending baseFee and then set
    the maxFeePerGas field accordingly (to the sum of the base fee and the tip).
    All you have to do is decide how much tip to provide, which you can get by
    simply calling the eth_maxPriorityFeePerGas method on Alchemy.

    Although this is the simplest method, it may not be the cheapest. There are
    two dimensions to consider when submitting your transaction: speed and cost.
    If you bid high, you get mined earlier. If you bid low, you get mined later
    or not at all. When you submit only the maxPriorityFeePerGas field, the
    defaults will fill in the base fee for you. Recall that the base fee depends
    on how full previous blocks were. If many of the previous blocks were full,
    then the base fee can end up being quite high! And since we are filling in
    the value for you, you can end up paying a surprisingly high gas price.

    To avoid this pitfall you can supply the maxFeePerGas field. If you supply
    only this field, then the tip will be filled in for you, however, there are
    no guarantees on when your transaction will be mined. You can also supply
    both the maxFeePerGas and the maxPriorityFeePerGas fields for full control.

    Read more:
    https://docs.alchemy.com/alchemy/guides/eip-1559/maxpriorityfeepergas-vs-maxfeepergas#when-to-use-max-priority-fee-per-gas-vs-max-fee-per-gas
    """

    nonce: Optional[int] = None
    default_gas: Optional[int] = None
    max_fee_per_gas: Optional[assets.GWEI] = None
    max_priority_fee_per_gas: Optional[assets.GWEI] = None
    estimated_gas_surplus: int = DEFAULT_ESTIMATED_GAS_SURPLUS


@dataclass
class Chain(ABC):
    """Class for blockchain identification."""

    name: str  # human readable name
    slug: str  # the unique key used to identify this chain -> used in task routing keys
    id: int  # constant chain ID used in contract calls; see https://besu.hyperledger.org/en/stable/Concepts/NetworkID-And-ChainID/
    is_testnet: bool = False

    def __str__(self) -> str:
        return self.name or self.slug


class ETHChain(Chain, ABC):
    ETH_DECIMALS = 18

    def do(self, signing_account: Account, tx: TxParams) -> TxReceipt:
        signed_tx = signing_account.sign_transaction(tx)
        tx_hash = self.w3.toHex(
            self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        )
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        self.wait_blocks_diff(receipt.blockNumber)
        return receipt

    def wait_blocks_diff(
        self,
        tx_block: int,
        number_blocks: int = 6,
        timeout: Optional[float] = None,
        poll_latency: float = 1,
    ):
        """Wait the given number of blocks to be mined after `tx_block`.

        Adapted from web3.eth.Eth.wait_for_transaction_receipt.

        The timeout before raising TimeExhausted can be defined, otherwise defaults to 30 * `number_blocks`; 14s is the average block time but peaks are 30s. See see https://etherscan.io/chart/blocktime.

        Args:
            tx_block (int): The block containing the transaction of intrest.
            number_blocks (int, optional): The number of blocks to wait. Defaults to 6.
            timeout (Optional[float], optional): The timeout in seconds. Defaults to reasonable expected waiting time.
            poll_latency (float, optional): Waiting time in seconds between polling current block number. Defaults to 1.

        Raises:
            ValueError: if the tx_block is in the future
            TimeExhausted: if timeout exhausted
        """
        try:
            with Timeout(
                timeout or float(number_blocks * 30)
            ) as _timeout:  # average block time is 14s, but peaks are 30s
                while True:
                    current_block = self.w3.eth.get_block("latest").number

                    diff = current_block - tx_block
                    if diff < 0:
                        raise ValueError(
                            f"given transaction block {tx_block} is a future block"
                        )
                    elif diff >= number_blocks:
                        break
                    _timeout.sleep(poll_latency)
        except Timeout:
            raise TimeExhausted(
                f"Timeout exausted when waiting for {number_blocks} after transaction block {tx_block} of transaction"
            )

    def add_tx_params(
        self,
        tx: TxParams,
        account: Union[Account, ChecksumAddress],
        base_tx_params: Optional[BaseTxParams] = None,
        legacy_pricing=False,
    ) -> TxParams:
        """Adds transaction parameters to `tx`, calculating values not yet provided.

        See https://web3py.readthedocs.io/en/stable/web3.eth.html#web3.eth.Eth.send_transaction.

        Args:
            tx (TxParams): the transaction to update with parameters
            account (Account): The account or address to use for calculating the nonce and estimate gas
            base_tx_params (BaseTxParams, optional): Defaults to reasonable defaults for missing params or if None is provided for a value of BaseTxParams' attributes

        Raises:
            PipelineExecutionError: If the provided base_tx_params are conflicting with defaults.

        Returns:
            TxParams: the updated `tx`
        """
        address = account if isinstance(account, (bytes, str)) else account.address

        if base_tx_params is None:
            base_tx_params = BaseTxParams()
        else:
            # make a copy to avoid unintended aliasing
            base_tx_params = BaseTxParams(**dataclasses.asdict(base_tx_params))

        if (
            base_tx_params.max_fee_per_gas is None
            and base_tx_params.max_priority_fee_per_gas is None
        ):
            raise PipelineExecutionError(
                "at least one of base_tx_params.max_fee_per_gas and base_tx_params.max_priority_fee_per_gas must be set"
            )
        elif (
            base_tx_params.max_fee_per_gas is None
        ):  # => max_priority_fee_per_gas is not None

            # Doubling the Base Fee when calculating  the Max Fee ensures that
            # your transaction will remain marketable for six consecutive 100%
            # full blocks. The table below illustrates why.
            # See https://www.blocknative.com/blog/eip-1559-fees
            base_tx_params.max_fee_per_gas = assets.GWEI(
                self.base_fee_per_gas * 2 + base_tx_params.max_priority_fee_per_gas
            )

            if base_tx_params.max_fee_per_gas < self.base_fee_per_gas:
                raise PipelineExecutionError(
                    "base_tx_params.max_fee_per_gas must be larger or equal to the current block's base_fee_per_gas"
                )

        if base_tx_params.nonce is None:
            base_tx_params.nonce = self.w3.eth.get_transaction_count(address)

        # sadly contract functions `buildTransaction` method adds gasPrice since it thinks legacy pricing is desired if no pricing values set upfront
        if not legacy_pricing and "gasPrice" in tx:
            del tx["gasPrice"]

        tx.update(
            {
                "chainId": self.id,
                "nonce": Nonce(base_tx_params.nonce),
                "from": address,
            }
        )

        if not legacy_pricing:
            if base_tx_params.max_fee_per_gas is not None:
                tx["maxFeePerGas"] = self.w3.toWei(
                    base_tx_params.max_fee_per_gas, "gwei"
                )
            if base_tx_params.max_priority_fee_per_gas is not None:
                tx["maxPriorityFeePerGas"] = self.w3.toWei(
                    base_tx_params.max_priority_fee_per_gas,
                    "gwei",
                )

        if base_tx_params.default_gas:
            # NOTE: it's a typing mistake in the library and it's actually required to pass Gwei, not Wei
            tx["gas"] = Wei(base_tx_params.default_gas)
        else:
            tx["gas"] = Wei(
                self.estimate_gas(tx) + base_tx_params.estimated_gas_surplus
            )

        return tx

    @staticmethod
    @abstractmethod
    def node_url() -> str:
        pass

    @staticmethod
    @abstractmethod
    def etherscan_url(txn_hash) -> str:
        pass

    @cached_property
    def w3(self):
        return Web3(Web3.HTTPProvider(self.node_url()))

    @property
    def base_fee_per_gas(self) -> assets.GWEI:
        fee_history = self.w3.eth.fee_history(block_count=1, newest_block="latest")
        # return value has 2 list entries for current and next block, so 0 returns current block
        return assets.GWEI(self.w3.fromWei(fee_history["baseFeePerGas"][0], "gwei"))

    @property
    def gas_used_ratio(self) -> Decimal:
        fee_history = self.w3.eth.fee_history(block_count=1, newest_block="latest")
        # return value has single list entries for current block only
        return Decimal(fee_history["gasUsedRatio"][0])

    def estimate_gas(self, tx: TxParams) -> int:
        """Estimate gas fee for a the given transaction.

        TODO: improve by using better heuristic or external API.
        """
        # The web3.py library returns Gwei already, but states Wei, we leave it as int and therefore returns Gwei as a result
        return self.w3.eth.estimate_gas(tx)

    def estimate_gas_fee(self, tx: TxParams, current_gas_price) -> assets.ETH:
        """Estimates total gas fee in ETH for a given transaction, converting it from Gwei. Post London Upgrade, the formula is
        Gas units (limit) * (Base fee + Tip)

        See https://ethereum.org/ig/developers/docs/gas/ for details
        """
        return assets.ETH(
            (self.w3.eth.estimate_gas(tx) * current_gas_price) / (Decimal(10) ** 9)
        )

    @staticmethod
    def convert_gwei_to_eth(amount: Union[assets.GWEI, int]) -> assets.ETH:
        """Converts Gwei to ETH units."""
        return assets.ETH(amount / Decimal(10) ** 9)

    @cached_property
    @abstractmethod
    def contracts(self) -> Contracts:
        pass

    def eth_balance(self, address: ChecksumAddress) -> assets.ETH:
        """Retrieves the ETH balance.

        Does not require a contract but is supported by web3 directly."""
        balance_wei = self.w3.eth.get_balance(address)
        return assets.ETH(self.w3.fromWei(balance_wei, "ether"))
