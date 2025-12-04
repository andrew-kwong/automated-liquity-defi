from dataclasses import dataclass

from automated_defi.pipeline import pipeline as p
from automated_defi.pipeline.evaluation import Evaluation, State, Visitor


@dataclass
class PrintExecutor(Visitor):
    """
    An executor just logging the step's string representation. Evaluates
    expressions once to True, then False in subsequent evaluations.
    """

    def __init__(self) -> None:
        super().__init__()
        self.log: list[str] = []

    def transform(self, step: p.Transform, state: State) -> Evaluation:
        self.log.append(str(step))
        return Evaluation(state=state)

    def expr(self, step: p.Expr, state: State) -> Evaluation:
        self.log.append(str(step))
        # make sure condition is returns True once
        state["_condition_"] = state.get(step.slug, True)
        state[step.slug] = False
        return Evaluation(state=state)

    def setup(self, step: p.Setup, state: State) -> Evaluation:
        self.log.append(str(step))
        return Evaluation(state=state)

    def balance(self, step: p.Balance, state: State) -> Evaluation:
        self.log.append(str(step))
        return Evaluation(state=state)

    def prices(self, step: p.Prices, state: State) -> Evaluation:
        self.log.append(str(step))
        return Evaluation(state=state)

    def borrow_limit_fraction(
        self, step: p.BorrowLimitFraction, state: State
    ) -> Evaluation:
        self.log.append(str(step))
        return Evaluation(state=state)

    def borrow_limit(self, step: p.BorrowLimit, state: State) -> Evaluation:
        self.log.append(str(step))
        return Evaluation(state=state)

    def borrow_balance(self, step: p.BorrowBalance, state: State) -> Evaluation:
        self.log.append(str(step))
        return Evaluation(state=state)

    def borrow(self, step: p.Borrow, state: State) -> Evaluation:
        self.log.append(str(step))
        return Evaluation(state=state)

    def transfer(self, step: p.Balance, state: State) -> Evaluation:
        self.log.append(str(step))
        return Evaluation(state=state)

    def set_allowance(self, step: p.SetAllowance, state: State) -> Evaluation:
        self.log.append(str(step))
        return Evaluation(state=state)

    def set_contract_allowance(
        self, step: p.SetContractAllowance, state: State
    ) -> Evaluation:
        self.log.append(str(step))
        return Evaluation(state=state)

    def allowance(self, step: p.Allowance, state: State) -> Evaluation:
        self.log.append(str(step))
        return Evaluation(state=state)

    def give_collateral(self, step: p.GiveCollateral, state: State) -> Evaluation:
        self.log.append(str(step))
        return Evaluation(state=state)

    def supply(self, step: p.Supply, state: State) -> Evaluation:
        self.log.append(str(step))
        return Evaluation(state=state)

    def c_token_equivalent(self, step: p.CTokenEquivalent, state: State) -> Evaluation:
        self.log.append(str(step))
        return Evaluation(state=state)

    def one_inch_source_quote(
        self, step: p.OneInchSourceQuote, state: State
    ) -> Evaluation:
        self.log.append(str(step))
        return Evaluation(state=state)

    def one_inch_target_quote(
        self, step: p.OneInchTargetQuote, state: State
    ) -> Evaluation:
        self.log.append(str(step))
        return Evaluation(state=state)

    def forecast_borrow_limit_fraction_after_swap_within_limit(
        self, step: p.ForecastBorrowLimitFractionAfterSwapWithinLimit, state: State
    ) -> Evaluation:
        self.log.append(str(step))
        return Evaluation(state=state)

    def redeemable(self, step: p.Redeemable, state: State) -> Evaluation:
        self.log.append(str(step))
        return Evaluation(state=state)

    def redeem(self, step: p.Redeem, state: State) -> Evaluation:
        self.log.append(str(step))
        return Evaluation(state=state)

    def repay(self, step: p.Repay, state: State) -> Evaluation:
        self.log.append(str(step))
        return Evaluation(state=state)

    def set_one_inch_allowance(
        self, step: p.SetOneInchAllowance, state: State
    ) -> Evaluation:
        self.log.append(str(step))
        return Evaluation(state=state)

    def one_inch_swap(self, step: p.OneInchSwap, state: State) -> Evaluation:
        self.log.append(str(step))
        return Evaluation(state=state)

    def comp_accrued(self, step: p.CompAccrued, state: State) -> Evaluation:
        self.log.append(str(step))
        return Evaluation(state=state)

    def harvest_comp(self, step: p.HarvestComp, state: State) -> Evaluation:
        self.log.append(str(step))
        return Evaluation(state=state)

    def estimate_harvest_cost(
        self, step: p.EstimateHarvestCost, state: State
    ) -> Evaluation:
        self.log.append(str(step))
        return Evaluation(state=state)

    def stability_pool_check(
        self, step: p.StabilityPoolCheck, state: State
    ) -> Evaluation:
        self.log.append(str(step))
        return Evaluation(state=state)

    def liquity_exit_check(self, step: p.LiquityExitCheck, state: State) -> Evaluation:
        self.log.append(str(step))
        return Evaluation(state=state)

    def store_min_gas_balance(
        self, step: p.StoreMinGasBalance, state: State
    ) -> Evaluation:
        self.log.append(str(step))
        return Evaluation(state=state)

    def calculate_difference(
        self, step: p.CalculateDifference, state: State
    ) -> Evaluation:
        self.log.append(str(step))
        return Evaluation(state=state)

    def calculate_lqty_apr(
        self, step: p.CalculateLiquityAPR, state: State
    ) -> Evaluation:
        self.log.append(str(step))
        return Evaluation(state=state)

    def lqty_accrued(self, step: p.LQTYAccrued, state: State) -> Evaluation:
        self.log.append(str(step))
        return Evaluation(state=state)

    def eth_accrued(self, step: p.ETHAccrued, state: State) -> Evaluation:
        self.log.append(str(step))
        return Evaluation(state=state)

    def harvest_lqty(self, step: p.HarvestLQTY, state: State) -> Evaluation:
        self.log.append(str(step))
        return Evaluation(state=state)

    def deposit_lusd(self, step: p.DepositLUSD, state: State) -> Evaluation:
        self.log.append(str(step))
        return Evaluation(state=state)

    def withdraw_from_sp(self, step: p.WithdrawLUSD, state: State) -> Evaluation:
        self.log.append(str(step))
        return Evaluation(state=state)

    def convert_eth_to_weth(self, step: p.ConvertETHToWETH, state: State) -> Evaluation:
        self.log.append(f"{step!s}: {state!s}")
        return Evaluation(state=state)

    def report_result(self, step: p.ReportResult, state: State) -> Evaluation:
        self.log.append(f"{step!s}: {state!s}")
        return Evaluation(state=state)
