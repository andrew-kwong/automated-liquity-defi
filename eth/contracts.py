from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from decimal import Decimal
from functools import cached_property
from typing import TYPE_CHECKING, Dict, Generic, List, Optional, TypeVar, Union

from eth_account import Account
from eth_account.signers.base import BaseAccount
from eth_typing import ChecksumAddress, HexStr
from web3.contract import Contract
from web3.types import TxParams, Wei

from automated_defi.decimal_utils import decimal_context
from automated_defi.errors import PipelineDefinitionError

if TYPE_CHECKING:
    # avoid cyclic imports
    from automated_defi.eth.contract_index import Contracts

from . import assets
from .contract import BaseContract

A = TypeVar("A", bound=assets.ERC20Asset)

UINT_MAX = 2**256 - 1
"""The maximum unsigned integer understood by Ethereum.

See https://github.com/ethereum/solidity-examples/blob/4e5f1f3a559559ae9b54b500743534a4446b680c/src/math/ExactMath.sol#L11.
"""
INT_MAX = 2**255 - 1
"""The maximum signed integer understood by Ethereum.

See https://github.com/ethereum/solidity-examples/blob/4e5f1f3a559559ae9b54b500743534a4446b680c/src/math/ExactMath.sol#L18.
"""


@dataclass
class ERC20Contract(BaseContract, Generic[A], ABC):
    """An ERC20 token contract."""

    decimals: int
    symbol: str

    @cached_property
    def _quantizer(self) -> Decimal:
        return Decimal(10) ** -self.decimals

    def serialize(self, amount: A) -> int:
        """Serializes the amount represented as a decimal into a the expanded int form expected by contract calls."""
        return int((amount * 10**self.decimals).to_integral_exact())

    def deserialize(self, amount: int) -> A:
        """Deserializes the amount represented in an expanded int form into a decimal understood by the user."""
        return assets.ERC20Asset(
            (amount / Decimal(10) ** self.decimals).quantize(
                self._quantizer, context=decimal_context()
            )
        )

    def balance(self, account: Account) -> A:
        return self.deserialize(
            self.contract.functions.balanceOf(account.address).call()
        )

    def total_supply(self):
        return self.deserialize(self.contract.functions.totalSupply().call())

    def approve(
        self,
        account: Account,
        spender: Union[ERC20Contract, ChecksumAddress],
        amount: A = assets.ERC20Asset(Decimal(0)),
        set_unlimited: bool = False,
    ) -> TxParams:
        """Allow the contract to reserve up to a certain amount from wallet.

        Should be first set to `0` according to [EIP-20 token standard](https://eips.ethereum.org/EIPS/eip-20#approve).
        """
        return self.contract.functions.approve(
            spender.address if isinstance(spender, ERC20Contract) else spender,
            UINT_MAX if set_unlimited else self.serialize(amount),
        ).buildTransaction(
            {
                "from": account.address,
            }
        )

    def allowance(
        self,
        owner: Account,
        spender: Union[ERC20Contract, ChecksumAddress],
    ) -> A:
        """Returns the remaining number of tokens that can be transfered by `spender`."""
        allowance = self.contract.functions.allowance(
            owner.address,
            spender.address if isinstance(spender, ERC20Contract) else spender,
        ).call()
        return self.deserialize(allowance)

    def transfer(
        self,
        source: Union[Account, HexStr],
        target: Union[Account, HexStr],
        amount: A,
    ) -> TxParams:
        source_address = source.address if isinstance(source, BaseAccount) else source
        target_address = target.address if isinstance(target, BaseAccount) else target
        return self.contract.functions.transfer(
            target_address,
            self.serialize(amount),
        ).buildTransaction(
            {
                "from": source_address,
            }
        )


@dataclass
class TokenContract(ERC20Contract[assets.Token]):
    def __str__(self) -> str:
        return f"{self.name}: {self.symbol}"


