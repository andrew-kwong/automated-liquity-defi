from __future__ import annotations

import logging
from abc import ABC
from copy import deepcopy
from dataclasses import dataclass, field, fields, replace
from decimal import Decimal
from functools import cached_property
from gettext import gettext as _
from typing import (
    TYPE_CHECKING,
    Callable,
    Dict,
    Generator,
    List,
    NamedTuple,
    NewType,
    Optional,
    Tuple,
    Union,
)

from automated_defi.errors import (
    InvalidChainEffectError,
    InvalidFormalParamError,
    InvalidFormalParamTypeError,
    InvalidParamTypeError,
    InvalidReferenceError,
    MissingParamError,
)
from automated_defi.eth import assets
from automated_defi.pipeline.params import Param, Ref
from automated_defi.protocol.chain import (
    DEFAULT_ESTIMATED_GAS_SURPLUS,
    DEFAULT_PRIORITY_FEE,
)
from automated_defi.utils import DataclassEncoderMixin, camel_to_snake, nested

if TYPE_CHECKING:
    # avoid cyclic imports
    from automated_defi.pipeline.evaluation import State, Visitor

logger = logging.getLogger(__name__)

Path = NewType("Path", List[str])


class Evaluation(NamedTuple):
    """An actual evaluation of a step leading to a (modified) state and information about its effects."""

    state: State
    chain_effect: bool = False


class Pipeline:
    """A pipeline defines a parameterized control flow consisting of nested steps.

    The steps build a hierarchy that can be traversed for static preparate or analysis.
    It can also be run by an executor using the visitor pattern.

    A simple pipeline definition and run invocation looks like this:

        pipeline=p.Pipeline(
            p.Group(
                slug="pipeline",
                steps=[
                    p.Setup(),
                    p.Balance(token=Param[str](key="token", default="ETH")),
                    p.ReportResult(
                        func=lambda state: state.get("ETH_balance", None)
                    ),
                ],
            )
        )

        # build dict of user-defined and externally provided parameters
        params={
            "eth_account": {
                "address": "0x27D41B00071221365d7c06aa33F14201462b3327",
                "slug": "simon",
            },
            'pipeline': {
                'balance': {'token': 'ETH'},
            }
        }
        executor = MyExecutor()(
            params=params
        )

        # run the pipeline
        res = pipeline(executor, params)
    """

    def __init__(self, root: Step = None) -> None:
        if not root:
            root = Group(slug="main")
        self.root = root
        self._init_slugs()

    def _init_slugs(self):
        """Assigns globally unique slugs to pipeline's steps or validates uniqueness of user-provided slugs."""
        seen = set()
        for __, el in self.root.walk():
            if el.slug:
                # check that pre-assigned, non-empty slug is unique
                if el.slug in seen:
                    raise RuntimeError(f"duplicate slug found: {el.slug}")
                seen.add(el.slug)
                continue

            # generate a unique slug from step name in the format <step_name>_<1, 2, ...>
            base_slug = camel_to_snake(el.__class__.__name__)
            slug = base_slug
            i = 1

            while slug in seen:
                slug = "{}_{}".format(base_slug, i)
                i += 1

            el.slug = slug
            seen.add(el.slug)

    @property
    def params(self) -> dict:
        p = {}
        for path, step in self.root.walk():
            nested(p, path).update(step.params)
        return p

    @property
    def initial_params_json(self) -> dict:
        user_params: Dict[str, Optional[Union[str, int]]] = {}
        for path, step in self.root.walk():
            for param in step.params.values():
                initial = param.initial
                if initial is None:
                    pass
                elif isinstance(initial, Decimal):
                    initial = initial.to_eng_string()
                elif isinstance(initial, (str, bool, int)):
                    pass
                else:
                    raise TypeError(
                        f"unexpected type {type(initial)} received from Param.initial"
                    )
                nested(user_params, path)[param.key] = initial
        return user_params

    def __call__(self, executor: Visitor, user_params: Optional[dict] = None) -> State:
        if not user_params:
            user_params = {}
        return self.root.accept(
            executor,
            state={},
            user_params=user_params.get(self.root.slug, None) or {},
        ).state


