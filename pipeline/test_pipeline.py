from typing import NamedTuple

import pytest

from automated_defi.errors import InvalidChainEffectError
from automated_defi.pipeline import pipeline as p
from automated_defi.pipeline.evaluation import Evaluation, State
from automated_defi.protocol.print_executor import PrintExecutor
from automated_defi.protocol.specs import Protocols

protocols = Protocols()


class TestPrintPipeline:
    class Case(NamedTuple):
        routing_key: str
        params: dict

        def __str__(self) -> str:
            return self.routing_key

    testcases = [
        Case(
            routing_key="eth.balance.1",
            params={
                "eth_account": {
                    "address": "0x27D41B00071221365d7c06aa33F14201462b3327",
                    "slug": "simon",
                },
                "pipeline": {
                    "balance": {"token": "ETH"},
                },
            },
        ),
        Case(
            routing_key="eth.transfer.1",
            params={
                "eth_account": {
                    "address": "0x27D41B00071221365d7c06aa33F14201462b3327",
                    "slug": "simon",
                },
                "pipeline": {
                    "transfer": {
                        "address": "0x7474Ee487b0b26b7507fca44634FafBB8be219F9",
                        "amount": 1,
                        "token": "USDC",
                    }
                },
            },
        ),
        Case(
            routing_key="eth-rinkeby.compound.2",
            params={
                "eth_account": {
                    "address": "0x27D41B00071221365d7c06aa33F14201462b3327",
                    "slug": "simon",
                },
                "pipeline": {
                    "setup": {
                        "estimated_gas_surplus": 100000,
                        "max_priority_fee": "3",
                    },
                    "ETH_sufficient": {"min_eth": "0.1"},
                    "allow_USDC": {"amount": "0"},
                    "supply": {"amount": "5"},
                    "main_loop": {
                        "max": 50,
                        "borrow": {
                            "borrow_limit_exhausted": {"fraction": "0.8"},
                            "borrowable_DAI_above_threshold": {"threshold": "0"},
                        },
                        "swap_borrowed": {"allow_DAI_1inch": {"amount": "0"}},
                        "comp_harvesting": {
                            "accrued_COMP_above_threshold": {"threshold": "0"}
                        },
                        "swap_comp": {
                            "COMP_balance_above_threshold": {"threshold": "0"},
                            "allow_COMP_1inch": {"amount": "0"},
                        },
                    },
                },
            },
        ),
        Case(
            routing_key="eth-rinkeby.compound-reverse.2",
            params={
                "eth_account": {
                    "address": "0x27D41B00071221365d7c06aa33F14201462b3327",
                    "slug": "simon",
                },
                "pipeline": {
                    "setup": {
                        "default_gas": None,
                        "estimated_gas_surplus": 100000,
                        "max_priority_fee": "3",
                    },
                    "ETH_sufficient": {"min_eth": "0.1"},
                    "allow_USDC": {"amount": "0"},
                    "allow_DAI": {"amount": "0"},
                    "swap_redeem_repay_loop": {
                        "max": 50,
                        "swap": {
                            "borrow_limit_exhausted": {"fraction": "0.9"},
                            "swappable_cUSDC_above_threshold": {"threshold": "0"},
                            "allow_cUSDC_1inch": {"amount": "0"},
                        },
                        "redeem": {"cDAI_balance_above_threshold": {"threshold": "0"}},
                        "repay": {
                            "max_possible_repay_above_threshold": {"threshold": "0"}
                        },
                    },
                    "comp_harvesting": {
                        "accrued_COMP_above_threshold": {"threshold": "0"}
                    },
                    "swap_comp": {
                        "COMP_balance_above_threshold": {"threshold": "0"},
                        "allow_COMP_1inch": {"amount": "0"},
                    },
                },
            },
        ),
        Case(
            routing_key="eth-rinkeby.liquity.1",
            params={
                "eth_account": {
                    "address": "0x3DB1C1fCfa5F67f2f67FabA1E58Dd42579f16dc6",
                    "slug": "andrew",
                },
                "liquity_strategy_pipeline": {
                    "setup": {"estimated_gas_surplus": 100000, "max_priority_fee": "3"},
                    "liquity_deposit_pipeline": {
                        "LUSD_min_deposit": {"min_lusd_deposit": "0.1"}
                    },
                    "main_loop": {
                        "max": 50,
                        "harvesting": {
                            "lqty_eth_harvesting": {
                                "estimate_harvest_cost": {
                                    "gas_speed": "average",
                                    "factor": "1",
                                }
                            }
                        },
                        "swap_lqty_to_lusd": {
                            "LQTY_balance_above_swap_threshold": {
                                "swap_LQTY_threshold": "1"
                            },
                            "allow_LQTY_1inch": {"amount": "1"},
                        },
                        "prepare_swap_eth_to_weth": {
                            "store_min_gas_balance": {"min_gas_balance": "0.5"}
                        },
                        "swap_weth_to_lusd": {
                            "WETH_balance": {"weth_threshold": "0.001"},
                            "allow_WETH_1inch": {"amount": "1"},
                        },
                    },
                },
            },
        ),
        Case(
            routing_key="eth-rinkeby.liquity-exit.1",
            params={
                "eth_account": {
                    "address": "0x3DB1C1fCfa5F67f2f67FabA1E58Dd42579f16dc6",
                    "slug": "andrew",
                },
                "liquity_exit_pipeline": {
                    "setup": {"estimated_gas_surplus": 100000, "max_priority_fee": "3"},
                    "liquity_exit_swap_and_check_pipeline_": {
                        "swap_eth_to_lusd": {
                            "store_min_gas_balance": {"min_gas_balance": "0.5"},
                            "allow_WETH_1inch": {"amount": "1"},
                        },
                        "swap_lqty_to_lusd": {
                            "LQTY_balance_above_swap_threshold": {
                                "swap_LQTY_threshold": "1"
                            },
                            "allow_LQTY_1inch": {"amount": "1"},
                        },
                    },
                },
            },
        ),
        Case(
            routing_key="eth.liquity-apr.1",
            params={
                "eth_account": {
                    "address": "0x3DB1C1fCfa5F67f2f67FabA1E58Dd42579f16dc6",
                    "slug": "andrew",
                },
                "pipeline": {},
            },
        ),
    ]

    @pytest.mark.parametrize("case", testcases, ids=lambda case: str(case))
    def test_print_pipeline(self, case: Case, snapshot):
        protocol = protocols.by_routing_key[case.routing_key]
        executor = PrintExecutor()
        protocol.pipeline(executor, case.params)
        assert executor.log == snapshot