@dataclass
class StabilityPoolContract(BaseContract):

    # check on how much LQTY is accrued
    def lqty_accrued(
        self,
        account: Account,
    ) -> Decimal:
        lqty = self.contract.functions.getDepositorLQTYGain(account.address).call()
        return assets.LQTY(lqty / Decimal(10) ** 18)

    # check on how much ETH is gained from liquidated troves
    def eth_accrued(
        self,
        account: Account,
    ) -> Decimal:
        eth = self.contract.functions.getDepositorETHGain(account.address).call()
        return assets.ETH(eth / Decimal(10) ** 18)

    # check on how much LUSD is deposited
    def lusd_deposit(
        self,
        account: Account,
    ) -> Decimal:
        lusd = self.contract.functions.getCompoundedLUSDDeposit(account.address).call()
        return assets.LUSD(lusd / Decimal(10) ** 18)

    # returns total LUSD Deposit supply
    def get_total_lusd_deposits(
        self,
    ) -> Decimal:
        total = self.contract.functions.getTotalLUSDDeposits().call()
        return assets.LUSD(total / Decimal(10) ** 18)

    # deposit LUSD to stability pool
    def provide_to_sp(
        self,
        contracts: Contracts,
        source: Account,
        amount: assets.LUSD,
    ) -> TxParams:
        """Provide LUSD to stability pool"""
        if self.chain.is_testnet:
            address = "0x0000000000000000000000000000000000000000"
        else:
            # frontend tag on mainnet
            address = "0x30E5D10DC30a0CE2545a4dbe8DE4fCbA590062c5"
            contracts["LUSD"].address
        return self.contract.functions.provideToSP(amount, address).buildTransaction()

    # withdraw LUSD from the stability pool
    def withdraw_from_sp(
        self,
        source: Account,
        amount: assets.LUSD,
    ) -> TxParams:
        """Withdraw LUSD from stability pool"""
        return self.contract.functions.withdrawFromSP(amount).buildTransaction()


@dataclass
class CommunityIssuanceContract(BaseContract):

    # gets the total LQTY Issued
    def total_lqty_issued(
        self,
    ) -> Decimal:
        lqty_total = self.contract.functions.totalLQTYIssued().call()
        return assets.LQTY(lqty_total / Decimal(10) ** 18)


@dataclass
class WrappedEtherContract(TokenContract):
    """
    Wrapped Ether Contract: converts ETH to wETH and vice versa
    See: https://weth.io/

    """

    # Converts from ETH to wETH
    def eth_to_wETH(self, source: Account, amount: assets.ETH) -> TxParams:
        tx = self.contract.functions.deposit().buildTransaction()
        tx["value"] = Wei(self.serialize(amount))
        return tx

    # Converts from wETH to ETH
    def wETH_to_eth(self, source: Account, amount: assets.WETH) -> TxParams:
        return self.contract.functions.withdraw(
            self.serialize(amount)
        ).buildTransaction()


