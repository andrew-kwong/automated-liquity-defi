import json
from collections import defaultdict
from dataclasses import dataclass, field
from functools import cached_property
from gettext import gettext as _
from typing import Optional

from automated_defi.pipeline import pipeline as p
from automated_defi.pipeline_defs import (
    compound_DAI_USDC,
    compound_exit_DAI_USDC,
    compound_exit_USDC_DAI,
    compound_USDC_DAI,
    get_comp_accrued,
    get_lqty_accrued,
    get_lqty_apr,
    get_token_balance,
    liquity,
    liquity_exit,
    pl_balances,
    transfer,
    usd_prices,
)
from automated_defi.protocol.chain import Chain
from automated_defi.protocol.chains import Chains
from automated_defi.utils import EnhancedJSONEncoder


@dataclass
class Spec:
    """Class to define a protocol specification and its parameterization."""

    slug: str  # the unique key used to identify this protocol together with the version -> used in task routing keys
    version: int  # part of identifcation, see slug -> used in task routing keys
    name: Optional[str] = None  # human readable name
    description: Optional[str] = None  # human readable description
    reverses: list[str] = field(default_factory=list)
    pipeline: p.Pipeline = field(default_factory=lambda: p.Pipeline())
    chain: Chain = Chains.ETH_MAINNET

    @cached_property
    def routing_key(self) -> str:
        return f"{self.chain.slug}.{self.slug}.{self.version}"

    def __str__(self) -> str:
        return f"{self.name} [{self.chain.name}]" or self.routing_key

    def json(self):
        return json.dumps(self, cls=SpecJSONEncoder)


