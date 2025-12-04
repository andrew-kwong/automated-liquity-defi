from abc import ABC
from decimal import Decimal

from automated_defi import decimal_utils


class Asset(Decimal, ABC):
    """A monetary value (=a value measured in a currency) represented by a Decimal.

    Meant to be used before the decimal expansion in contract calls, without loosing the precision.
    """

    def __repr__(self) -> str:
        return f"{type(self).__name__}('{decimal_utils.fmt(self)}')"


class USD(Asset):
    def __str__(self) -> str:
        return f"${decimal_utils.fmt(self)}"


class ERC20Asset(Asset):
    def __str__(self) -> str:
        return decimal_utils.fmt(self)


class Token(ERC20Asset):
    pass


class CToken(ERC20Asset):
    pass


class ETH(Asset):
    pass


class WETH(Token):
    pass


class WEI(Asset):
    pass


class GWEI(Asset):
    pass


class USDC(Token):
    pass


class cUSDC(CToken):
    pass


class DAI(Token):
    pass


class cDAI(CToken):
    pass


class COMP(ERC20Asset):
    pass


class LUSD(Token):
    pass


class LQTY(Token):
    pass