@dataclass
class CTokenContract(ERC20Contract[assets.CToken]):
    comptroller_address: str
    underlying_asset_address: Optional[str]

    def balance_of_underlying(
        self, contracts: Contracts, account: Account
    ) -> assets.Token:
        return contracts[self.underlying_asset_address].deserialize(
            self.contract.functions.balanceOfUnderlying(account.address).call()
        )

    def rate_in_underlying(self, contracts: Contracts) -> Decimal:
        """Returns the rate r of the underlying token such that r*num_c_token=num_token.

        See
        - Relevant Compound docs: https://compound.finance/docs#guides
        - Compound JS SDK implementation: https://github.com/compound-finance/compound-js/blob/be7db2d6166729d4bced13a2d791c0fba91d80a4/src/priceFeed.ts#L46.
        """
        rate = self.contract.functions.exchangeRateCurrent().call()

        mantissa = (
            18 + contracts[self.underlying_asset_address].decimals - self.decimals
        )
        return rate / Decimal(10) ** mantissa

    def mint(
        self,
        contracts: Contracts,
        source: Account,
        amount: assets.Token,
    ) -> TxParams:
        """Supplies tokens to Compound, receiving c-Tokens in turn."""
        return self.contract.functions.mint(
            mintAmount=contracts[self.underlying_asset_address].serialize(amount),
        ).buildTransaction(
            {
                "from": source.address,
            }
        )

    def borrow(
        self,
        contracts: Contracts,
        target: Account,
        amount: assets.Token,
    ) -> TxParams:
        """Borrow an amount of a token from Compound."""

        return self.contract.functions.borrow(
            borrowAmount=contracts[self.underlying_asset_address].serialize(amount)
        ).buildTransaction(
            {
                "from": target.address,
            }
        )

    def borrow_balance(
        self,
        contracts: Contracts,
        account: Account,
    ) -> assets.Token:
        """Fetches the account's borrow balance with interest in the underlying asset."""
        b = self.contract.functions.borrowBalanceStored(account=account.address).call()
        return contracts[self.underlying_asset_address].deserialize(b)

    def redeem(
        self,
        account: Account,
        amount: assets.CToken,
    ) -> TxParams:
        """Redeem a c-token amount."""

        return self.contract.functions.redeem(
            redeemTokens=self.serialize(amount)
        ).buildTransaction(
            {
                "from": account.address,
            }
        )

    def redeem_underlying(
        self,
        contracts: Contracts,
        account: Account,
        amount: assets.Token,
    ) -> TxParams:
        """Redeem a token amount."""

        return self.contract.functions.redeemUnderlying(
            redeemAmount=contracts[self.underlying_asset_address].serialize(amount)
        ).buildTransaction(
            {
                "from": account.address,
            }
        )

    def repay(
        self,
        contracts: Contracts,
        account: Account,
        amount: assets.Token,
        remaining: bool = False,
    ) -> TxParams:
        """Repay a token amount.

        Args:
            contracts (Contracts): contracts to lookup underlying token for serialization
            account (Account): the account issuing the transaction
            amount (assets.Token): the amount of tokens to repay (but see `remaining`)
            remaining (bool, optional): If True, pays back as much as available on wallet (instead of amount). Defaults to False.

        Returns:
            TxParams: the transaction to be executed
        """

        return self.contract.functions.repayBorrow(
            repayAmount=UINT_MAX
            if remaining
            else contracts[self.underlying_asset_address].serialize(amount)
        ).buildTransaction(
            {
                "from": account.address,
            }
        )