class Protocols:
    # TODO we could load this from JSON config files later, that's why it's wrapped in a class (also makes testing easier, avoiding monkey patching)
    specs: list[Spec] = [
        Spec(
            name=_("Get token balance"),
            description=_("Get balance of the given token contract or ETH."),
            slug="balance",
            version=1,
            pipeline=get_token_balance,
            chain=Chains.ETH_MAINNET,
        ),
        Spec(
            name=_("Get token balance"),
            description=_("Get balance of the given token contract or ETH."),
            slug="balance",
            version=1,
            pipeline=get_token_balance,
            chain=Chains.ETH_GOERLI,
        ),
        Spec(
            name=_("Get token balance"),
            description=_("Get balance of the given token contract or ETH."),
            slug="balance",
            version=1,
            pipeline=get_token_balance,
            chain=Chains.ETH_ROPSTEN,
        ),
        Spec(
            name=_("Get token balance"),
            description=_("Get balance of the given token contract or ETH."),
            slug="balance",
            version=1,
            pipeline=get_token_balance,
            chain=Chains.ETH_RINKEBY,
        ),
        Spec(
            name=_("Get COMP accrued"),
            description=_("Get COMP accrued while interacting with Compound."),
            slug="comp_accrued",
            version=1,
            pipeline=get_comp_accrued,
            chain=Chains.ETH_MAINNET,
        ),
        Spec(
            name=_("P&L balances"),
            description=_(
                "Retrieve wallet balances and accrued balances of all protocols."
            ),
            slug="pl-balances",
            version=1,
            pipeline=pl_balances,
            chain=Chains.ETH_MAINNET,
        ),
        Spec(
            name=_("P&L balances"),
            description=_(
                "Retrieve wallet balances and accrued balances of all protocols."
            ),
            slug="pl-balances",
            version=1,
            pipeline=pl_balances,
            chain=Chains.ETH_GOERLI,
        ),
        Spec(
            name=_("P&L balances"),
            description=_(
                "Retrieve wallet balances and accrued balances of all protocols."
            ),
            slug="pl-balances",
            version=1,
            pipeline=pl_balances,
            chain=Chains.ETH_ROPSTEN,
        ),
        Spec(
            name=_("P&L balances"),
            description=_(
                "Retrieve wallet balances and accrued balances of all protocols."
            ),
            slug="pl-balances",
            version=1,
            pipeline=pl_balances,
            chain=Chains.ETH_RINKEBY,
        ),
        # the prices make only sense for mainnet
        Spec(
            name=_("USD prices"),
            description=_("Fetch current USD price of tokens from CoinMarketCap API."),
            slug="usd-prices",
            version=1,
            pipeline=usd_prices,
            chain=Chains.ETH_MAINNET,
        ),
        Spec(
            name=_("Get COMP accrued"),
            description=_("Get COMP accrued while interacting with Compound."),
            slug="comp_accrued",
            version=1,
            pipeline=get_comp_accrued,
            chain=Chains.ETH_RINKEBY,
        ),
        Spec(
            name=_("Transfer"),
            description=_("Transfers a token to a different address."),
            slug="transfer",
            version=1,
            pipeline=transfer,
            chain=Chains.ETH_MAINNET,
        ),
        Spec(
            name=_("Transfer"),
            description=_("Transfers a token to a different address."),
            slug="transfer",
            version=1,
            pipeline=transfer,
            chain=Chains.ETH_GOERLI,
        ),
        Spec(
            name=_("Transfer"),
            description=_("Transfers a token to a different address."),
            slug="transfer",
            version=1,
            pipeline=transfer,
            chain=Chains.ETH_ROPSTEN,
        ),
        Spec(
            name=_("Transfer"),
            description=_("Transfers a token to a different address."),
            slug="transfer",
            version=1,
            pipeline=transfer,
            chain=Chains.ETH_RINKEBY,
        ),
        Spec(
            name=_("Compound Supply USDC - Borrow DAI - Swap"),
            description=_(
                "A strategy for Compound that loops through supply USDC, borrow DAI and swap for more USDC to supply. Harvests COMP."
            ),
            slug="compound",
            version=2,
            pipeline=compound_USDC_DAI,
            chain=Chains.ETH_MAINNET,
        ),
        Spec(
            name=_("Compound Supply USDC - Borrow DAI - Swap"),
            description=_(
                "A strategy for Compound that loops through supply USDC, borrow DAI and swap for more USDC to supply. Harvests COMP."
            ),
            slug="compound",
            version=2,
            pipeline=compound_USDC_DAI,
            chain=Chains.ETH_RINKEBY,
        ),
        Spec(
            name=_("Exit Compound Supply USDC - Borrow DAI"),
            description=_(
                "The reverse strategy for 'Compound Supply-Borrow-Swap' strategy."
            ),
            reverses=["compound"],
            slug="compound-reverse",
            version=2,
            pipeline=compound_exit_USDC_DAI,
            chain=Chains.ETH_MAINNET,
        ),
        Spec(
            name=_("Exit Compound Supply USDC - Borrow DAI"),
            description=_(
                "The reverse strategy for 'Compound Supply-Borrow-Swap' strategy."
            ),
            reverses=["compound"],
            slug="compound-reverse",
            version=2,
            pipeline=compound_exit_USDC_DAI,
            chain=Chains.ETH_RINKEBY,
        ),
        Spec(
            name=_("Compound Supply DAI - Borrow USDC - Swap"),
            description=_(
                "A strategy for Compound that loops through supply USDC, borrow DAI and swap for more USDC to supply. Harvests COMP."
            ),
            slug="compound-dai-usdc",
            version=1,
            pipeline=compound_DAI_USDC,
            chain=Chains.ETH_MAINNET,
        ),
        Spec(
            name=_("Compound Supply DAI - Borrow USDC - Swap"),
            description=_(
                "A strategy for Compound that loops through supply USDC, borrow DAI and swap for more USDC to supply. Harvests COMP."
            ),
            slug="compound-dai-usdc",
            version=1,
            pipeline=compound_DAI_USDC,
            chain=Chains.ETH_RINKEBY,
        ),
        Spec(
            name=_("Exit Compound Supply DAI - Borrow USDC"),
            description=_(
                "The reverse strategy for 'Compound Supply-Borrow-Swap' strategy."
            ),
            reverses=["compound-dai-usdc"],
            slug="compound-exit-dai-usdc",
            version=1,
            pipeline=compound_exit_DAI_USDC,
            chain=Chains.ETH_MAINNET,
        ),
        Spec(
            name=_("Exit Compound Supply DAI - Borrow USDC"),
            description=_(
                "The reverse strategy for 'Compound Supply-Borrow-Swap' strategy."
            ),
            reverses=["compound-dai-usdc"],
            slug="compound-exit-dai-usdc",
            version=1,
            pipeline=compound_exit_DAI_USDC,
            chain=Chains.ETH_RINKEBY,
        ),
        Spec(
            name=_("Liquity"),
            description=_("The liquity harvest strategy."),
            reverses=["compound"],
            slug="liquity",
            version=1,
            pipeline=liquity,
            chain=Chains.ETH_RINKEBY,
        ),
        Spec(
            name=_("Liquity"),
            description=_("The liquity harvest strategy."),
            reverses=[],
            slug="liquity",
            version=1,
            pipeline=liquity,
            chain=Chains.ETH_MAINNET,
        ),
        Spec(
            name=_("Liquity Exit"),
            description=_("The liquity exit strategy."),
            reverses=["liquity"],
            slug="liquity-exit",
            version=1,
            pipeline=liquity_exit,
            chain=Chains.ETH_RINKEBY,
        ),
        Spec(
            name=_("Liquity Exit"),
            description=_("The liquity exit strategy."),
            reverses=["liquity"],
            slug="liquity-exit",
            version=1,
            pipeline=liquity_exit,
            chain=Chains.ETH_MAINNET,
        ),
        Spec(
            name=_("Calculate Liquity Accrued Rewards"),
            description=_("Get number of accrued LQTY/ETH"),
            reverses=[],
            slug="liquity-accrued",
            version=1,
            pipeline=get_lqty_accrued,
            chain=Chains.ETH_MAINNET,
        ),
        Spec(
            name=_("Calculate Liquity APR"),
            description=_("Liquity APR calculations."),
            reverses=[],
            slug="liquity-apr",
            version=1,
            pipeline=get_lqty_apr,
            chain=Chains.ETH_MAINNET,
        ),
    ]

    @cached_property
    def choices(self) -> list[tuple[str, str]]:
        return [(spec.routing_key, str(spec)) for spec in self.specs]

    @cached_property
    def by_routing_key(self) -> dict[str, Spec]:
        return {spec.routing_key: spec for spec in self.specs}

    @cached_property
    def by_chain(self) -> dict[str, list[Spec]]:
        d = defaultdict(list)
        for spec in self.specs:
            d[spec.chain.slug].append(spec)
        return d

    @cached_property
    def routing_keys_by_chain(self) -> dict[str, list[str]]:
        d = defaultdict(list)
        for spec in self.specs:
            d[spec.chain.slug].append(spec.routing_key)
        return d


class SpecJSONEncoder(EnhancedJSONEncoder):
    def default(self, o):
        if isinstance(o, p.Pipeline):
            return o.root
        return super().default(o)