@dataclass
class Step(DataclassEncoderMixin, ABC):
    slug: str = ""
    """Should be initialized to a fixed slug, stable over redefinitions of the same (even similar?) pipelines. This makes it possible to correlate transactions to steps in reporting and analytics."""

    @cached_property
    def get_description(self) -> Optional[str]:
        """human readable description"""
        return None

    @classmethod
    def _formal_params(cls) -> dict:
        return {
            f.name: getattr(cls, f.name)
            for f in fields(cls)
            if hasattr(cls, f.name) and isinstance(getattr(cls, f.name), Param)
        }

    @property
    def params(self) -> dict:
        p = {}
        for f in fields(self):
            value = getattr(self, f.name)
            # only add parameters left unset for user to be chosen
            if isinstance(value, Param):
                p[value.key] = value
        return p

    def _prepare_args(self, state: State, user_params: dict) -> Step:
        """Merges fixed step parameters with actual parameters, validating type and existence of required parameters.

        Returns a copy of this step with no more `Param` typed fields but actual and valid values.
        """
        # Field name -> actual parameter value or None if not required
        actual_params: Dict[str, Optional[Union[str, bool, int, Decimal]]] = {}
        for f, formal_param in self._formal_params().items():
            p = getattr(self, f)

            if isinstance(p, (str, bool, int, Decimal)):
                try:
                    actual = formal_param.type(p)
                except Exception:
                    raise InvalidParamTypeError(self.slug, formal_param.key, p)
                if actual is None and formal_param.required:
                    raise InvalidFormalParamError(self.slug, f, p)
                actual_params[f] = actual
            elif isinstance(p, Param):
                user_param = user_params.get(p.key, p.default)
                actual = None
                if user_param is None or user_param == "":
                    if p.required:
                        raise MissingParamError(self.slug, p.key)
                else:
                    try:
                        actual = p.type(user_param)
                    except Exception:
                        raise InvalidParamTypeError(self.slug, p.key, user_param)
                actual_params[f] = actual
            elif isinstance(p, Ref):
                actual_params[f] = state.get(p.key, p.default)
                if actual_params[f] is None and p.required:
                    raise InvalidReferenceError(self.slug, p.key)
            else:
                raise InvalidFormalParamTypeError(self.slug, f, p)
        return replace(self, **actual_params)

    def accept(self, visitor: Visitor, state: State, user_params: dict) -> Evaluation:
        # default to NOOP and passing on state as output of this step
        return Evaluation(state)

    def walk(self, path: Path = None) -> Generator[tuple[Path, Step], None, None]:
        if path is None:
            path = []
        yield (Path([*path, self.slug]), self)


class Write(Step, ABC):
    def accept(self, visitor: Visitor, state: State, user_params: dict) -> Evaluation:
        # default to NOOP and passing on state as output of this step
        return Evaluation(State)


class Read(Step, ABC):
    pass


@dataclass
class Transform(Step):
    func: Callable = field(
        hash=False,
        compare=False,
        default=lambda state: False,
        repr=False,
    )
    args: List[Union[Param, str, int, bool, Decimal]] = field(default_factory=list)

    @property
    def params(self) -> dict:
        return {arg.key: arg for arg in self.args if isinstance(arg, Param)}

    def _prepare_args(self, state: State, user_params: dict) -> Step:
        # already returns a modified copy of self
        expr = super()._prepare_args(state, user_params)
        # saver to create fixed-sized and access by index
        actual_args = [None] * len(self.args)
        for i, p in enumerate(self.args):
            if isinstance(p, (str, bool, int, Decimal)):
                actual_args[i] = p
            elif isinstance(p, Param):
                user_param = user_params.get(p.key, p.default)
                actual = None
                if user_param is None or user_param == "":
                    if p.required:
                        raise MissingParamError(self.slug, f"args[{i}], key={p.key}")
                else:
                    try:
                        actual = p.type(user_param) if user_param is not None else None
                    except Exception:
                        raise InvalidParamTypeError(
                            self.slug, f"args[{i}], key={p.key}", user_param
                        )
                actual_args[i] = actual
            elif isinstance(p, Ref):
                actual_args[i] = state.get(p.key, p.default)
                if actual_args[i] is None and p.required:
                    raise InvalidReferenceError(self.slug, p.key)
            else:
                raise InvalidFormalParamTypeError(self.slug, f"args[{i}]", p)
        expr.args = actual_args
        return expr

    def accept(self, visitor: Visitor, state: State, user_params: dict) -> Evaluation:
        return visitor.transform(
            self._prepare_args(state, user_params), deepcopy(state)
        )


@dataclass
class Expr(Transform):
    def accept(self, visitor: Visitor, state: State, user_params: dict) -> Evaluation:
        return visitor.expr(self._prepare_args(state, user_params), deepcopy(state))


