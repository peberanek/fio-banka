# Fio Banka API Client

[![image](https://img.shields.io/pypi/v/fio-banka)](https://pypi.org/project/fio-banka/)
[![image](https://img.shields.io/pypi/l/fio-banka)](https://pypi.org/project/fio-banka/)
[![image](https://img.shields.io/pypi/pyversions/fio-banka)](https://pypi.org/project/fio-banka/)
[![image](https://github.com/peberanek/fio-banka/actions/workflows/tests.yml/badge.svg)](https://github.com/peberanek/fio-banka/actions/workflows/tests.yml)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/peberanek/fio-banka/main.svg)](https://results.pre-commit.ci/latest/github/peberanek/fio-banka/main)

Client for [Fio Banka, a.s. API](https://www.fio.cz/bank-services/internetbanking-api). Inspired by Honza Javorek's [fiobank](https://github.com/honzajavorek/fiobank).

## Description

This client is useful if you need to parse account info and transactions in 1 request (Fio banka imposes a limit of 1 request per 30 seconds) or if you want to fetch raw data (text or binary - e.g. PDF).

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
>>> import fio_banka

>>> account = fio_banka.Account("<API-token>")
>>> fmt = fio_banka.TransactionsFmt.JSON
>>> account.periods(date(2023, 1, 1), date(2023, 1, 2), fmt)
'{"accountStatement":{"info":{"accountId": ...(long output)... '

>>> try:
>>>     account.last(fmt)
>>> except fio_banka.RequestError as exc:
>>>     print(exc)
Exceeded time limit (1 request per 30s).

>>> import time
>>> time.sleep(fio_banka.REQUEST_TIMELIMIT)
>>> data = account.last(fmt)
>>> data
'{"accountStatement":{"info":{"accountId": ...(long output)... '
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
>>> list(fio_banka.get_transactions(data))[:2]
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
Transaction(
    transaction_id="10000000001",
    date=datetime.date(2023, 1, 2),
    amount=Decimal("-1500.89"),
    currency="CZK",
    account_id="9876543210",
    account_name="",
    bank_id="0800",
    bank_name="Česká spořitelna, a.s.",
    ks="0558",
    vs="0001",
    ss="0002",
    user_identification=None,
    remittance_info=None,  # Zprava pro prijemce
    type="Okamžitá odchozí platba",
    executor="Novák, Jan",
    specification=None,
    comment=None,
    bic=None,
    order_id=30000000001,
    payer_reference=None,
)
```

## Contributing

Set up development environment via [Pipenv](https://pipenv.pypa.io/en/latest/):
```bash
pipenv install --dev -e .
pipenv run pre-commit install
```

> [!NOTE]
> If you prefer to create the virtual environment in the project's directory, add `PIPENV_VENV_IN_PROJECT=1` into `.env` file. For more info see [Virtualenv mapping caveat](https://pipenv.pypa.io/en/latest/installation/#virtualenv-mapping-caveat).

Run tests:
```bash
pytest
```

Use [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/).

## License

This project is licensed under the terms of the MIT license.
