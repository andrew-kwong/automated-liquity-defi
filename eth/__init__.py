from web3._utils import transactions

# monkey patch the defaults because they are erroneously evaluated in buildTransaction calls and lead to errors on testnets
# why are we even calling buildTransaction before having all transaction parameters finalized?
# -> We want to set some transaction parameters (not contract method parameters) in contracts.py, such as "from" in transfer, but also attach general parameters like all around gas and nonces later
# -> Debugging gets cumbersome when errors are only thrown later when executing a transaction in chain.do
transactions.TRANSACTION_DEFAULTS = {}
