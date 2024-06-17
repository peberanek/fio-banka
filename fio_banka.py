"""Fio banka API.

API description:
    https://www.fio.cz/docs/cz/API_Bankovnictvi.pdf (Czech only)

`REQUEST_TIMELIMIT_IN_SECONDS`: time limit for 1 request.
`AccountStatementFmt`: enum of account statement formats.
`TransactionReportFmt`: enum of transaction report formats.
`AccountInfo`: named tuple of account information.
`Transaction`: named tuple of a single transaction data.
`FioBankaError`: base exception.
    `RequestError`: an HTTP request could not be fulfilled.
        `InvalidRequestError`: request is invalid (typically URL or token).
        `TimeLimitError`: request time limit has been exceeded.
        `InvalidTokenError`: token is inactive or invalid.
        `TooManyItemsError`: the number of transactions exceeds 50000.
        `AuthorizationError`: token is not authorized to fetch data (e.g. data
            older then N days).
`Account`: client for interaction with an account.
    `fetch_transaction_report_for_period()`: return transaction report for
        a given time period.
    `fetch_account_statement()`: return account statement.
    `fetch_transaction_report_since_last_download()`: return transaction report
        since the last download.
    `fetch_last_account_statement_info()`: return year and ID of the last
        account statement.
    `set_last_downloaded_transaction_id()`: set ID of the last successfully
        downloaded transaction.
    `set_last_unsuccessful_download_date()`: set date of the last unsucessful
        download.
    `parse_account_info()`: return account information from a JSON string.
    `parse_transactions()`: return transactions from a JSON string.

Example usage:
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
"""

import collections.abc
import datetime
import decimal
import enum
import json
import typing

import requests

REQUEST_TIMELIMIT_IN_SECONDS = 30


@enum.unique
class AccountStatementFmt(enum.StrEnum):
    """Enum of account statement formats."""

    CSV = enum.auto()
    GPC = enum.auto()
    HTML = enum.auto()
    JSON = enum.auto()
    OFX = enum.auto()
    XML = enum.auto()
    PDF = enum.auto()
    MT940 = enum.auto()
    CBA_XML = enum.auto()
    SBA_XML = enum.auto()


@enum.unique
class TransactionReportFmt(enum.StrEnum):
    """Enum of transaction report formats."""

    CSV = enum.auto()
    GPC = enum.auto()
    HTML = enum.auto()
    JSON = enum.auto()
    OFX = enum.auto()
    XML = enum.auto()


_OptionalStr = str | None
_OptionalDecimal = decimal.Decimal | None
_OptionalDate = datetime.date | None
_OptionalInt = int | None
_Fmt = AccountStatementFmt | TransactionReportFmt


class AccountInfo(typing.NamedTuple):
    """Account information."""

    account_id: _OptionalStr
    bank_id: _OptionalStr
    currency: _OptionalStr
    iban: _OptionalStr
    bic: _OptionalStr
    opening_balance: _OptionalDecimal
    closing_balance: _OptionalDecimal
    date_start: _OptionalDate
    date_end: _OptionalDate
    year_list: _OptionalInt
    id_list: _OptionalInt
    id_from: _OptionalInt
    id_to: _OptionalInt
    id_last_download: _OptionalInt


class Transaction(typing.NamedTuple):
    """Transaction data."""

    transaction_id: str
    date: datetime.date
    amount: decimal.Decimal
    currency: str
    account_id: _OptionalStr
    account_name: _OptionalStr
    bank_id: _OptionalStr
    bank_name: _OptionalStr
    ks: _OptionalStr
    vs: _OptionalStr
    ss: _OptionalStr
    user_identification: _OptionalStr
    remittance_info: _OptionalStr
    type: _OptionalStr
    executor: _OptionalStr
    specification: _OptionalStr
    comment: _OptionalStr
    bic: _OptionalStr
    order_id: _OptionalInt
    payer_reference: _OptionalStr


class FioBankaError(Exception):
    """Base exception."""


class RequestError(FioBankaError):
    """An HTTP request could not be fulfilled."""

    def __init__(self) -> None:  # noqa: D107
        super().__init__(self.__class__.__doc__)


class InvalidRequestError(RequestError):
    """Request is invalid (typically URL or token)."""


class TimeLimitError(RequestError):
    """Request time limit has been exceeded."""


class InvalidTokenError(RequestError):
    """Token is inactive or invalid."""