@dataclass
class Group(Step):
    description: Optional[str] = None
    given: List[Read] = field(default_factory=list)
    entry_condition: Optional[Expr] = None
    steps: List[Step] = field(default_factory=list)
    hide_details: Optional[bool] = False

    @cached_property
    def get_description(self) -> Optional[str]:
        return self.description

    def _eval_condition(
        self, visitor: Visitor, state: State, user_params: dict
    ) -> Tuple[State, bool]:
        for step in self.given:
            state, chain_effect = step.accept(
                visitor, state, user_params.get(step.slug, {})
            )
            if chain_effect:
                raise InvalidChainEffectError(
                    step_slug=step.slug, caller=f"{self.slug}.given"
                )
        if self.entry_condition:
            state, chain_effect = self.entry_condition.accept(
                visitor, state, user_params.get(self.entry_condition.slug, {})
            )
            if chain_effect:
                raise InvalidChainEffectError(
                    step_slug=self.entry_condition,
                    caller=f"{self.slug}.entry_condition",
                )
            return state, state.get("_condition_", False)
        else:
            return state, True

    def accept(self, visitor: Visitor, state: State, user_params: dict) -> Evaluation:
        self = self._prepare_args(state, user_params)
        state = visitor.enter_group(self, deepcopy(state))

        state, condition = self._eval_condition(visitor, state, user_params)
        any_chain_effect = False
        if condition:
            for step in self.steps:
                state, chain_effect = step.accept(
                    visitor, state, user_params.get(step.slug, {})
                )
                any_chain_effect = any_chain_effect or chain_effect

        state = visitor.exit_group(self, deepcopy(state))
        return Evaluation(state, any_chain_effect)

    def walk(self, path: List[str] = None) -> Generator[Tuple[Path, Step], None, None]:
        if path is None:
            path = []
        p = Path([*path, self.slug])
        yield (p, self)
        for step in self.given:
            yield from step.walk(p)
        if self.entry_condition:
            yield from self.entry_condition.walk(p)
        for step in self.steps:
            yield from step.walk(p)


@dataclass
class Repeat(Group):
    max: int = Param[int](
        key="max",
        type=int,
        default=50,
    )
    entry_condition: Optional[Expr] = None

    @cached_property
    def get_description(self) -> Optional[str]:
        return self.description

    def accept(self, visitor: Visitor, state: State, user_params: dict) -> Evaluation:
        self = self._prepare_args(state, user_params)
        state = visitor.enter_repeat(self, deepcopy(state))

        any_chain_effect = False
        c = 0
        for c in range(self.max):
            # use state updated by steps below for entry_condition reevaluation
            state, condition = self._eval_condition(visitor, state, user_params)
            if not condition:
                break

            for step in self.steps:
                state, chain_effect = step.accept(
                    visitor, state, user_params.get(step.slug, {})
                )
                any_chain_effect = any_chain_effect or chain_effect

            # cancel loop as soon as one iteration did not produce any side effects
            if not any_chain_effect:
                break

        if c >= self.max - 1:
            # TODO later we may make this a hard error that aborts the pipeline immediately
            logger.warn("maximum iterations reached for Repeat Group")

        state = visitor.exit_repeat(self, deepcopy(state))
        return Evaluation(state, any_chain_effect)


@dataclass
class Setup(Step):
    estimated_gas_surplus: Union[Param, int] = Param[int](
        name=_("Estimated gas surplus"),
        key="estimated_gas_surplus",
        type=int,
        default=DEFAULT_ESTIMATED_GAS_SURPLUS,
    )
    max_priority_fee: Union[Param, assets.GWEI] = Param[str](
        name=_("Max priority fee"),
        key="max_priority_fee",
        type=assets.GWEI,
        default=DEFAULT_PRIORITY_FEE,
    )

    def accept(self, visitor: Visitor, state: State, user_params: dict) -> Evaluation:
        return visitor.setup(self._prepare_args(state, user_params), deepcopy(state))


@dataclass
class Balance(Read):
    token: Union[Param, str] = Param[str](
        name=_("Token"), key="token", type=str, default="ETH"
    )

    @cached_property
    def get_description(self) -> Optional[str]:
        return _("Get balance of a token.")

    def accept(self, visitor: Visitor, state: State, user_params: dict) -> Evaluation:
        return visitor.balance(self._prepare_args(state, user_params), deepcopy(state))