class TestChainEffect:
    """Tests if chain effects are reported and lead to abortion if happing from pipeline steps that do not allow for side effects happening."""

    class InvalidChainEffectExecutor(PrintExecutor):
        def balance(self, step: p.Balance, state: State) -> Evaluation:
            super().balance(step, state)
            # produce a chain effect in a call that is supposed to not have any
            return Evaluation(state=state, chain_effect=True)

    class Case(NamedTuple):
        routing_key: str
        params: dict

        def __str__(self) -> str:
            return self.routing_key

    testcases = [
        Case(
            routing_key="eth-rinkeby.compound.2",
            params={
                "eth_account": {
                    "address": "0x27D41B00071221365d7c06aa33F14201462b3327",
                    "slug": "simon",
                },
                "pipeline": {
                    "setup": {
                        "default_gas": 500000,
                        "max_priority_fee": "3",
                    },
                    "supply": {
                        "amount": "5",
                    },
                    "ETH_sufficient": {
                        "min_eth": "0.1",
                    },
                    "allowance": {
                        "set_allowance": {
                            "amount": "0",
                        },
                    },
                    "main_loop": {
                        "max": 50,
                        "borrow": {
                            "borrow_limit_exhausted": {
                                "fraction": "0.8",
                            },
                            "borrowable_DAI_above_threshold": {
                                "threshold": "0",
                            },
                        },
                        "comp_harvesting": {
                            "accrued_COMP_above_threshold": {
                                "threshold": "0",
                            },
                        },
                        "swap_borrowed": {
                            "set_contract_allowance": {
                                "amount": "0",
                            },
                        },
                        "swap_comp": {
                            "COMP_balance_above_threshold": {
                                "threshold": "0",
                            },
                        },
                    },
                },
            },
        ),
    ]

    @pytest.mark.parametrize("case", testcases, ids=lambda case: str(case))
    def test_chain_effect_error(self, case: Case):
        protocol = protocols.by_routing_key[case.routing_key]
        executor = TestChainEffect.InvalidChainEffectExecutor()
        with pytest.raises(InvalidChainEffectError):
            protocol.pipeline(executor, case.params)
