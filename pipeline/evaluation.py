import logging
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import MutableMapping

from automated_defi.eth import assets
from automated_defi.pipeline import pipeline as p
from automated_defi.protocol.chain import BaseTxParams

from .pipeline import Evaluation

logger = logging.getLogger(__name__)


class State(MutableMapping):
    pass


class Visitor(ABC):
    """
    The Visitor Interface declares a set of visiting methods that correspond to
    component classes. The signature of a visiting method allows the visitor to
    identify the exact class of the component that it's dealing with.
    """

    def transform(self, step: p.Transform, state: State) -> Evaluation:
        logger.info(f"execute {step!r}")
        return Evaluation(state=step.func(state, *step.args))

    def expr(self, step: p.Expr, state: State) -> Evaluation:
        logger.info(f"execute {step!r}")
        state["_condition_"] = step.func(state, *step.args)
        return Evaluation(state=state)

    def enter_group(self, step: p.Group, state: State) -> State:
        logger.info(f"enter {step!r}")
        return state

    def exit_group(self, step: p.Group, state: State) -> State:
        logger.info(f"exit {step!r}")
        return state

    def enter_repeat(self, step: p.Repeat, state: State) -> State:
        logger.info(f"enter {step!r}")
        return state

    def exit_repeat(self, step: p.Repeat, state: State) -> State:
        logger.info(f"exit {step!r}")
        return state

    def setup(self, step: p.Setup, state: State) -> Evaluation:
        logger.info(f"execute {step!r}")

        base_tx_params = BaseTxParams(
            estimated_gas_surplus=step.estimated_gas_surplus,
            max_priority_fee_per_gas=assets.GWEI(Decimal(step.max_priority_fee)),
        )

        return Evaluation(
            state={**state, "base_tx_params": base_tx_params},
            chain_effect=False,
        )

    @abstractmethod
    def balance(self, step: p.Balance, state: State) -> Evaluation:
        return Evaluation(state=state)

    @abstractmethod
    def prices(self, step: p.Prices, state: State) -> Evaluation:
        return Evaluation(state=state)

    @abstractmethod
    def borrow_limit_fraction(
        self, step: p.BorrowLimitFraction, state: State
    ) -> Evaluation:
        return Evaluation(state=state)

    @abstractmethod
    def borrow_limit(self, step: p.BorrowLimit, state: State) -> Evaluation:
        return Evaluation(state=state)

    @abstractmethod
    def borrow_balance(self, step: p.BorrowBalance, state: State) -> Evaluation:
        return Evaluation(state=state)

    @abstractmethod
    def borrow(self, step: p.Borrow, state: State) -> Evaluation:
        return Evaluation(state=state)

    @abstractmethod
    def transfer(self, step: p.Transfer, state: State) -> Evaluation:
        return Evaluation(state=state)

    @abstractmethod
    def set_allowance(self, step: p.SetAllowance, state: State) -> Evaluation:
        return Evaluation(state=state)

    @abstractmethod
    def set_contract_allowance(
        self, step: p.SetContractAllowance, state: State
    ) -> Evaluation:
        return Evaluation(state=state)

    @abstractmethod
    def allowance(self, step: p.Allowance, state: State) -> Evaluation:
        return Evaluation(state=state)

    @abstractmethod
    def give_collateral(self, step: p.GiveCollateral, state: State) -> Evaluation:
        return Evaluation(state=state)

    @abstractmethod
    def supply(self, step: p.Supply, state: State) -> Evaluation:
        return Evaluation(state=state)

    @abstractmethod
    def c_token_equivalent(self, step: p.CTokenEquivalent, state: State) -> Evaluation:
        return Evaluation(state=state)

    @abstractmethod
    def one_inch_source_quote(
        self, step: p.OneInchSourceQuote, state: State
    ) -> Evaluation:
        return Evaluation(state=state)

    @abstractmethod
    def one_inch_target_quote(
        self, step: p.OneInchTargetQuote, state: State
    ) -> Evaluation:
        return Evaluation(state=state)

    @abstractmethod
    def forecast_borrow_limit_fraction_after_swap_within_limit(
        self, step: p.ForecastBorrowLimitFractionAfterSwapWithinLimit, state: State
    ) -> Evaluation:
        return Evaluation(state=state)

    @abstractmethod
    def redeemable(self, step: p.Redeemable, state: State) -> Evaluation:
        return Evaluation(state=state)

    @abstractmethod
    def redeem(self, step: p.Redeem, state: State) -> Evaluation:
        return Evaluation(state=state)

    @abstractmethod
    def repay(self, step: p.Repay, state: State) -> Evaluation:
        return Evaluation(state=state)

    @abstractmethod
    def set_one_inch_allowance(
        self, step: p.SetOneInchAllowance, state: State
    ) -> Evaluation:
        return Evaluation(state=state)

    @abstractmethod
    def one_inch_swap(self, step: p.OneInchSwap, state: State) -> Evaluation:
        return Evaluation(state=state)

    @abstractmethod
    def comp_accrued(self, step: p.CompAccrued, state: State) -> Evaluation:
        return Evaluation(state=state)

    @abstractmethod
    def harvest_comp(self, step: p.HarvestComp, state: State) -> Evaluation:
        return Evaluation(state=state)

    @abstractmethod
    def estimate_harvest_cost(
        self, step: p.EstimateHarvestCost, state: State
    ) -> Evaluation:
        return Evaluation(state=state)

    @abstractmethod
    def stability_pool_check(
        self, step: p.StabilityPoolCheck, state: State
    ) -> Evaluation:
        return Evaluation(state=state)

    @abstractmethod
    def liquity_exit_check(self, step: p.LiquityExitCheck, state: State) -> Evaluation:
        return Evaluation(state=state)

    @abstractmethod
    def store_min_gas_balance(
        self, step: p.StoreMinGasBalance, state: State
    ) -> Evaluation:
        return Evaluation(state=state)

    @abstractmethod
    def calculate_difference(
        self, step: p.CalculateDifference, state: State
    ) -> Evaluation:
        return Evaluation(state=state)

    @abstractmethod
    def calculate_lqty_apr(
        self, step: p.CalculateLiquityAPR, state: State
    ) -> Evaluation:
        return Evaluation(state=state)

    @abstractmethod
    def lqty_accrued(self, step: p.LQTYAccrued, state: State) -> Evaluation:
        return Evaluation(state=state)

    @abstractmethod
    def eth_accrued(self, step: p.ETHAccrued, state: State) -> Evaluation:
        return Evaluation(state=state)

    @abstractmethod
    def harvest_lqty(self, step: p.HarvestLQTY, state: State) -> Evaluation:
        return Evaluation(state=state)

    @abstractmethod
    def deposit_lusd(self, step: p.DepositLUSD, state: State) -> Evaluation:
        return Evaluation(state=state)

    @abstractmethod
    def withdraw_from_sp(self, step: p.WithdrawLUSD, state: State) -> Evaluation:
        return Evaluation(state=state)

    @abstractmethod
    def report_result(self, step: p.ReportResult, state: State) -> Evaluation:
        return Evaluation(state=state)

    @abstractmethod
    def convert_eth_to_weth(self, step: p.ConvertETHToWETH, state: State) -> Evaluation:
        return Evaluation(state=state)