class TooManyItemsError(RequestError):
    """The number of transactions exceeds 50000."""


class AuthorizationError(RequestError):
    """Token is not authorized to fetch data (e.g. data older than N days)."""


def _parse_date(fio_date: str) -> datetime.date:
    return datetime.date.fromisoformat(fio_date[:10])


def _parse_json(data: str):
    return json.loads(data, parse_float=decimal.Decimal)


class Account:
    """Client for interaction with an account."""

    _BASE_URL = "https://fioapi.fio.cz/v1/rest"
    _TOKEN_LEN = 64
    # https://requests.readthedocs.io/en/latest/user/advanced/#timeouts
    # It's a good practice to set connect timeouts to slightly larger than
    # a multiple of 3, which is the default TCP packet retransmission window.
    _TIMEOUT_IN_SECONDS = 10

    def __init__(self, token: str) -> None:
        """Return Account instance.

        Args:
            token (str): API token (64 characters long)
        """
        if len(token) != self._TOKEN_LEN:
            raise ValueError(f"Invalid token length: token must have {self._TOKEN_LEN} characters")
        self._token = token

    def _request(self, url: str, fmt: _Fmt | None) -> requests.Response:
        # IMPORTANT: As the API token is included in the URL, make sure it
        # is not shown in traceback. Use the `from` clause with caution.
        try:
            response = requests.get(self._BASE_URL + url, timeout=self._TIMEOUT_IN_SECONDS)
        except requests.exceptions.RequestException:
            # Timeout is typically hit when using an invalid token.
            raise InvalidRequestError from None
        try:
            response.raise_for_status()
        except requests.HTTPError:
            exception: type[RequestError]
            match response.status_code:
                case 404:
                    exception = InvalidRequestError
                case 409:
                    exception = TimeLimitError
                case 413:
                    exception = TooManyItemsError
                case 422:
                    exception = AuthorizationError
                case 500:
                    exception = InvalidTokenError
                case _:
                    exception = RequestError
            raise exception from None
        match fmt:
            case TransactionReportFmt.GPC | AccountStatementFmt.GPC:
                response.encoding = "cp1250"
        return response

    @staticmethod
    def _check_fmt(fmt: _Fmt, fmt_type: type[_Fmt]) -> None:
        if not isinstance(fmt, fmt_type):
            raise TypeError(f"Invalid type: `fmt` must be a member of {fmt_type.__name__} enum")

    def _request_transaction_report(self, url: str, fmt: TransactionReportFmt) -> str:
        self._check_fmt(fmt, TransactionReportFmt)
        return self._request(url, fmt).text

    def _request_account_statement(self, url: str, fmt: AccountStatementFmt) -> str | bytes:
        self._check_fmt(fmt, AccountStatementFmt)
        response = self._request(url, fmt)
        if fmt == AccountStatementFmt.PDF:
            return response.content  # bytes
        return response.text

    def fetch_transaction_report_for_period(
        self, date_from: datetime.date, date_to: datetime.date, fmt: TransactionReportFmt
    ) -> str:
        """Return transaction report for the given time period.

        Args:
            date_from (datetime.date): start date
            date_to (datetime.date): end date
            fmt (TransactionsReportFmt): transaction report format

        Raises:
            RequestError or any of its subclasses.

        Side effects:
            Calls Fio banka API.

        Returns:
            str: transaction report
        """
        if date_from > date_to:
            raise ValueError("Invalid date: `date_from` must be less than or equal to `date_to`")
        url = (
            f"/periods/{self._token}/{date_from.isoformat()}/{date_to.isoformat()}/"
            f"transactions.{fmt}"
        )
        return self._request_transaction_report(url, fmt)

    def fetch_account_statement(
        self, year: int, statement_id: int, fmt: AccountStatementFmt
    ) -> str | bytes:
        """Return account statement.

        Args:
            year (int): year of the account statement
            statement_id (int): ID of the account statement
            fmt (AccountStatementFmt): account statement format

        Raises:
            RequestError or any of its subclasses.

        Side effects:
            Calls Fio banka API.

        Returns:
            str | bytes: account statement (bytes when the format is PDF, str
                otherwise)
        """
        if statement_id < 0:
            raise ValueError(f"Invalid statement ID: '{statement_id}'; ID must be positive")
        url = f"/by-id/{self._token}/{year}/{statement_id}/transactions.{fmt}"
        return self._request_account_statement(url, fmt)

    def fetch_transaction_report_since_last_download(self, fmt: TransactionReportFmt) -> str:
        """Return transaction report since the last download.

        Args:
            fmt (TransactionReportFmt): transaction report format

        Raises:
            RequestError or any of its subclasses.

        Side effects:
            Calls Fio banka API.

        Returns:
            str: transaction report
        """
        url = f"/last/{self._token}/transactions.{fmt}"
        return self._request_transaction_report(url, fmt)

    def fetch_last_account_statement_info(self):
        """Return year and ID of the last account statement.

        Raises:
            RequestError or any of its subclasses.

        Side effects:
            Calls Fio banka API.

        Returns:
            tuple[int, int]: account statement year and ID
        """
        url = f"/lastStatement/{self._token}/statement"
        year, statement_id = self._request(url, None).text.split(",")
        return (int(year), int(statement_id))

    def set_last_downloaded_transaction_id(self, transaction_id: int) -> None:
        """Set ID of the last successfully downloaded transaction.

        Args:
            transaction_id (int): transaction ID

        Raises:
            RequestError or any of its subclasses.

        Side effects:
            Calls Fio banka API.
        """
        if transaction_id < 0:
            raise ValueError(f"Invalid transaction ID: '{transaction_id}'; ID must be positive")
        url = f"/set-last-id/{self._token}/{transaction_id}/"
        self._request(url, None)

    def set_last_unsuccessful_download_date(self, download_date: datetime.date) -> None:
        """Set date of the last unsuccessful download.

        Args:
            download_date (datetime.date): date of the last unsuccessful download

        Raises:
            RequestError or any of its subclasses.

        Side effects:
            Calls Fio banka API.
        """
        url = f"/set-last-date/{self._token}/{download_date.isoformat()}/"
        self._request(url, None)

    @staticmethod
    def parse_account_info(data: str) -> AccountInfo:
        """Return account information from data.

        Args:
            data (str): a JSON string representing transaction report or
                account statement

        Returns:
            AccountInfo: account information
        """
        info = _parse_json(data)["accountStatement"]["info"]
        return AccountInfo(
            account_id=info["accountId"],
            bank_id=info["bankId"],
            currency=info["currency"],
            iban=info["iban"],
            bic=info["bic"],
            opening_balance=info["openingBalance"],
            closing_balance=info["closingBalance"],
            date_start=_parse_date(info["dateStart"]),
            date_end=_parse_date(info["dateEnd"]),
            year_list=info["yearList"],
            id_list=info["idList"],
            id_from=info["idFrom"],
            id_to=info["idTo"],
            id_last_download=info["idLastDownload"],
        )

    @staticmethod
    def parse_transactions(data: str) -> collections.abc.Generator[Transaction, None, None]:
        """Yield transactions from data.

        Args:
            data (str): a JSON string representing transaction report or
                account statement

        Yields:
            Generator[Transaction, None, None]: transaction
        """

        def get_value(data, key, cast: collections.abc.Callable | None = None):
            value = data[key]["value"]
            if cast is not None:
                return cast(value)
            return value

        def get_value_or_none(data, key):
            if data[key] is None:
                return None
            return get_value(data, key)

        txns = _parse_json(data)["accountStatement"]["transactionList"]["transaction"]
        for txn in txns:
            yield Transaction(
                transaction_id=get_value(txn, "column22", cast=str),  # str
                date=get_value(txn, "column0", cast=_parse_date),
                amount=get_value(txn, "column1"),
                currency=get_value(txn, "column14"),
                account_id=get_value_or_none(txn, "column2"),
                account_name=get_value_or_none(txn, "column10"),
                bank_id=get_value_or_none(txn, "column3"),
                bank_name=get_value_or_none(txn, "column12"),
                ks=get_value_or_none(txn, "column4"),
                vs=get_value_or_none(txn, "column5"),
                ss=get_value_or_none(txn, "column6"),
                user_identification=get_value_or_none(txn, "column7"),
                remittance_info=get_value_or_none(txn, "column16"),
                type=get_value_or_none(txn, "column8"),
                executor=get_value_or_none(txn, "column9"),
                specification=get_value_or_none(txn, "column18"),
                comment=get_value_or_none(txn, "column25"),
                bic=get_value_or_none(txn, "column26"),
                order_id=get_value_or_none(txn, "column17"),  # int
                payer_reference=get_value_or_none(txn, "column27"),
            )