@dataclass
class Prices(Read):
    tokens: Union[Param, str] = Param[str](
        name=_("Tokens"), key="tokens", type=str, default="ETH"
    )

    @cached_property
    def get_description(self) -> Optional[str]:
        return _("Get USD prices of comma separated list of tokens.")

    def accept(self, visitor: Visitor, state: State, user_params: dict) -> Evaluation:
        return visitor.prices(self._prepare_args(state, user_params), deepcopy(state))


@dataclass
class BorrowLimit(Read):
    token: Union[Param, str] = Param[str](
        name=_("Token"), key="token", type=str, default="ETH"
    )
    borrow_limit_fraction: Union[Param, Decimal] = Param[Decimal](
        key="borrow_limit_fraction",
        type=Decimal,
        default=Decimal("0.8"),
    )

    @cached_property
    def get_description(self) -> Optional[str]:
        return _(
            "Get borrow limit of `token` such that `borrow_limit_fraction` is not exceeded, or 0 if limit is already reached/exceeded."
        )

    def accept(self, visitor: Visitor, state: State, user_params: dict) -> Evaluation:
        return visitor.borrow_limit(
            self._prepare_args(state, user_params), deepcopy(state)
        )


@dataclass
class BorrowLimitFraction(Read):
    @cached_property
    def get_description(self) -> Optional[str]:
        return _("Calculates the fraction used of borrow limit.")

    def accept(self, visitor: Visitor, state: State, user_params: dict) -> Evaluation:
        return visitor.borrow_limit_fraction(
            self._prepare_args(state, user_params), deepcopy(state)
        )


@dataclass
class BorrowBalance(Read):
    token: Union[Param, str] = Param[str](
        name=_("Token"), key="token", type=str, default="ETH"
    )

    @cached_property
    def get_description(self) -> Optional[str]:
        return _("Get current borrow amount of `token`.")

    def accept(self, visitor: Visitor, state: State, user_params: dict) -> Evaluation:
        return visitor.borrow_balance(
            self._prepare_args(state, user_params), deepcopy(state)
        )


@dataclass
class Borrow(Write):
    token: Union[Param, str] = Param[str](
        name=_("Token"), key="token", type=str, default="ETH"
    )
    amount: Union[Param, assets.Token] = Param[assets.Token](
        name=_("Amount"), key="amount", type=assets.Token
    )

    @cached_property
    def get_description(self) -> Optional[str]:
        return _("Borrow a token.")

    def accept(self, visitor: Visitor, state: State, user_params: dict) -> Evaluation:
        return visitor.borrow(self._prepare_args(state, user_params), deepcopy(state))


@dataclass
class Transfer(Write):
    token: Union[Param, str] = Param[str](
        name=_("Token"), key="token", type=str, default="ETH"
    )
    to: Union[Param, str] = Param[str](
        name=_("Address"), key="address", type=str, default="0x"
    )
    amount: Union[Param, assets.ERC20Asset] = Param[assets.ERC20Asset](
        name=_("Amount"), key="amount", type=assets.ERC20Asset
    )

    @cached_property
    def get_description(self) -> Optional[str]:
        return _("Transfer a token.")

    def accept(self, visitor: Visitor, state: State, user_params: dict) -> Evaluation:
        return visitor.transfer(self._prepare_args(state, user_params), deepcopy(state))


@dataclass
class SetAllowance(Write):
    token: Union[Param, str] = Param[str](
        name=_("Token"), key="token", type=str, default="ETH"
    )
    amount: Union[Param, assets.Token] = Param[assets.Token](
        name=_("Amount"), key="amount", type=assets.Token, default=Decimal(1)
    )
    set_unlimited: Union[Param, bool] = Param[bool](
        name=_("Set unlimited"), key="set_unlimited", type=bool, default=True
    )

    @cached_property
    def get_description(self) -> Optional[str]:
        return _(
            "Sets the maximum allowed amount to use by the c-token contract belonging to `token`. Only executes if the current allowance is smaller then `amount`. In this case, `set_unlimited` decides if we are setting the exact `amount` or unlimited (2^255-1) allowance."
        )

    def accept(self, visitor: Visitor, state: State, user_params: dict) -> Evaluation:
        return visitor.set_allowance(
            self._prepare_args(state, user_params), deepcopy(state)
        )


