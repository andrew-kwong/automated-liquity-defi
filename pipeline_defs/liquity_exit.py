from decimal import Decimal
from gettext import gettext as _

from automated_defi.eth import assets
from automated_defi.pipeline import pipeline as p
from automated_defi.pipeline.params import Param, Ref

liquity_exit = p.Pipeline(
    p.Group(
        slug="liquity_exit_pipeline",
        given=[
            p.Setup(),
            p.StabilityPoolCheck(),
        ],
        steps=[
            # withdraw stage
            p.Group(
                slug="liquity_exit_withdraw_pipeline",
                entry_condition=p.Expr(
                    slug="check_LUSD_balance_pool",
                    func=lambda state: state["lusd_in_pool"] > 0,
                ),
                steps=[
                    p.WithdrawLUSD(amount=Ref(key="lusd_in_pool")),
                ],
            ),
            # swap and exit check stage
            p.Group(
                slug="liquity_exit_swap_and_check_pipeline_",
                steps=[
                    p.Group(
                        slug="prepare_swap_eth_to_weth",
                        description=_(
                            "Wraps ETH to WETH as preparation to swap WETH to LUSD in order to redeposit back to the stability pool."
                        ),
                        given=[
                            p.Balance(token="ETH"),
                            p.StoreMinGasBalance(),
                        ],
                        entry_condition=p.Expr(
                            slug="ETH_balance",
                            func=lambda state: state["ETH_balance"]
                            >= state["eth_min_gas_balance"],
                        ),
                        steps=[
                            p.CalculateDifference(),
                            p.ConvertETHToWETH(
                                amount=Ref(key="ETH_difference"),
                            ),
                        ],
                    ),
                    p.Group(
                        slug="swap_weth_to_lusd",
                        description=_(
                            "Swaps WETH to LUSD in order to redeposit back to the stability pool."
                        ),
                        given=[
                            p.Balance(token="WETH"),
                        ],
                        entry_condition=p.Expr(
                            slug="WETH_balance",
                            func=lambda state, weth_threshold: state["WETH_balance"]
                            >= weth_threshold,
                            args=[
                                Param[assets.WETH](
                                    key="weth_threshold",
                                    type=assets.WETH,
                                    default=assets.WETH(Decimal("0.001")),
                                )
                            ],
                        ),
                        steps=[
                            p.SetOneInchAllowance(
                                slug="allow_WETH_1inch",
                                token="WETH",
                            ),
                            p.OneInchSwap(
                                source_token="WETH",
                                target_token="LUSD",
                                amount=Ref(key="WETH_balance"),
                                slippage_tolerance=Decimal("0.01"),
                                expected_conversion_rate=Decimal("0.0003564"),
                            ),
                        ],
                    ),
                    p.Group(
                        slug="swap_lqty_to_lusd",
                        description=_("Swaps LQTY balance to LUSD"),
                        given=[p.Balance(token="LQTY")],
                        entry_condition=p.Expr(
                            slug="LQTY_balance_above_swap_threshold",
                            func=lambda state, swap_LQTY_threshold: state[
                                "LQTY_balance"
                            ]
                            >= swap_LQTY_threshold,
                            args=[
                                Param[assets.LQTY](
                                    key="swap_LQTY_threshold",
                                    type=assets.LQTY,
                                    default=assets.LQTY(Decimal(1)),
                                )
                            ],
                        ),
                        steps=[
                            p.SetOneInchAllowance(
                                slug="allow_LQTY_1inch",
                                token="LQTY",
                            ),
                            p.OneInchSwap(
                                source_token="LQTY",
                                target_token="LUSD",
                                amount=Ref(key="LQTY_balance"),
                                slippage_tolerance=Decimal("0.01"),
                                expected_conversion_rate=Decimal("0.6388"),
                            ),
                        ],
                    ),
                    p.LiquityExitCheck(),
                ],
            ),
        ],
    ),
)
