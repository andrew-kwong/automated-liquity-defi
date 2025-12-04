from decimal import ROUND_HALF_DOWN, Context, Decimal, getcontext


def decimal_context(ctx: Context = None):
    """Returns a copy of the given (or default) decimal context with sufficient precision and rounding strategy."""
    if not ctx:
        ctx = getcontext()

    # do not update context to make library not have side-effects to default decimal context!
    ctx = ctx.copy()

    ctx.prec = 100
    ctx.rounding = ROUND_HALF_DOWN
    return ctx


def _moneyfmt(
    value: Decimal,
    places=2,
    curr="",
    sep=",",
    dp=".",
    pos="",
    neg="-",
    trailneg="",
):
    """Convert Decimal to a money formatted string.

    Corresponds exacly to https://docs.python.org/3.9/library/decimal.html#recipes.

    places:  required number of places after the decimal point
    curr:    optional currency symbol before the sign (may be blank)
    sep:     optional grouping separator (comma, period, space, or blank)
    dp:      decimal point indicator (comma or period)
             only specify as blank when places is zero
    pos:     optional sign for positive numbers: '+', space or blank
    neg:     optional sign for negative numbers: '-', '(', space or blank
    trailneg:optional trailing minus indicator:  '-', ')', space or blank

    >>> d = Decimal('-1234567.8901')
    >>> moneyfmt(d, curr='$')
    '-$1,234,567.89'
    >>> moneyfmt(d, places=0, sep='.', dp='', neg='', trailneg='-')
    '1.234.568-'
    >>> moneyfmt(d, curr='$', neg='(', trailneg=')')
    '($1,234,567.89)'
    >>> moneyfmt(Decimal(123456789), sep=' ')
    '123 456 789.00'
    >>> moneyfmt(Decimal('-0.02'), neg='<', trailneg='>')
    '<0.02>'

    """
    q = Decimal(10) ** -places  # 2 places --> '0.01'
    sign, digits, exp = value.quantize(q, context=decimal_context()).as_tuple()
    result = []
    digits = list(map(str, digits))
    build, next = result.append, digits.pop
    if sign:
        build(trailneg)
    for i in range(places):
        build(next() if digits else "0")
    if places:
        build(dp)
    if not digits:
        build("0")
    i = 0
    while digits:
        build(next())
        i += 1
        if i == 3 and digits:
            i = 0
            build(sep)
    build(curr)
    build(neg if sign else pos)
    return "".join(reversed(result))


def fmt(
    value: Decimal,
) -> str:
    """Convert Decimal to a money formatted string that is parsable by the
    constructor of `Decimal`.

    In contrast to `str(decimal)` it suppresses scientific notation for small
    decimals and always prints it as `XX.XXXXX`.
    """
    return _moneyfmt(
        value=value,
        places=-value.as_tuple().exponent,
        curr="",
        sep="",
        dp=".",
        pos="",
        neg="-",
        trailneg="",
    )