@dataclass
class SetContractAllowance(Write):
    token: Union[Param, str] = Param[str](
        name=_("Token"), key="token", type=str, default="ETH"
    )
    spender_contract: Union[Param, str] = Param[str](
        name=_("Spender contract address"), key="spender_contract", type=str
    )
    amount: Union[Param, assets.Token] = Param[assets.Token](
        name=_("Amount"), key="amount", type=assets.Token, default=Decimal(1)
    )
    set_unlimited: Union[Param, bool] = Param[bool](
        name=_("Set unlimited"), key="set_unlimited", type=bool, default=True
    )

    @cached_property
    def get_description(self) -> Optional[str]:
        return _(
            "Sets the maximum allowed amount to use by spender contract. Only executes if the current allowance is smaller then `amount`. In this case, `set_unlimited` decides if we are setting the exact `amount` or unlimited (2^255-1) allowance."
        )

    def accept(self, visitor: Visitor, state: State, user_params: dict) -> Evaluation:
        return visitor.set_contract_allowance(
            self._prepare_args(state, user_params), deepcopy(state)
        )


@dataclass
class Allowance(Read):
    token: Union[Param, str] = Param[str](
        name=_("Token"), key="token", type=str, default="ETH"
    )

    @cached_property
    def get_description(self) -> Optional[str]:
        return _("Fetches the max allowed amount to use as collateral.")

    def run(self, visitor: Visitor, state: State, user_params: dict) -> Evaluation:
        return visitor.allowance(
            self._prepare_args(state, user_params), deepcopy(state)
        )


@dataclass
class GiveCollateral(Write):
    c_token: Union[Param, str] = Param[str](name=_("CToken"), type=str, key="c_token")

    @cached_property
    def get_description(self) -> Optional[str]:
        return _("Provides collateral.")

    def accept(self, visitor: Visitor, state: State, user_params: dict) -> Evaluation:
        return visitor.give_collateral(
            self._prepare_args(state, user_params), deepcopy(state)
        )


@dataclass
class Supply(Write):
    token: Union[Param, str] = Param[str](name=_("Token"), type=str, key="token")
    target_amount_supplied: Union[Param, assets.Token] = Param[assets.Token](
        name=_("Target amount (lower bound)"),
        key="target_amount_supplied",
        type=assets.Token,
    )

    @cached_property
    def get_description(self) -> Optional[str]:
        return _(
            "Supplies as much as necessary to have at least 'target amount' of 'token' supplied into Compound."
        )

    def accept(self, visitor: Visitor, state: State, user_params: dict) -> Evaluation:
        return visitor.supply(self._prepare_args(state, user_params), deepcopy(state))


@dataclass
class Redeemable(Read):
    c_token: Union[Param, str] = Param[str](
        name=_("C-token to redeem"), type=str, key="c_token"
    )
    borrow_limit_fraction: Union[Param, Decimal] = Param[Decimal](
        key="borrow_limit_fraction",
        type=Decimal,
        default=Decimal("0.9"),
    )

    @cached_property
    def get_description(self) -> Optional[str]:
        return _(
            "Calculates (exactly) the redeemable amount of `c_token` such that we remain within `borrow_limit_fraction`, or 0 if this fraction is already exceeded."
        )

    def accept(self, visitor: Visitor, state: State, user_params: dict) -> Evaluation:
        return visitor.redeemable(
            self._prepare_args(state, user_params), deepcopy(state)
        )


@dataclass
class Redeem(Write):
    c_token: Union[Param, str] = Param[str](name=_("CToken"), type=str, key="c_token")
    amount: Union[Param, assets.CToken] = Param[assets.CToken](
        name=_("Amount"),
        key="amount",
        type=assets.CToken,
    )

    @cached_property
    def get_description(self) -> Optional[str]:
        return _("Redeems `amount` `c_token` supplied to Compound.")

    def accept(self, visitor: Visitor, state: State, user_params: dict) -> Evaluation:
        return visitor.redeem(self._prepare_args(state, user_params), deepcopy(state))


@dataclass
class Repay(Write):
    token: Union[Param, str] = Param[str](name=_("Token"), type=str, key="token")
    amount: Union[Param, assets.Token] = Param[assets.Token](
        name=_("Amount"),
        key="amount",
        type=assets.Token,
    )
    remaining: Union[Param, bool] = Param[bool](
        name=_("Repay remaining"), key="remaining", type=bool, default=True
    )

    @cached_property
    def get_description(self) -> Optional[str]:
        return _("Repays `amount` `token` borrowed from Compound.")

    def accept(self, visitor: Visitor, state: State, user_params: dict) -> Evaluation:
        return visitor.repay(self._prepare_args(state, user_params), deepcopy(state))


