"""A client and helper functions for Fio banka, a.s. API.

* REQUEST_TIMELIMIT (int): time limit in seconds for 1 API request
* `Account`: client for interaction with an account
* `TransactionsFmt`: enum of transaction report formats consumed by `Account` methods
* `AccountStatementFmt`: enum of account statement formats consumed by `Account` methods
* Type aliases: `Fmt` and a couple of `Optional*` types
* `AccountInfo`: container for account information
* `Transaction`: container for transaction data
* Exceptions:
    * `FioBankaError`: Base exception for all Fio banka exceptions.
        * `RequestError`: An HTTP request could not be fulfilled.
            * `InvalidRequestError`: Request (typically the URL) is invalid.
            * `TimeLimitError`: Request time limit has been exceeded.
            * `InvalidTokenError`: Token is inactive or invalid.
            * `TooManyItemsError`: The number of transactions exceeds 50000.
            * `AuthorizationError`: Token is not authorized to fetch historical data.
        * `ValidationError`: Fetched data are invalid.
* `str_to_date`: helper function for parsing date strings
* `get_account_info`: helper function for getting `AccountInfo`
* `get_transactions`: helper generator yielding `Transaction` objects

Basic usage:
    >>> from fio_banka import Account, TransactionsFmt, get_account_info, get_transactions
    >>> account = Account("<API-token>")
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
        account_id=None,
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

REQUEST_TIMELIMIT = 30  # seconds


@unique
class TransactionsFmt(StrEnum):
    """Transaction report formats."""

    CSV = auto()
    GPC = auto()
    HTML = auto()
    JSON = auto()
    OFX = auto()
    XML = auto()


@unique
class AccountStatementFmt(StrEnum):
    """Account statement formats."""

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
    """Container for account information."""

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
    """Container for transaction data."""

    transaction_id: str
    date: date
    amount: Decimal
    currency: str
    account_id: OptionalStr
    account_name: OptionalStr
    bank_id: OptionalStr
    bank_name: OptionalStr
    ks: OptionalStr
    vs: OptionalStr
    ss: OptionalStr
    user_identification: OptionalStr
    remittance_info: OptionalStr
    type: OptionalStr  # noqa: A003
    executor: OptionalStr
    specification: OptionalStr
    comment: OptionalStr
    bic: OptionalStr
    order_id: OptionalInt
    payer_reference: OptionalStr


class FioBankaError(Exception):
    """Base exception for all Fio banka exceptions."""


class RequestError(FioBankaError):
    """An HTTP request could not be fulfilled."""


class InvalidRequestError(RequestError):
    """Request (typically the URL) is invalid."""

    def __init__(self) -> None:
        """Initialize the exception."""
        super().__init__(
            "Invalid request. Make sure the URL and its parameters are correct.",
        )


class TimeLimitError(RequestError):
    """Request time limit has been exceeded."""

    def __init__(self) -> None:
        """Initialize the exception."""
        super().__init__(
            f"Exceeded time limit (1 request per {REQUEST_TIMELIMIT}s).",
        )


class InvalidTokenError(RequestError):
    """Token is inactive or invalid."""

    def __init__(self) -> None:
        """Initialize the exception."""
        super().__init__("Invalid token. Make sure the token is active and valid.")


class TooManyItemsError(RequestError):
    """The number of transactions exceeds 50000."""

    def __init__(self) -> None:
        """Initialize the exception."""
        super().__init__(
            "Too many items. Make sure the number of requested transactions is <= 50000.",
        )


class AuthorizationError(RequestError):
    """Token is not authorized to fetch historical data."""

    def __init__(self) -> None:
        """Initialize the exception."""
        super().__init__(
            "Authorization error. Make sure the token is authorized to fetch"
            " data older than 90 days. Follow instructions at"
            " https://www.fio.cz/docs/cz/API_Bankovnictvi.pdf, section 3.1.",
        )


class ValidationError(FioBankaError):
    """Fetched data are invalid."""


def _parse_data(data: str):
    # json.JSONDecodeError is a subclass of ValueError
    return json.loads(data, parse_float=Decimal)


def _check_type(data, _type):
    if not isinstance(data, _type):
        raise ValidationError(f"Unexpected data type: {type(data)}, expected {_type}")
    return data


def str_to_date(date_str: str) -> date:
    """Return date from a string that begins with a date in ISO format.

    Args:
        date_str (str): a date string, e.g. '2023-01-01+0100'

    Returns:
        date
    """
    return date.fromisoformat(date_str[:10])


def get_account_info(data: str) -> AccountInfo:
    """Return account information from data.

    Args:
        data (str): a JSON string representing transactions or
            an account statement

    Returns:
        AccountInfo: a data structure representing account information
    """
    try:
        info = _parse_data(data)["accountStatement"]["info"]
    except KeyError as exc:
        raise ValueError(f"Missing key in data: {exc}") from exc
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
    """Yield transactions from data.

    Args:
        data (str): a JSON string representing transactions or
            an account statement

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
        raise ValueError(f"Missing key in data: {exc}") from exc
    for txn in txns:
        yield Transaction(
            transaction_id=get_value(txn, "column22", coerce=str),  # str
            date=get_value(txn, "column0", coerce=str_to_date),
            amount=get_value(txn, "column1"),
            currency=get_value(txn, "column14"),
            account_id=get_value(txn, "column2"),
            account_name=get_value(txn, "column10"),
            bank_id=get_value(txn, "column3"),
            bank_name=get_value(txn, "column12"),
            ks=get_value(txn, "column4"),
            vs=get_value(txn, "column5"),
            ss=get_value(txn, "column6"),
            user_identification=get_value(txn, "column7"),
            remittance_info=get_value(txn, "column16"),
            type=get_value(txn, "column8"),
            executor=get_value(txn, "column9"),
            specification=get_value(txn, "column18"),
            comment=get_value(txn, "column25"),
            bic=get_value(txn, "column26"),
            order_id=get_value(txn, "column17"),  # int
            payer_reference=get_value(txn, "column27"),
        )