@dataclass
class ComptrollerContract(BaseContract):
    """
    The helper contract offering generic interactions around cToken.

    *NOTE*: eventhough COMP is a ERC-20 token, the ComptrollerContract is a
    managing (proxy) contract and itself not a ERC-20 token contract.
    """

    contract: Contract

    def enter_markets(
        self,
        account: Account,
        contracts: list[CTokenContract],
    ) -> Optional[TxParams]:
        """Enables collateral (enter one or several markets)."""
        # NOTE: apparently we can enter the market for cUSDC
        c_token_contracts = [
            c.address
            for c in contracts
            if not self.check_membership(account=account, contract=c)
        ]
        if c_token_contracts:
            return self.contract.functions.enterMarkets(
                cTokens=c_token_contracts,
            ).buildTransaction()
        return None

    def check_membership(
        self,
        account: Account,
        contract: CTokenContract,
    ) -> bool:
        return self.contract.functions.checkMembership(
            account=account.address, cToken=contract.address
        ).call()

    def get_account_liquidity(
        self,
        account: Account,
    ) -> Decimal:
        """
        Account Liquidity represents the USD value borrowable by a user, before
        it reaches liquidation. Users with a shortfall (negative liquidity) are
        subject to liquidation, and can’t withdraw or borrow assets until
        Account Liquidity is positive again.

        *NOTE*: We know from experimation that the returned USD value has 18
        decimals of precision, this is however undocumented! See
        https://compound.finance/docs/comptroller#account-liquidity.
        """
        _, liquidity, _ = self.contract.functions.getAccountLiquidity(
            account=account.address
        ).call()
        return liquidity / Decimal(10) ** 18

    def get_assets(
        self,
        account: Account,
    ) -> List[ChecksumAddress]:
        """Returns contract addresses of c-token involved in Compound, in supply
        AND borrow actions.

        NOTE: Even when borrowing a normal token only its corresponding c-token gets listed."""
        return self.contract.functions.getAssetsIn(account.address).call()

    def collateral_factor(
        self,
        c_token: CTokenContract,
    ) -> Decimal:
        res = self.contract.functions.markets(c_token.address).call()
        if len(res) == 2:  # rinkeby has less return arguments
            is_listed, collateral_factor = res
        elif len(res) == 3:
            is_listed, collateral_factor, _ = res
        else:
            raise PipelineDefinitionError(
                f"unexpected number of return arguments {len(res)} for method {self.name}.markets"
            )
        if not is_listed:
            raise PipelineDefinitionError(f"'{c_token}' is not listed by compound")
        return collateral_factor / Decimal(10) ** 18

    def comp_accrued(
        self,
        account: Account,
    ) -> Decimal:
        comp = self.contract.functions.compAccrued(account.address).call()
        return comp / Decimal(10) ** 18

    def claim_comp(
        self,
        account: Account,
        c_token_contracts: List[CTokenContract],
    ) -> TxParams:
        """Claim accrued comp by transfering to given account."""
        return self.contract.functions.claimComp(
            holder=account.address, cTokens=[c.address for c in c_token_contracts]
        ).buildTransaction(
            {
                "from": account.address,
            }
        )


@dataclass
class PriceFeedContract(BaseContract):
    def get_price(
        self,
        of: TokenContract,
    ) -> Decimal:
        """
        Get the most recent price for a token in USD with 18 decimals of
        precision.

        See https://compound.finance/docs/prices#underlying-price.
        """
        price = Decimal(self.contract.functions.price(of.symbol).call())
        return price / Decimal(10) ** 6


@dataclass
class PriceOracleProxyContract(BaseContract):
    def get_underlying_price(
        self,
        of: CTokenContract,
    ) -> Decimal:
        """
        Get the most recent price for a token in USD with 18 decimals of
        precision.

        See https://compound.finance/docs/prices#underlying-price.
        """
        price = Decimal(self.contract.functions.getUnderlyingPrice(of.address).call())
        return price / Decimal(10) ** 18


@dataclass
class PriceOracleContract(BaseContract):
    def get_price(
        self,
        of: TokenContract,
    ) -> Decimal:
        """
        Get the most recent price for a token in USD with 18 decimals of
        precision.

        See https://compound.finance/docs/prices#underlying-price.
        """
        price = Decimal(self.contract.functions.getPrice(of.address).call())
        return price / Decimal(10) ** 6


@dataclass
class UniswapAnchoredViewContract(BaseContract):
    def get_price(
        self,
        of: Union[str, TokenContract],
    ) -> Decimal:
        price = Decimal(
            self.contract.functions.price(
                of.symbol if isinstance(of, TokenContract) else of
            ).call()
        )
        return price / Decimal(10) ** 6


@dataclass
class CompoundLensContract(BaseContract):
    def all_underlying_prices(
        self,
        token_contracts: List[CTokenContract],
    ) -> Dict[str, Decimal]:
        """
        Get the most recent price for a token in USD with 18 decimals of
        precision.

        See https://compound.finance/docs/prices#underlying-price.
        """
        tuples = self.contract.functions.cTokenUnderlyingPriceAll(
            [c.address for c in token_contracts]
        ).call()
        by_address = {t[0]: t[1] for t in tuples}

        prices = {}
        for c in token_contracts:
            prices[c.name] = by_address[c.address] / Decimal(10) ** 18
        return prices