@dataclass
class CompAccrued(Read):
    @cached_property
    def get_description(self) -> Optional[str]:
        return _("Get amound accrued COMP from Compound protocol.")

    def accept(self, visitor: Visitor, state: State, user_params: dict) -> Evaluation:
        return visitor.comp_accrued(
            self._prepare_args(state, user_params), deepcopy(state)
        )


@dataclass
class HarvestComp(Write):
    @cached_property
    def get_description(self) -> Optional[str]:
        return _("Harvest accrued COMP from Compound.")

    def accept(self, visitor: Visitor, state: State, user_params: dict) -> Evaluation:
        return visitor.harvest_comp(
            self._prepare_args(state, user_params), deepcopy(state)
        )


@dataclass
class LQTYAccrued(Read):
    @cached_property
    def get_description(self) -> Optional[str]:
        return _("Get amount of accrued LQTY from Liquity protocol.")

    def accept(self, visitor: Visitor, state: State, user_params: dict) -> Evaluation:
        return visitor.lqty_accrued(
            self._prepare_args(state, user_params), deepcopy(state)
        )


@dataclass
class ETHAccrued(Read):
    @cached_property
    def get_description(self) -> Optional[str]:
        return _("Get amount of accrued ETH from Liquity protocol.")

    def accept(self, visitor: Visitor, state: State, user_params: dict) -> Evaluation:
        return visitor.eth_accrued(
            self._prepare_args(state, user_params), deepcopy(state)
        )


@dataclass
class HarvestLQTY(Write):
    @cached_property
    def get_description(self) -> Optional[str]:
        return _(
            "Deposit LUSD to stability pool and/or Harvest accrued LQTY/ETH from Liquity."
        )

    def accept(self, visitor: Visitor, state: State, user_params: dict) -> Evaluation:
        return visitor.harvest_lqty(
            self._prepare_args(state, user_params), deepcopy(state)
        )


@dataclass
class DepositLUSD(Write):
    amount: Union[Param, assets.Token] = Param[assets.Token](
        name=_("Amount"), key="amount", type=assets.Token
    )

    @cached_property
    def get_description(self) -> Optional[str]:
        return _(
            "Deposit LUSD to stability pool and/or Harvest accrued LQTY/ETH from Liquity."
        )

    def accept(self, visitor: Visitor, state: State, user_params: dict) -> Evaluation:
        return visitor.deposit_lusd(
            self._prepare_args(state, user_params), deepcopy(state)
        )


@dataclass
class WithdrawLUSD(Write):
    amount: Union[Param, assets.Token] = Param[assets.Token](
        name=_("Amount"), key="amount", type=assets.Token
    )

    @cached_property
    def get_description(self) -> Optional[str]:
        return _(
            "Withdraws LUSD from stabiliy pool and/or Harvest accrued LQTY/ETH from Liquity."
        )

    def accept(self, visitor: Visitor, state: State, user_params: dict) -> Evaluation:
        return visitor.withdraw_from_sp(
            self._prepare_args(state, user_params), deepcopy(state)
        )


@dataclass
class EstimateHarvestCost(Step):
    gas_speed: Union[Param, str] = Param[str](
        name=_("Gas Speed Selection"), key="gas_speed", type=str, default="average"
    )
    factor: Union[Param, Decimal] = Param[Decimal](
        name=_("Factor Gas Multiplier"),
        key="factor",
        type=Decimal,
        default=Decimal(1),
    )

    @cached_property
    def get_description(self) -> Optional[str]:
        return _(
            "User inputs for gas selection (fast, average, or safe) and factor multiplier inorder to estimate harvest threshold."
        )

    def accept(self, visitor: Visitor, state: State, user_params: dict) -> Evaluation:
        return visitor.estimate_harvest_cost(
            self._prepare_args(state, user_params), deepcopy(state)
        )


class StabilityPoolCheck(Read):
    @cached_property
    def get_description(self) -> Optional[str]:
        return _("Checks for the amount of LUSD in the stability pool")

    def accept(self, visitor: Visitor, state: State, user_params: dict) -> Evaluation:
        return visitor.stability_pool_check(
            self._prepare_args(state, user_params), deepcopy(state)
        )


