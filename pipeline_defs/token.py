from automated_defi.pipeline import pipeline as p

get_token_balance = p.Pipeline(
    p.Group(
        slug="pipeline",
        steps=[
            p.Balance(),
        ],
    )
)

get_comp_accrued = p.Pipeline(
    p.Group(
        slug="pipeline",
        steps=[
            p.CompAccrued(),
        ],
    )
)

transfer = p.Pipeline(
    p.Group(
        slug="pipeline",
        steps=[
            p.Setup(),
            p.Transfer(),
        ],
    )
)

TOKENS = ["ETH", "USDC", "cUSDC", "DAI", "cDAI", "COMP", "LUSD", "LQTY"]

pl_balances = p.Pipeline(
    p.Group(
        slug="pipeline",
        steps=[p.Balance(token=token) for token in TOKENS]
        + [
            p.LQTYAccrued(),
            p.CompAccrued(),
            p.ETHAccrued(),
            p.StabilityPoolCheck(),
            p.BorrowBalance(token="DAI"),
            p.BorrowBalance(token="USDC"),
        ],
    )
)

usd_prices = p.Pipeline(
    p.Group(
        slug="pipeline",
        steps=[
            p.Prices(tokens=",".join(TOKENS)),
            p.ReportResult(
                slug="usd_prices",
                func=lambda state: state["usd_prices"],
            ),
        ],
    )
)
