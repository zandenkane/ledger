# how to contribute

Python 3.10+. `pip install -e .[dev]` for setup.

The hash chain implementation is in src/ledger/chain.py. Each entry gets SHA-256'd with the previous hash to form a tamper-evident chain. If you want to add a new export format, look at src/ledger/export.py.

`pytest` runs the full suite.