class Account:
    """Client for interaction with an account."""

    _BASE_URL = "https://www.fio.cz/ib_api/rest"

    def __init__(self, token: str) -> None:
        """Return an instance of the Account class.

        Args:
            token (str): an API token (64 characters long)
        """
        token_len = 64
        if len(token) != token_len:
            raise ValueError(f"Token has to be {token_len} characters long")
        self._token = token
        # https://requests.readthedocs.io/en/latest/user/advanced/#timeouts
        # It's a good practice to set connect timeouts to slightly larger than
        # a multiple of 3, which is the default TCP packet retransmission window.
        self._timeout = 10  # seconds

    def _request(self, url: str, fmt: Fmt | None) -> str | bytes:
        # WARNING: Raising exceptions from `requests` exceptions may leak
        # the API token (in the request URL) into traceback. Use the `from`
        # clause with caution.
        def hide_token(s: str) -> str:
            return s.replace(self._token, "****TOKEN****")

        try:
            response: requests.Response = requests.get(
                self._BASE_URL + url,
                timeout=self._timeout,
            )
        except requests.exceptions.RequestException as exc:
            # Timeout is typically hit when trying to use an invalid token.
            raise RequestError(hide_token(str(exc) + " (invalid token?)")) from None
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            exception: RequestError
            match response.status_code:
                case 404:
                    exception = InvalidRequestError()
                case 409:
                    exception = TimeLimitError()
                case 413:
                    exception = TooManyItemsError()
                case 422:
                    exception = AuthorizationError()
                case 500:
                    exception = InvalidTokenError()
                case _:
                    exception = RequestError(hide_token(str(exc)))
            raise exception from None
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
            ValidationError: raised when the fetched data are invalid

        Returns:
            str
        """
        url = (
            f"/periods/{self._token}/{date_from.isoformat()}/{date_to.isoformat()}"
            f"/transactions.{fmt}"
        )
        return _check_type(self._request(url, fmt), str)

    def by_id(self, year: int, _id: int, fmt: AccountStatementFmt) -> str | bytes:
        """Return official account statement.

        Args:
            year (int): year of the account statement
            id (int): ID of the account statement
            fmt (StatementFmt): format of the fetched data

        Returns:
            str | bytes: bytes when the format is PDF, str otherwise
        """
        url = f"/by-id/{self._token}/{year}/{_id}/transactions.{fmt}"
        return self._request(url, fmt)

    def last(self, fmt: TransactionsFmt) -> str:
        """Return transactions since the last download.

        Args:
            fmt (TransactionsFmt): format of the fetched data

        Raises:
            RequestError: raised when a server or a client error occurs
            ValidationError: raised when the fetched data are invalid

        Returns:
            str
        """
        url = f"/last/{self._token}/transactions.{fmt}"
        return _check_type(self._request(url, fmt), str)

    def set_last_id(self, _id: int) -> None:
        """Set ID of the last successfully downloaded transaction.

        Args:
            id (int): transaction ID

        Raises:
            RequestError: raised when a server or a client error occurs
        """
        url = f"/set-last-id/{self._token}/{_id}/"
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
            ValidationError: raised when the fetched data are invalid

        Returns:
            tuple[int, int]: year and ID of the last official account statement
        """
        url = f"/lastStatement/{self._token}/statement"
        year, _id = _check_type(self._request(url, None), str).split(",")
        return (int(year), int(_id))
