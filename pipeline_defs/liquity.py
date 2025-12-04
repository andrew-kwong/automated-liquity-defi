from decimal import Decimal
from gettext import gettext as _

from automated_defi.eth import assets
from automated_defi.pipeline import pipeline as p
from automated_defi.pipeline.params import Param, Ref

# Tracks amount of LQTY/ETH accrued in Liquity
get_lqty_accrued = p.Pipeline(
    p.Group(
        slug="lqty_accrued_pipeline",
        steps=[
            p.LQTYAccrued(),
            p.ETHAccrued(),
        ],
    )
)

# Calculates LQTY APR
get_lqty_apr = p.Pipeline(
    p.Group(
        slug="lqty_apr_pipeline",
        steps=[
            p.CalculateLiquityAPR(),
        ],
    )
)

liquity = p.Pipeline(
    p.Group(
        slug="liquity_strategy_pipeline",
        given=[
            p.Setup(),
        ],
        steps=[
            # deposit group
            p.Group(
                slug="liquity_deposit_pipeline",
                given=[
                    p.Balance(token="LUSD"),
                ],
                entry_condition=p.Expr(
                    slug="LUSD_min_deposit",
                    func=lambda state, min_lusd_deposit: state["LUSD_balance"]
                    > min_lusd_deposit,
                    args=[
                        Param[assets.LUSD](
                            key="min_lusd_deposit",
                            type=assets.LUSD,
                            default=assets.LUSD(Decimal("0.1")),
                        )
                    ],
                ),
                steps=[
                    p.DepositLUSD(
                        amount=Ref(key="LUSD_balance"),
                    ),
                    p.StabilityPoolCheck(),
                ],
            ),
            # harvest group
            p.Repeat(
                slug="main_loop",
                description=_(
                    "Loops as long as at least one of the contained steps is not skipped."
                ),
                steps=[
                    p.Group(
                        slug="harvesting",
                        given=[
                            p.StabilityPoolCheck(),
                        ],
                        entry_condition=p.Expr(
                            slug="check_LUSD_balance_pool",
                            func=lambda state: state["lusd_in_pool"] > 0,
                        ),
                        steps=[
                            p.Group(
                                slug="lqty_eth_harvesting",
                                description=_("Harvests accrued LQTY/ETH."),
                                given=[
                                    p.LQTYAccrued(),
                                    p.EstimateHarvestCost(),
                                ],
                                entry_condition=p.Expr(
                                    slug="accrued_LQTY_above_threshold",
                                    func=lambda state: state["accrued_lqty_usd"]
                                    > state["gas_threshold_usd"],
                                ),
                                steps=[
                                    p.HarvestLQTY(),
                                ],
                            ),
                        ],
                    ),
                    p.Group(
                        slug="swap_lqty_to_lusd",
                        description=_(
                            "Swaps LQTY to LUSD in order to redeposit back to the stability pool."
                        ),
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
                ],
            ),
        ],
    )
)
