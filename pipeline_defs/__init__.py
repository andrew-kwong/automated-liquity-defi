from automated_defi.eth import assets

from .compound import CompoundTemplate
from .liquity import get_lqty_accrued, get_lqty_apr, liquity
from .liquity_exit import liquity_exit
from .token import (
    get_comp_accrued,
    get_token_balance,
    pl_balances,
    transfer,
    usd_prices,
)

compound_USDC_DAI = CompoundTemplate(
    source_token_type=assets.USDC,
    source_c_token_type=assets.cUSDC,
    target_token_type=assets.DAI,
    target_c_token_type=assets.cDAI,
).enter_strategy
compound_exit_USDC_DAI = CompoundTemplate(
    source_token_type=assets.USDC,
    source_c_token_type=assets.cUSDC,
    target_token_type=assets.DAI,
    target_c_token_type=assets.cDAI,
).exit_strategy

compound_DAI_USDC = CompoundTemplate(
    source_token_type=assets.DAI,
    source_c_token_type=assets.cDAI,
    target_token_type=assets.USDC,
    target_c_token_type=assets.cUSDC,
).enter_strategy
compound_exit_DAI_USDC = CompoundTemplate(
    source_token_type=assets.DAI,
    source_c_token_type=assets.cDAI,
    target_token_type=assets.USDC,
    target_c_token_type=assets.cUSDC,
).exit_strategy


__all__ = [
    compound_USDC_DAI,
    compound_exit_USDC_DAI,
    compound_DAI_USDC,
    compound_exit_DAI_USDC,
    liquity,
    liquity_exit,
    get_lqty_accrued,
    get_lqty_apr,
    get_comp_accrued,
    get_token_balance,
    pl_balances,
    usd_prices,
    transfer,
]
