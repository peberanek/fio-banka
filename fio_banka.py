"""This module provides a wrapper and helper functions for Fio banka, a.s. API

* `Account`: wrapper for interaction with an account
* `TransactionsFmt`: enum of transaction report formats consumed by `Account` methods
* `AccountStatementFmt`: enum of account statement formats consumed by `Account` methods
* Type aliases: `Fmt` and a couple of `Optional*` types
* `AccountInfo`: container for account information
* `Transaction`: container for transaction data
* Exceptions: `RequestError` and `DataError`, both subclasses of `FioBankaError`
* `str_to_date`: helper function for parsing date strings
* `get_account_info`: helper function for getting `AccountInfo`
* `get_transactions`: helper generator yielding `Transaction` objects

Basic usage:
    >>> from fio_banka import Account, TransactionsFmt, get_account_info, get_transactions
    >>> account = Account("<your-token>")
    >>> data = account.last(TransactionsFmt.JSON)
    >>> get_account_info(data)
    AccountInfo(
        account_id='2000000000',
        bank_id='2010',
        currency='CZK',
        iban='CZ1000000000002000000000',
        ...
    )
    >>> get_transactions(data)
    Transaction(
        transaction_id='10000000000',
        date=datetime.date(2023, 1, 1),
        amount=Decimal('2000.0'),
        currency='CZK',
        account=None,
        ...
    )
"""
import json
from collections.abc import Callable, Generator
from datetime import date
from decimal import Decimal
from enum import StrEnum, auto, unique
from typing import NamedTuple

import requests


@unique
class TransactionsFmt(StrEnum):
    """An Enum of transaction report formats"""

    CSV = auto()
    GPC = auto()
    HTML = auto()
    JSON = auto()
    OFX = auto()
    XML = auto()


@unique
class AccountStatementFmt(StrEnum):
    """An Enum of account statement formats"""

    CSV = auto()
    GPC = auto()
    HTML = auto()
    JSON = auto()
    OFX = auto()
    XML = auto()
    PDF = auto()
    MT940 = auto()
    CBA_XML = auto()
    SBA_XML = auto()


Fmt = TransactionsFmt | AccountStatementFmt
OptionalStr = str | None
OptionalDecimal = Decimal | None
OptionalDate = date | None
OptionalInt = int | None


class AccountInfo(NamedTuple):
    """Container for account information"""

    account_id: OptionalStr
    bank_id: OptionalStr
    currency: OptionalStr
    iban: OptionalStr
    bic: OptionalStr
    opening_balance: OptionalDecimal
    closing_balance: OptionalDecimal
    date_start: OptionalDate
    date_end: OptionalDate
    year_list: OptionalInt
    id_list: OptionalInt
    id_from: OptionalInt
    id_to: OptionalInt
    id_last_download: OptionalInt


class Transaction(NamedTuple):
    """Container for transaction data"""

    transaction_id: str
    date: date
    amount: Decimal
    currency: str
    account: OptionalStr
    account_name: OptionalStr
    bank_id: OptionalStr
    bank_name: OptionalStr
    ks: OptionalStr
    vs: OptionalStr
    ss: OptionalStr
    user_identification: OptionalStr
    recipient_message: OptionalStr
    type: OptionalStr
    executor: OptionalStr
    specification: OptionalStr
    comment: OptionalStr
    bic: OptionalStr
    order_id: OptionalInt
    payer_reference: OptionalStr


class FioBankaError(Exception):
    """Base exception for all custom exceptions"""


class RequestError(FioBankaError):
    """Raised when a server or a client error occurs.

    Args:
        message (str): an error message
        status_code (int): an HTTP response status code

    Attrs:
        status_code (int): an HTTP response status code
    """

    # https://stackoverflow.com/a/1319675
    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self._status_code = status_code

    @property
    def status_code(self):
        return self._status_code


class DataError(FioBankaError):
    """Raised when the fetched data are invalid."""


def _parse_data(data: str):
    # json.JSONDecodeError is subclass of ValueError
    return json.loads(data, parse_float=Decimal)


def _check_type(data, _type):
    if not isinstance(data, _type):
        raise DataError(f"Unexpected data type: {type(data)}, expected {_type}")
    return data


def str_to_date(date_str: str) -> date:
    """Return date from a string that begins with a date in ISO format.

    Args:
        date_str (str): a date string, e.g. '2023-01-01+0100'

    Raises:
        ValueError: raised when date_str cannot be parsed

    Returns:
        date
    """
    return date.fromisoformat(date_str[:10])


def get_account_info(data: str) -> AccountInfo:
    """Return account information from data.

    Args:
        data (str): a JSON string representing transactions or
            an account statement

    Raises:
        ValueError: raised when input data are invalid

    Returns:
        AccountInfo: a data structure representing account information
    """
    try:
        info = _parse_data(data)["accountStatement"]["info"]
    except KeyError as exc:
        raise ValueError(f"Missing key in data: {exc}")
    return AccountInfo(
        account_id=info["accountId"],
        bank_id=info["bankId"],
        currency=info["currency"],
        iban=info["iban"],
        bic=info["bic"],
        opening_balance=info["openingBalance"],
        closing_balance=info["closingBalance"],
        date_start=str_to_date(info["dateStart"]),
        date_end=str_to_date(info["dateEnd"]),
        year_list=info["yearList"],
        id_list=info["idList"],
        id_from=info["idFrom"],
        id_to=info["idTo"],
        id_last_download=info["idLastDownload"],
    )