@dataclass
class LiquityExitCheck(Read):
    @cached_property
    def get_description(self) -> Optional[str]:
        return _(
            "Double check for any possible remaining LUSD, LQTY, and ETH balances left over"
        )

    def accept(self, visitor: Visitor, state: State, user_params: dict) -> Evaluation:
        return visitor.liquity_exit_check(
            self._prepare_args(state, user_params), deepcopy(state)
        )


@dataclass
class StoreMinGasBalance(Step):
    min_gas_balance: Union[Param, assets.ETH] = Param[assets.ETH](
        name=_("Minimum ETH balance to swap"),
        key="min_gas_balance",
        type=assets.ETH,
        default=Decimal(0.5),
    )

    @cached_property
    def get_description(self) -> Optional[str]:
        return _(
            "Stores minimum ETH gas balance left over in the wallet specified by the user"
        )

    def accept(self, visitor: Visitor, state: State, user_params: dict) -> Evaluation:
        return visitor.store_min_gas_balance(
            self._prepare_args(state, user_params), deepcopy(state)
        )


@dataclass
class CalculateDifference(Read):
    @cached_property
    def get_description(self) -> Optional[str]:
        return _(
            "Calculates the difference to swap from the ETH balance in wallet - minimum ETH gas balance specified by the user"
        )

    def accept(self, visitor: Visitor, state: State, user_params: dict) -> Evaluation:
        return visitor.calculate_difference(
            self._prepare_args(state, user_params), deepcopy(state)
        )


@dataclass
class CalculateLiquityAPR(Read):
    @cached_property
    def get_description(self) -> Optional[str]:
        return _(
            "Calculates LQTY APR, which is an estimate of the LQTY return on the LUSD deposited to the Stability Pool over the next year, not including your ETH gains from liquidations."
        )

    def accept(self, visitor: Visitor, state: State, user_params: dict) -> Evaluation:
        return visitor.calculate_lqty_apr(
            self._prepare_args(state, user_params), deepcopy(state)
        )


@dataclass
class ForecastBorrowLimitFractionAfterSwapWithinLimit(Read):
    source_token: Union[Param, str] = Param[str](
        name=_("From"), type=str, key="source_token"
    )
    target_token: Union[Param, str] = Param[str](
        name=_("To"), type=str, key="target_token"
    )
    amount: Union[Param, assets.ERC20Asset] = Param[assets.ERC20Asset](
        name=_("Amount"), key="amount", type=assets.ERC20Asset
    )
    target_amount: Union[Param, assets.ERC20Asset] = Param[assets.ERC20Asset](
        name=_("Target Amount"), key="target_amount", type=assets.ERC20Asset
    )
    borrow_limit_fraction: Union[Param, Decimal] = Param[Decimal](
        key="borrow_limit_fraction",
        type=Decimal,
        default=Decimal("0.9"),
    )

    @cached_property
    def get_description(self) -> Optional[str]:
        return _(
            "Forecasts the (worst case) borrow limit after swapping `amount` `source_token` into `target_token` and raises if that limit is above `borrow_limit_fraction`."
        )

    def accept(self, visitor: Visitor, state: State, user_params: dict) -> Evaluation:
        return visitor.forecast_borrow_limit_fraction_after_swap_within_limit(
            self._prepare_args(state, user_params), deepcopy(state)
        )


@dataclass
class OneInchTargetQuote(Read):
    source_token: Union[Param, str] = Param[str](
        name=_("From"), type=str, key="source_token"
    )
    target_token: Union[Param, str] = Param[str](
        name=_("To"), type=str, key="target_token"
    )
    source_amount: Union[Param, assets.ERC20Asset] = Param[assets.ERC20Asset](
        name=_("Source amount"), key="source_amount", type=assets.ERC20Asset
    )

    @cached_property
    def get_description(self) -> Optional[str]:
        return _(
            "Gets a quote from 1inch API to determine the amount of `target_token` we receive when swapping `source_amount` `source_token`."
        )

    def accept(self, visitor: Visitor, state: State, user_params: dict) -> Evaluation:
        return visitor.one_inch_target_quote(
            self._prepare_args(state, user_params), deepcopy(state)
        )


