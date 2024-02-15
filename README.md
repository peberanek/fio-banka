# Fio Banka API

[![image](https://img.shields.io/pypi/v/fio-banka)](https://pypi.org/project/fio-banka/)
[![image](https://img.shields.io/pypi/l/fio-banka)](https://pypi.org/project/fio-banka/)
[![image](https://img.shields.io/pypi/pyversions/fio-banka)](https://pypi.org/project/fio-banka/)
[![image](https://github.com/peberanek/fio-banka/actions/workflows/tests.yml/badge.svg)](https://github.com/peberanek/fio-banka/actions/workflows/tests.yml)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/peberanek/fio-banka/main.svg)](https://results.pre-commit.ci/latest/github/peberanek/fio-banka/main)

Rework of Honza Javorek's [fiobank](https://github.com/honzajavorek/fiobank), with the following upgrades:

* Parse both account info and transactions in 1 request. This is particularly useful as Fio banka allows only 1 request per 30 seconds.
* Known error states are covered by exceptions for fine-grade error handling.
* Fetch data in all supported formats (including PDF).
* New design allows to support other end points than account.
* Safer data types: money as [`decimal.Decimal` instead of `float`](https://docs.python.org/3/tutorial/floatingpoint.html), data stored as `typing.NamedTuple` instead of `dict`.

> [!NOTE]
> Merchant transaction report and order upload are not implemented. Feel free to send a PR.

## Quick example
```python
>>> import fio_banka, datetime
>>> account = fio_banka.Account("my-API-token")
>>> transaction_report = account.fetch_transaction_report_for_period(
...     datetime.date(2023, 1, 1),
...     datetime.date(2023, 1, 2),
...     fio_banka.TransactionReportFmt.JSON
... )
>>> account.parse_account_info(transaction_report)  # JSON only
AccountInfo(
    account_id='2000000000',
    bank_id='2010',
    currency='CZK',
    iban='CZ1000000000002000000000',
    ...
)
>>> next(iter(account.parse_transactions(transaction_report)))  # JSON only
Transaction(
    transaction_id='10000000000',
    date=datetime.date(2023, 1, 1),
    amount=Decimal('2000.0'),
    currency='CZK',
    account_id=None,
    ...
```

## Documentation

For full description see the module [docstring](https://github.com/peberanek/fio-banka/blob/main/fio_banka.py).

API documentation by Fio banka:

* [Specification](https://www.fio.cz/docs/cz/API_Bankovnictvi.pdf) (Czech only)
* [XSD Schema](https://www.fio.cz/xsd/IBSchema.xsd)


## Installation

```
pip install fio-banka
```

## Contributing

Set up development environment via [Pipenv](https://pipenv.pypa.io/en/latest/):

```bash
pipenv sync --dev
pipenv run pre-commit install
```

Run tests:
```bash
pytest
```

Use [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/).

I highly recommend to follow [Test-Driven Development (revisited)](https://www.youtube.com/watch?v=IN9lftH0cJc). Actually, all existing tests follow it.

## License

This project is licensed under the terms of the MIT license.