def get_transactions(data: str) -> Generator[Transaction, None, None]:
    """Return generator yielding transactions from data.

    Args:
        data (str): a JSON string representing transactions or
            an account statement

    Raises:
        ValueError: raised when input data are invalid

    Yields:
        Generator[Transaction, None, None]
    """

    def get_value(data, key, coerce: Callable | None = None):
        if data[key] is None:
            return None
        value = data[key]["value"]
        if coerce is not None:
            return coerce(value)
        return value

    try:
        txns = _parse_data(data)["accountStatement"]["transactionList"]["transaction"]
    except KeyError as exc:
        raise ValueError(f"Missing key in data: {exc}")
    for txn in txns:
        yield Transaction(
            transaction_id=get_value(txn, "column22", coerce=str),  # str
            date=get_value(txn, "column0", coerce=str_to_date),
            amount=get_value(txn, "column1"),
            currency=get_value(txn, "column14"),
            account=get_value(txn, "column2"),
            account_name=get_value(txn, "column10"),
            bank_id=get_value(txn, "column3"),
            bank_name=get_value(txn, "column12"),
            ks=get_value(txn, "column4"),
            vs=get_value(txn, "column5"),
            ss=get_value(txn, "column6"),
            user_identification=get_value(txn, "column7"),
            recipient_message=get_value(txn, "column16"),
            type=get_value(txn, "column8"),
            executor=get_value(txn, "column9"),
            specification=get_value(txn, "column18"),
            comment=get_value(txn, "column25"),
            bic=get_value(txn, "column26"),
            order_id=get_value(txn, "column17"),  # int
            payer_reference=get_value(txn, "column27"),
        )


class Account:
    """Wrapper for interaction with an account

    Class vars:
        REQUEST_TIMELIMIT (int): time limit in seconds for 1 API request

    Args:
        token (str): an unique string 64 characters long

    Raises:
        ValueError: raised when the provided token has an invalid format
    """

    _BASE_URL = "https://www.fio.cz/ib_api/rest"
    REQUEST_TIMELIMIT = 30  # seconds

    def __init__(self, token: str) -> None:
        token_len = 64
        if len(token) != token_len:
            raise ValueError(f"Token has to be {token_len} characters long")
        self._token = token
        self._timeout = 10  # seconds

    def _request(self, url: str, fmt: Fmt | None) -> str | bytes:
        response: requests.Response = requests.get(
            self._BASE_URL + url, timeout=self._timeout
        )
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            # Make sure token value is not leaked into error msg.
            message = str(exc).replace(self._token, "TOKEN_VALUE_IS_HIDDEN")
            raise RequestError(message, response.status_code) from exc
        match fmt:
            case AccountStatementFmt.PDF:
                return response.content  # bytes
            case TransactionsFmt.GPC | AccountStatementFmt.GPC:
                response.encoding = "cp1250"
        return response.text

    def periods(self, date_from: date, date_to: date, fmt: TransactionsFmt) -> str:
        """Return transactions for a specific time period.

        Args:
            date_from (date): start date
            date_to (date): end date
            fmt (TransactionsFmt): format of the fetched data

        Raises:
            RequestError: raised when a server or a client error occurs
            DataError: raised when the fetched data are invalid

        Returns:
            str
        """
        url = (
            f"/periods/{self._token}/{date_from.isoformat()}/{date_to.isoformat()}"
            f"/transactions.{fmt}"
        )
        return _check_type(self._request(url, fmt), str)

    def by_id(self, year: int, id: int, fmt: AccountStatementFmt) -> str | bytes:
        """Return official account statement.

        Args:
            year (int): year of the account statement
            id (int): ID of the account statement
            fmt (StatementFmt): format of the fetched data

        Returns:
            str | bytes: bytes when the format is PDF, str otherwise
        """
        url = f"/by-id/{self._token}/{year}/{id}/transactions.{fmt}"
        return self._request(url, fmt)

    def last(self, fmt: TransactionsFmt) -> str:
        """Return transactions since the last download.

        Args:
            fmt (TransactionsFmt): format of the fetched data

        Raises:
            RequestError: raised when a server or a client error occurs
            DataError: raised when the fetched data are invalid

        Returns:
            str
        """
        url = f"/last/{self._token}/transactions.{fmt}"
        return _check_type(self._request(url, fmt), str)

    def set_last_id(self, id: int) -> None:
        """Set ID of the last successfully downloaded transaction.

        Args:
            id (int): transaction ID

        Raises:
            RequestError: raised when a server or a client error occurs
        """
        url = f"/set-last-id/{self._token}/{id}/"
        self._request(url, None)

    def set_last_date(self, date: date) -> None:
        """Set date of the last unsuccessful download.

        Args:
            date (date): download date

        Raises:
            RequestError: raised when a server or a client error occurs
        """
        url = f"/set-last-date/{self._token}/{date.isoformat()}/"
        self._request(url, None)

    def last_statement(self) -> tuple[int, int]:
        """Return year and ID of the last official account statement.

        Raises:
            RequestError: raised when a server or a client error occurs
            DataError: raised when the fetched data are invalid

        Returns:
            tuple[int, int]: year and ID of the last official account statement
        """
        url = f"/lastStatement/{self._token}/statement"
        year, _id = _check_type(self._request(url, None), str).split(",")
        return (int(year), int(_id))