@dataclass
class OneInchSourceQuote(Read):
    source_token: Union[Param, str] = Param[str](
        name=_("From"), type=str, key="source_token"
    )
    target_token: Union[Param, str] = Param[str](
        name=_("To"), type=str, key="target_token"
    )
    target_amount: Union[Param, assets.ERC20Asset] = Param[assets.ERC20Asset](
        name=_("Target Amount"), key="target_amount", type=assets.ERC20Asset
    )
    slippage_tolerance: Union[Param, Decimal] = Param[Decimal](
        name=_("Slippage tolerance"),
        key="slippage_tolerance",
        type=Decimal,
        default=Decimal("0.015"),
    )

    @cached_property
    def get_description(self) -> Optional[str]:
        return _(
            "Gets a quote from 1inch API to approximate the conversion rate and then guess the required amount of `source_token` to receive `target_amount` `target_token` by swap."
        )

    def accept(self, visitor: Visitor, state: State, user_params: dict) -> Evaluation:
        return visitor.one_inch_source_quote(
            self._prepare_args(state, user_params), deepcopy(state)
        )


@dataclass
class SetOneInchAllowance(Write):
    token: Union[Param, str] = Param[str](
        name=_("Token"), key="token", type=str, default="ETH"
    )
    amount: Union[Param, assets.Token] = Param[assets.Token](
        name=_("Amount"), key="amount", type=assets.Token, default=Decimal(1)
    )

    @cached_property
    def get_description(self) -> Optional[str]:
        return _(
            "Sets the maximum allowed amount to use by 1inch router contract by asking 1inch's API for the best approve parameters."
        )

    def accept(self, visitor: Visitor, state: State, user_params: dict) -> Evaluation:
        return visitor.set_one_inch_allowance(
            self._prepare_args(state, user_params), deepcopy(state)
        )


@dataclass
class OneInchSwap(Write):
    source_token: Union[Param, str] = Param[str](
        name=_("From"), type=str, key="source_token"
    )
    target_token: Union[Param, str] = Param[str](
        name=_("To"), type=str, key="target_token"
    )
    amount: Union[Param, assets.ERC20Asset] = Param[assets.ERC20Asset](
        name=_("Amount"), key="amount", type=assets.ERC20Asset
    )
    expected_conversion_rate: Union[Param, Decimal] = Param[Decimal](
        name=_("Expected conversion rate"),
        key="expected_conversion_rate",
        type=Decimal,
        default=Decimal("1"),
    )
    slippage_tolerance: Union[Param, Decimal] = Param[Decimal](
        name=_("Slippage tolerance"),
        key="slippage_tolerance",
        type=Decimal,
        default=Decimal("0.015"),
    )
    """Used for checking if price is reasonable and simulation on testnets (before slippage)."""

    @cached_property
    def get_description(self) -> Optional[str]:
        return _(
            "Swap from an amount of tokens to another token using 1inch. Gets simulated by a transfer on testnets."
        )

    def accept(self, visitor: Visitor, state: State, user_params: dict) -> Evaluation:
        return visitor.one_inch_swap(
            self._prepare_args(state, user_params), deepcopy(state)
        )


@dataclass
class CTokenEquivalent(Read):
    token: Union[Param, str] = Param[str](
        name=_("Token type of amount"), type=str, key="token"
    )
    amount: Union[Param, assets.Token] = Param[assets.Token](
        name=_("Amount"), key="amount", type=assets.Token
    )

    @cached_property
    def get_description(self) -> Optional[str]:
        return _(
            "Calculates the c-token equivalent needed to receive target `amount` `token` on redeem."
        )

    def accept(self, visitor: Visitor, state: State, user_params: dict) -> Evaluation:
        return visitor.c_token_equivalent(
            self._prepare_args(state, user_params), deepcopy(state)
        )


@dataclass
class ConvertETHToWETH(Write):
    amount: Union[Param, assets.ETH] = Param[assets.ETH](
        name=_("Amount"), key="amount", type=assets.ETH
    )

    @cached_property
    def get_description(self) -> Optional[str]:
        return _("Converts ETH to WETH.")

    def accept(self, visitor: Visitor, state: State, user_params: dict) -> Evaluation:
        return visitor.convert_eth_to_weth(
            self._prepare_args(state, user_params), deepcopy(state)
        )


@dataclass
class ReportResult(Transform):
    """Reports the final result of the pipeline evaluation.

    Can appear multiple times in a strategy spec since it records results under the slug of the producing pipeline step.
    If the same step reports multiple times, e.g. in a repeat loop, results will be overwritten.
    """

    @cached_property
    def get_description(self) -> Optional[str]:
        return _("Reports an intermediate/final result of the pipeline evaluation.")

    def accept(self, visitor: Visitor, state: State, user_params: dict) -> Evaluation:
        return visitor.report_result(
            self._prepare_args(state, user_params), deepcopy(state)
        )
