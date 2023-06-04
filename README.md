# Fio Banka API Client

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
>>> from fio_banka import Account, TransactionsFmt

>>> account = Account("<your-token>")
>>> fmt = TransactionsFmt.JSON
>>> account.periods(date(2023, 1, 1), date(2023, 1, 2), fmt)
'{"accountStatement":{"info":{"accountId": ... '

>>> try:
>>>     account.last(fmt)
>>> except RequestError as exc:
>>>     print(f"'{exc}'")
>>>     print(exc.status_code)
'409 Client Error:  for url: https://www.fio.cz/ib_api/rest/last/TOKEN_VALUE_IS_HIDDEN/transactions.json'
409
```

We hit request time limit: 1 request per token per 30 seconds. Let's be a good user.
```python
>>> import time
>>> time.sleep(account.REQUEST_TIMELIMIT)
>>> data = account.last(fmt)
>>> data
'{"accountStatement":{"info":{"accountId": ... '
```

Data extraction (make sure data are downloaded as *JSON*):
```python
>>> from fio_banka import get_account_info, get_transactions
>>> get_account_info(data)
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
>>> list(get_transactions(data))[0]
Transaction(
    transaction_id='10000000000',
    date=datetime.date(2023, 1, 1),
    amount=Decimal('2000.0'),
    currency='CZK',
    account=None,
    account_name='',
    bank_id=None,
    bank_name=None,
    ks=None,
    vs='1000',
    ss=None,
    user_identification='Nákup: example.com, dne 31.12.2022, částka  2000.00 CZK',
    recipient_message='Nákup: example.com, dne 31.12.2022, částka  2000.00 CZK',
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
make tests
```

## License

This project is licensed under the terms of the MIT license.
