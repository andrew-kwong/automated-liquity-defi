from dataclasses import dataclass
from decimal import Decimal
from functools import cached_property
from gettext import gettext as _
from typing import Type

from automated_defi.eth import assets
from automated_defi.pipeline import pipeline as p
from automated_defi.pipeline.params import Param, Ref


@dataclass(frozen=True)
class CompoundTemplate:
    source_token_type: Type[assets.Token]
    source_c_token_type: Type[assets.CToken]
    target_token_type: Type[assets.Token]
    target_c_token_type: Type[assets.CToken]

    @cached_property
    def SOURCE(self):
        return self.source_token_type.__name__

    @cached_property
    def cSOURCE(self):
        return self.source_c_token_type.__name__

    @cached_property
    def TARGET(self):
        return self.target_token_type.__name__

    @cached_property
    def cTARGET(self):
        return self.target_c_token_type.__name__

    @property
    def harvest_comp(self):
        return p.Group(
            slug="comp_harvesting",
            description=_("Harvests accrued comp."),
            given=[p.CompAccrued()],
            entry_condition=p.Expr(
                slug="accrued_COMP_above_threshold",
                func=lambda state, threshold: state["COMP_accrued"] > threshold,
                args=[
                    Param[assets.COMP](
                        key="threshold",
                        type=assets.COMP,
                        default=assets.COMP(Decimal(0)),
                    )
                ],
            ),
            steps=[
                p.HarvestComp(),
            ],
        )

    @property
    def swap_comp(self):
        return p.Group(
            slug="swap_comp",
            description=_(
                "Swaps COMP balance into c%(source_token)s (which in turn increases the collateral)."
            )
            % {"source_token": self.SOURCE},
            given=[p.Balance(token="COMP")],
            entry_condition=p.Expr(
                slug="COMP_balance_above_threshold",
                func=lambda state, threshold: state["COMP_balance"] > threshold,
                args=[
                    Param[assets.COMP](
                        key="threshold",
                        type=assets.COMP,
                        default=assets.COMP(Decimal(0)),
                    )
                ],
            ),
            steps=[
                # NOTE we can't use SetContractAllowance for COMP for unknown reasons
                p.SetOneInchAllowance(
                    slug="allow_COMP_1inch",
                    token="COMP",
                ),
                p.OneInchSwap(
                    source_token="COMP",
                    target_token=self.cSOURCE,
                    amount=Ref(key="COMP_balance"),
                ),
                p.BorrowLimitFraction(),
                p.BorrowLimit(
                    slug="borrow_limit_fraction_after_swap", token=self.TARGET
                ),
            ],
        )

    @property
    def enter_strategy(self):
        return p.Pipeline(
            p.Group(
                slug="pipeline",
                given=[
                    p.Setup(),
                    p.Balance(token="ETH"),
                ],
                entry_condition=p.Expr(
                    slug="ETH_sufficient",
                    func=lambda state, min_eth: state["ETH_balance"] >= min_eth,
                    args=[
                        Param[assets.ETH](
                            key="min_eth",
                            type=assets.ETH,
                            default=assets.ETH(Decimal("0.1")),
                        )
                    ],
                ),
                steps=[
                    p.SetAllowance(
                        slug=f"allow_{self.SOURCE}",
                        token=self.SOURCE,
                        set_unlimited=True,
                    ),
                    p.GiveCollateral(
                        c_token=self.cSOURCE,
                    ),
                    p.Supply(
                        token=self.SOURCE,
                        target_amount_supplied=Param[self.source_token_type](
                            key="target_amount_supplied",
                            type=self.source_token_type,
                            default=self.source_token_type(5),
                        ),
                    ),
                    p.Repeat(
                        slug="main_loop",
                        description=_(
                            "Loops as long as at least one of the contained steps is not skipped."
                        ),
                        steps=[
                            p.Group(
                                slug="borrow",
                                description=_(
                                    "Borrows as many %(target_token)s as the configured fraction of the available borrow limit allows to."
                                )
                                % {"target_token": self.TARGET},
                                given=[
                                    p.BorrowLimitFraction(slug="borrow_limit_fraction"),
                                    p.BorrowLimit(
                                        slug="borrow_limit_exhausted",
                                        token=self.TARGET,
                                    ),
                                ],
                                entry_condition=p.Expr(
                                    slug=f"borrowable_{self.TARGET}_above_threshold",
                                    func=lambda state, threshold: state[
                                        f"{self.TARGET}_borrow_limit"
                                    ]
                                    > threshold,
                                    args=[
                                        Param[self.target_token_type](
                                            key="threshold",
                                            type=self.target_token_type,
                                            default=self.target_token_type(Decimal(0)),
                                        )
                                    ],
                                ),
                                steps=[
                                    p.Borrow(
                                        token=self.TARGET,
                                        amount=Ref(key=f"{self.TARGET}_borrow_limit"),
                                    ),
                                ],
                            ),
                            p.Group(
                                slug="swap_borrowed",
                                description=_(
                                    "Swaps all available %(target_token)s on the wallet into c%(source_token)s (which in turn increases the collateral)."
                                )
                                % {
                                    "source_token": self.SOURCE,
                                    "target_token": self.TARGET,
                                },
                                given=[
                                    p.Balance(token=self.TARGET),
                                ],
                                entry_condition=p.Expr(
                                    slug=f"swappable_{self.TARGET}_above_threshold",
                                    func=lambda state, threshold: state[
                                        f"{self.TARGET}_balance"
                                    ]
                                    > threshold,
                                    args=[
                                        Param[self.target_token_type](
                                            key="threshold",
                                            type=self.target_token_type,
                                            default=self.target_token_type(Decimal(0)),
                                        )
                                    ],
                                ),
                                steps=[
                                    p.SetContractAllowance(
                                        slug=f"allow_{self.TARGET}_1inch",
                                        token=self.TARGET,
                                        # address is hard-coded response from 1Inch at https://api.1inch.io/v4.0/1/approve/spender
                                        # returning 1Inch v4 Router. See https://docs.1inch.io/docs/aggregation-protocol/api/swagger/
                                        spender_contract="0x1111111254fb6c44bac0bed2854e76f90643097d",
                                        set_unlimited=True,
                                    ),
                                    p.OneInchSwap(
                                        source_token=self.TARGET,
                                        target_token=self.cSOURCE,
                                        amount=Ref(key=f"{self.TARGET}_balance"),
                                    ),
                                    p.BorrowLimitFraction(),
                                    p.BorrowLimit(token=self.TARGET),
                                ],
                            ),
                            self.harvest_comp,
                            self.swap_comp,
                        ],
                    ),
                ],
            )
        )

    @property
    def exit_strategy(self):
        return p.Pipeline(
            p.Group(
                slug="pipeline",
                given=[
                    p.Setup(),
                    p.Balance(token="ETH"),
                ],
                entry_condition=p.Expr(
                    slug="ETH_sufficient",
                    func=lambda state, min_eth: state["ETH_balance"] >= min_eth,
                    args=[
                        Param[assets.ETH](
                            key="min_eth",
                            type=assets.ETH,
                            default=assets.ETH(Decimal("0.1")),
                        )
                    ],
                ),
                steps=[
                    p.SetAllowance(
                        slug=f"allow_{self.SOURCE}",
                        token=self.SOURCE,
                        set_unlimited=True,
                    ),
                    p.GiveCollateral(
                        c_token=self.cSOURCE,
                    ),
                    p.Repeat(
                        slug="swap_repay_loop",
                        description=_(
                            "Loops as long as at least one of the contained steps is not skipped."
                        ),
                        steps=[
                            p.Group(
                                slug="swap",
                                description=_(
                                    "If insufficient balance for repaying %(target_token)s debt, swap enough c%(source_token)s to %(target_token)s (ensuring the given used borrow limit fraction is not exceeded)."
                                )
                                % {
                                    "source_token": self.SOURCE,
                                    "target_token": self.TARGET,
                                },
                                given=[
                                    p.BorrowBalance(
                                        slug=f"{self.TARGET}_borrow_balance_for_swap",
                                        token=self.TARGET,
                                    ),
                                    p.Balance(
                                        slug=f"{self.TARGET}_balance_for_swap",
                                        token=self.TARGET,
                                    ),
                                    # calculate the insufficient target token balance that we need to receive by swap c-source-token -> target-token
                                    p.Transform(
                                        slug=f"{self.TARGET}_insufficient_repay",
                                        func=lambda state: {
                                            **state,
                                            f"{self.TARGET}_insufficient_repay": max(
                                                Decimal(0),
                                                state[f"{self.TARGET}_borrow_balance"]
                                                - state[f"{self.TARGET}_balance"],
                                            ),
                                        },
                                    ),
                                ],
                                entry_condition=p.Expr(
                                    slug=f"has_insufficient_{self.TARGET}_for_repay",
                                    func=lambda state: state[
                                        f"{self.TARGET}_insufficient_repay"
                                    ]
                                    > Decimal(0),
                                ),
                                steps=[
                                    p.Group(
                                        given=[
                                            p.OneInchSourceQuote(
                                                source_token=self.cSOURCE,
                                                target_token=f"{self.TARGET}",
                                                target_amount=Ref(
                                                    key=f"{self.TARGET}_insufficient_repay"
                                                ),
                                            ),
                                            # yes, just use redeemable to determine how many c-source-tokens are not "bound" to maintain a certain used borrow limit
                                            p.Redeemable(c_token=self.cSOURCE),
                                            p.Transform(
                                                slug="swappable",
                                                func=lambda state, surplus_if_available: {
                                                    **state,
                                                    f"{self.cSOURCE}_swappable": min(
                                                        state[f"{self.cSOURCE}_quote"]
                                                        + surplus_if_available,
                                                        state[
                                                            f"{self.cSOURCE}_redeemable"
                                                        ],
                                                    ),
                                                },
                                                args=[
                                                    Param[self.source_c_token_type](
                                                        key="surplus_if_available",
                                                        type=self.source_c_token_type,
                                                        default=self.source_c_token_type(
                                                            Decimal("0.1")
                                                        ),
                                                    )
                                                ],
                                            ),
                                        ],
                                        entry_condition=p.Expr(
                                            slug=f"{self.cSOURCE}_swappable_above_threshold",
                                            func=lambda state, threshold: state[
                                                f"{self.cSOURCE}_swappable"
                                            ]
                                            > threshold,
                                            args=[
                                                Param[self.source_c_token_type](
                                                    key="threshold",
                                                    type=self.source_c_token_type,
                                                    default=self.source_c_token_type(
                                                        Decimal(10)
                                                    ),
                                                )
                                            ],
                                        ),
                                        steps=[
                                            # quote again to know what we would get for the indeed swappable amount
                                            p.OneInchTargetQuote(
                                                source_token=self.cSOURCE,
                                                target_token=self.TARGET,
                                                source_amount=Ref(
                                                    key=f"{self.cSOURCE}_swappable"
                                                ),
                                            ),
                                            # we don't put this into a condition since it's a hard failure when we exceed the given limit (which must contain a buffer to account for small used borrow limit increase)
                                            p.ForecastBorrowLimitFractionAfterSwapWithinLimit(
                                                source_token=self.cSOURCE,
                                                target_token=self.TARGET,
                                                amount=Ref(
                                                    key=f"{self.cSOURCE}_swappable"
                                                ),
                                                target_amount=Ref(
                                                    key=f"{self.TARGET}_quote"
                                                ),
                                                # this is the hard-coded safety limit fraction
                                                borrow_limit_fraction=Decimal("0.99"),
                                            ),
                                            p.SetOneInchAllowance(
                                                slug=f"allow_{self.cSOURCE}_1inch",
                                                token=self.cSOURCE,
                                            ),
                                            p.OneInchSwap(
                                                source_token=self.cSOURCE,
                                                target_token=self.TARGET,
                                                amount=Ref(
                                                    key=f"{self.cSOURCE}_swappable"
                                                ),
                                            ),
                                            p.BorrowLimitFraction(),
                                            p.BorrowLimit(token=self.TARGET),
                                        ],
                                    )
                                ],
                            ),
                            p.Group(
                                slug="repay",
                                description=_(
                                    "Repay as many borrowed %(target_token)s as possible, i.e. min(%(target_token)s borrowed, %(target_token)s balance) to compound (will decrease the used borrow limit)."
                                )
                                % {"target_token": self.TARGET},
                                given=[
                                    p.BorrowBalance(
                                        slug=f"{self.TARGET}_borrow_balance_for_repay",
                                        token=self.TARGET,
                                    ),
                                    p.Balance(
                                        slug=f"{self.TARGET}_borrow_for_repay",
                                        token=self.TARGET,
                                    ),
                                    p.Transform(
                                        slug="max_possible_repay",
                                        func=lambda state: {
                                            **state,
                                            f"{self.TARGET}_max_possible_repay": min(
                                                state[f"{self.TARGET}_borrow_balance"],
                                                state[f"{self.TARGET}_balance"],
                                            ),
                                        },
                                    ),
                                ],
                                entry_condition=p.Expr(
                                    slug="max_possible_repay_above_threshold",
                                    func=lambda state, threshold: state[
                                        f"{self.TARGET}_max_possible_repay"
                                    ]
                                    > threshold,
                                    args=[
                                        Param[self.target_token_type](
                                            key="threshold",
                                            type=self.target_token_type,
                                            default=self.target_token_type(Decimal(0)),
                                        )
                                    ],
                                ),
                                steps=[
                                    p.Transform(
                                        slug="remaining_repay",
                                        func=lambda state: {
                                            **state,
                                            "remaining_repay": state[
                                                f"{self.TARGET}_balance"
                                            ]
                                            - state[f"{self.TARGET}_max_possible_repay"]
                                            < Decimal(0.1),
                                        },
                                    ),
                                    p.Repay(
                                        token=self.TARGET,
                                        amount=Ref(
                                            key=f"{self.TARGET}_max_possible_repay"
                                        ),
                                        remaining=Ref(key="remaining_repay"),
                                    ),
                                ],
                            ),
                        ],
                    ),
                    p.Group(
                        slug="redeem",
                        description=_(
                            "Redeem all c%(source_token)s on the wallet if possible."
                        )
                        % {"source_token": self.SOURCE},
                        given=[
                            p.Balance(token=self.cSOURCE),
                            p.Redeemable(
                                c_token=self.cSOURCE,
                                borrow_limit_fraction=Decimal("0.9"),
                            ),
                        ],
                        entry_condition=p.Expr(
                            slug=f"all_{self.cSOURCE}_redeemable_and_above_threshold",
                            func=lambda state, threshold: state[
                                f"{self.cSOURCE}_redeemable"
                            ]
                            >= state[
                                f"{self.cSOURCE}_balance"
                            ]  # only enter when complete c-token balance is redeemable
                            and state[f"{self.cSOURCE}redeemable"]
                            > threshold,  # and threshold met
                            args=[
                                Param[self.source_c_token_type](
                                    key="threshold",
                                    type=self.source_c_token_type,
                                    default=self.source_c_token_type(Decimal(0)),
                                )
                            ],
                        ),
                        steps=[
                            p.Redeem(
                                c_token=self.cSOURCE,
                                amount=Ref(key=f"{self.cSOURCE}_balance"),
                            ),
                        ],
                    ),
                    self.harvest_comp,
                    self.swap_comp,
                ],
            )
        )
