# Fio Banka API

[![image](https://img.shields.io/pypi/v/fio-banka)](https://pypi.org/project/fio-banka/)
[![image](https://img.shields.io/pypi/l/fio-banka)](https://pypi.org/project/fio-banka/)
[![image](https://img.shields.io/pypi/pyversions/fio-banka)](https://pypi.org/project/fio-banka/)
[![image](https://github.com/peberanek/fio-banka/actions/workflows/tests.yml/badge.svg)](https://github.com/peberanek/fio-banka/actions/workflows/tests.yml)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/peberanek/fio-banka/main.svg)](https://results.pre-commit.ci/latest/github/peberanek/fio-banka/main)

Thin wrapper for [Fio Banka, a.s. API](https://www.fio.cz/bank-services/internetbanking-api). Inspired by Honza Javorek's [fiobank](https://github.com/honzajavorek/fiobank).

## Description

This wrapper is intentionally simple. It does not limit the user by any specific data processing, data structures or error handling. Instead, it returns data as-is, i.e. in a text or a binary format. So the user can handle the processing, errors, data validation or more complex stuff (like caching) according to their needs. A couple of helper functions for data extraction are included nonetheless (see the [Usage](#usage) section below).

Currently, merchant transaction report and order upload are not implemented. Feel free to send a PR (I believe they should be reasonably easy to implement).

### Fio Banka API documentation:
* [Specification](https://www.fio.cz/docs/cz/API_Bankovnictvi.pdf) (Czech only)
* [XSD Schema](https://www.fio.cz/xsd/IBSchema.xsd)

## Installation

```
pip install fio-banka
```

## Usage

```python
>>> from datetime import date
>>> from fio_banka

>>> account = fio_banka.Account("<your-token>")
>>> fmt = fio_banka.TransactionsFmt.JSON
>>> account.periods(date(2023, 1, 1), date(2023, 1, 2), fmt)
'{"accountStatement":{"info":{"accountId": ... '

>>> try:
>>>     account.last(fmt)
>>> except fio_banka.RequestError as exc:
>>>     print(exc)
Exceeded time limit (1 request per 30s).

>>> import time
>>> time.sleep(fio_banka.REQUEST_TIMELIMIT)
>>> data = account.last(fmt)
>>> data
'{"accountStatement":{"info":{"accountId": ... '
```

Data extraction (make sure data are downloaded as *JSON*):
```python
>>> fio_banka.get_account_info(data)
AccountInfo(
    account_id='2000000000',
    bank_id='2010',
    currency='CZK',
    iban='CZ1000000000002000000000',
    bic='FIOBCZPPXXX',
    opening_balance=Decimal('1000.99'),
    closing_balance=Decimal('2000.10'),
    date_start=datetime.date(2023, 1, 1),
    date_end=datetime.date(2023, 1, 3),
    year_list=None,
    id_list=None,
    id_from=10000000000,
    id_to=10000000002,
    id_last_download=None
)
>>> list(fio_banka.get_transactions(data))[0]
Transaction(
    transaction_id='10000000000',
    date=datetime.date(2023, 1, 1),
    amount=Decimal('2000.0'),
    currency='CZK',
    account_id=None,
    account_name='',
    bank_id=None,
    bank_name=None,
    ks=None,
    vs='1000',
    ss=None,
    user_identification='Nákup: example.com, dne 31.12.2022, částka  2000.00 CZK',
    remittance_info='Nákup: example.com, dne 31.12.2022, částka  2000.00 CZK',  # Zprava pro prijemce
    type='Platba kartou',
    executor='Novák, Jan',
    specification=None,
    comment='Nákup: example.com, dne 31.12.2022, částka  2000.00 CZK',
    bic=None,
    order_id=30000000000,
    payer_reference=None
)
```

## Contributing

Build and activate development environment:
```
make venv
source venv/bin/activate
```

Install [pre-commit](https://pre-commit.com/) hook:
```
pre-commit install
```

Run tests:
```
pytest
```

Use [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/).

## License

This project is licensed under the terms of the MIT license.
