"""Test the `fio_banka` module.

Notes:
    * There does not seem to be an easy way to test GPC format encoding
        (cp1250). Therefore, the encoding is not tested.
    * Official API docs don't limit year or date values. We don't want
        to speculate, therefore they are not tested. Sanity checks only.
    * Tests of invalid formats (account statement, transaction report) are
        covered by:
        `TestAccount.test_fetch_transaction_report_for_period_with_invalid_format`,
        `TestAccount.test_fetch_account_statement_with_invalid_format`.
    * Tests of `AccountInfo` and `Transaction` objects are covered by `Account`
        tests.
"""

import datetime
import decimal
import os
import pathlib

import pytest
import requests

# Avoid shadowing by pytest fixture of the same name
import requests_mock as _requests_mock

import fio_banka


def test_constants_are_present():
    assert hasattr(fio_banka, "REQUEST_TIMELIMIT_IN_SECONDS")


def test_transaction_report_formats():
    """Test that all supported transaction report formats are present."""
    assert sorted([member.value for member in fio_banka.TransactionReportFmt]) == sorted(
        ["csv", "gpc", "html", "json", "ofx", "xml"]
    )


def test_account_statement_formats():
    """Test that all supported transaction report formats are present."""
    assert sorted([member.value for member in fio_banka.AccountStatementFmt]) == sorted(
        ["csv", "gpc", "html", "json", "ofx", "xml", "pdf", "mt940", "cba_xml", "sba_xml"]
    )


def test_exceptions_are_present():
    assert sorted([e for e in dir(fio_banka) if e.endswith("Error")]) == sorted(
        [
            "FioBankaError",
            "RequestError",
            "InvalidRequestError",
            "TimeLimitError",
            "InvalidTokenError",
            "TooManyItemsError",
            "AuthorizationError",
        ]
    )


class TestAccount:
    BASE_URL = "https://fioapi.fio.cz/v1/rest"
    TOKEN = "testTokenXZVZPOJ4pMrdnPleaUcdUlqy2LqFFVqI4dagXgi1eB1cgLzNjwsWS36"

    @pytest.fixture()
    def account(self) -> fio_banka.Account:
        return fio_banka.Account(self.TOKEN)

    @staticmethod
    @pytest.fixture()
    def account_statement() -> str:
        this_dir = pathlib.Path(os.path.realpath(__file__)).parent
        with (this_dir / "account_statement.json").open("r") as f:
            return f.read()

    @staticmethod
    @pytest.mark.parametrize(
        "token",
        [TOKEN, "", TOKEN[:-1], TOKEN + "x"],
        ids=["valid", "empty", "too-short", "too-long"],
    )
    def test_token_length(token: str):
        """Test that a token with invalid length is refused."""
        if len(token) == 64:  # noqa: PLR2004
            fio_banka.Account(token)
        else:
            with pytest.raises(ValueError, match="Invalid token length"):
                fio_banka.Account(token)

    @pytest.mark.parametrize(
        "fmt", [fio_banka.TransactionReportFmt.JSON, fio_banka.TransactionReportFmt.XML]
    )
    def test_fetch_transaction_report_for_period(
        self,
        account: fio_banka.Account,
        requests_mock: _requests_mock.Mocker,
        fmt: fio_banka.TransactionReportFmt,
    ):
        """Test the method `fetch_transaction_report_for_period`.

        The method should call correct URL and return text data.
        """
        text = "dummy text"
        requests_mock.get(
            self.BASE_URL + f"/periods/{self.TOKEN}/2023-01-01/2023-01-02/transactions.{fmt}",
            text=text,
        )
        assert (
            account.fetch_transaction_report_for_period(
                datetime.date(2023, 1, 1), datetime.date(2023, 1, 2), fmt
            )
            == text
        )

    @staticmethod
    def test_fetch_transaction_report_for_period_with_invalid_date(
        account: fio_banka.Account, requests_mock: _requests_mock.Mocker
    ):
        """Test that an invalid date range is refused."""
        requests_mock.get(_requests_mock.ANY)
        with pytest.raises(ValueError, match="Invalid date"):
            account.fetch_transaction_report_for_period(
                datetime.date(2023, 1, 2),
                datetime.date(2023, 1, 1),
                fio_banka.TransactionReportFmt.JSON,
            )

    @staticmethod
    def test_fetch_transaction_report_for_period_with_invalid_format(
        account: fio_banka.Account, requests_mock: _requests_mock.Mocker
    ):
        """Test that an invalid or unsupported data format is refused."""
        requests_mock.get(_requests_mock.ANY)
        with pytest.raises(TypeError, match="Invalid type"):
            account.fetch_transaction_report_for_period(
                datetime.date(2023, 1, 1),
                datetime.date(2023, 1, 1),
                "foo",  # type: ignore[reportArgumentType,arg-type]
            )

    @pytest.mark.parametrize(
        "fmt",
        [
            fio_banka.AccountStatementFmt.JSON,
            fio_banka.AccountStatementFmt.GPC,
            fio_banka.AccountStatementFmt.PDF,
        ],
    )
    def test_fetch_account_statement(
        self,
        account: fio_banka.Account,
        requests_mock: _requests_mock.Mocker,
        fmt: fio_banka.AccountStatementFmt,
    ):
        """Test the method `fetch_account_statement`.

        The method should call correct URL and return text or binary data.
        """
        url = self.BASE_URL + f"/by-id/{self.TOKEN}/2023/1/transactions.{fmt}"
        payload: str | bytes
        if fmt == fio_banka.AccountStatementFmt.PDF:
            payload = b"dummy bytes"
            requests_mock.get(url, content=payload)
        else:
            payload = "dummy text"
            requests_mock.get(url, text=payload)
        assert account.fetch_account_statement(2023, 1, fmt) == payload

    @staticmethod
    def test_fetch_account_statement_with_invalid_id(
        account: fio_banka.Account,
        requests_mock: _requests_mock.Mocker,
    ):
        """Test that negative ID is refused."""
        requests_mock.get(_requests_mock.ANY)
        with pytest.raises(ValueError, match="Invalid statement ID"):
            account.fetch_account_statement(2023, -1, fio_banka.AccountStatementFmt.JSON)

    @staticmethod
    def test_fetch_account_statement_with_invalid_format(
        account: fio_banka.Account, requests_mock: _requests_mock.Mocker
    ):
        """Test that an invalid or unsupported data format is refused."""
        requests_mock.get(_requests_mock.ANY)
        with pytest.raises(TypeError, match="Invalid type"):
            account.fetch_account_statement(2023, 1, "bar")  # type: ignore[reportArgumentType,arg-type]

    @pytest.mark.parametrize(
        "fmt", [fio_banka.TransactionReportFmt.HTML, fio_banka.TransactionReportFmt.OFX]
    )
    def test_fetch_transaction_report_since_last_download(
        self,
        account: fio_banka.Account,
        requests_mock: _requests_mock.Mocker,
        fmt: fio_banka.TransactionReportFmt,
    ):
        """Test the method `fetch_transaction_report_since_last_download`.

        The method should call correct URL and return text data.
        """
        text = "dummy text"
        requests_mock.get(self.BASE_URL + f"/last/{self.TOKEN}/transactions.{fmt}", text=text)
        assert account.fetch_transaction_report_since_last_download(fmt) == text

    def test_fetch_last_account_statement_info(
        self,
        account: fio_banka.Account,
        requests_mock: _requests_mock.Mocker,
    ):
        """Test the method `fetch_last_account_statement_info`.

        The method should call correct URL and return a tuple with year and ID
        of the last account statement.
        """
        requests_mock.get(self.BASE_URL + f"/lastStatement/{self.TOKEN}/statement", text="2023,12")
        assert account.fetch_last_account_statement_info() == (2023, 12)

    def test_set_last_downloaded_transaction_id(
        self,
        account: fio_banka.Account,
        requests_mock: _requests_mock.Mocker,
    ):
        """Test the method `set_last_downloaded_transaction_id`.

        It should only call correct URL. No return value is expected.
        """
        transaction_id = 10000000000
        requests_mock.get(self.BASE_URL + f"/set-last-id/{self.TOKEN}/{transaction_id}/")
        account.set_last_downloaded_transaction_id(transaction_id)

    def test_set_last_downloaded_transaction_id_with_invalid_id(
        self,
        account: fio_banka.Account,
        requests_mock: _requests_mock.Mocker,
    ):
        """Test that an invalid ID is refused."""
        requests_mock.get(_requests_mock.ANY)
        with pytest.raises(ValueError, match="Invalid transaction ID"):
            account.set_last_downloaded_transaction_id(-1)

    def test_set_last_unsuccessful_download_date(
        self,
        account: fio_banka.Account,
        requests_mock: _requests_mock.Mocker,
    ):
        """Test the method `set_last_unsuccessful_download_date`.

        It should only call correct URL. No return value is expected.
        """
        requests_mock.get(self.BASE_URL + f"/set-last-date/{self.TOKEN}/2023-12-31/")
        account.set_last_unsuccessful_download_date(datetime.date(2023, 12, 31))

    @staticmethod
    def test_parse_account_info(account_statement: str):
        """Test the method `parse_account_info`.

        It should parse a JSON string and return an object representing account
        information.
        """
        assert fio_banka.Account.parse_account_info(account_statement) == fio_banka.AccountInfo(
            account_id="2000000000",
            bank_id="2010",
            currency="CZK",
            iban="CZ1000000000002000000000",
            bic="FIOBCZPPXXX",
            opening_balance=decimal.Decimal("4000.99"),
            closing_balance=decimal.Decimal("1000.10"),
            date_start=datetime.date(2023, 1, 1),
            date_end=datetime.date(2023, 1, 3),
            year_list=None,
            id_list=None,
            id_from=10000000000,
            id_to=10000000002,
            id_last_download=None,
        )

    @staticmethod
    def test_parse_transactions(account_statement: str):
        """Test the method `parse_transactions`.

        It should parse a JSON string and return generator yielding objects
        representing individual transactions.
        """
        txns = list(fio_banka.Account.parse_transactions(account_statement))
        total_txns = 3
        assert total_txns == len(txns) == len({txn.transaction_id for txn in txns})
        assert txns[0] == fio_banka.Transaction(
            transaction_id="10000000000",
            date=datetime.date(2023, 1, 1),
            amount=decimal.Decimal("-2000.00"),
            currency="CZK",
            account_id=None,
            account_name="",
            bank_id=None,
            bank_name=None,
            ks=None,
            vs="1000",
            ss=None,
            user_identification="Nákup: example.com, dne 31.12.2022, částka  2000.00 CZK",
            remittance_info="Nákup: example.com, dne 31.12.2022, částka  2000.00 CZK",
            type="Platba kartou",
            executor="Novák, Jan",
            specification=None,
            comment="Nákup: example.com, dne 31.12.2022, částka  2000.00 CZK",
            bic=None,
            order_id=30000000000,
            payer_reference=None,
        )

    @staticmethod
    def test_request_timeout(account: fio_banka.Account, requests_mock: _requests_mock.Mocker):
        """Test that a proper exception is raised on a request timeout."""
        requests_mock.get(_requests_mock.ANY, exc=requests.exceptions.ConnectTimeout)
        with pytest.raises(fio_banka.InvalidRequestError):
            account.fetch_transaction_report_for_period(
                datetime.date(2023, 1, 1),
                datetime.date(2023, 1, 1),
                fio_banka.TransactionReportFmt.JSON,
            )

    @staticmethod
    @pytest.mark.parametrize(
        ("status_code", "exception"),
        [
            (404, fio_banka.InvalidRequestError),
            (409, fio_banka.TimeLimitError),
            (413, fio_banka.TooManyItemsError),
            (422, fio_banka.AuthorizationError),
            (500, fio_banka.InvalidTokenError),
            (599, fio_banka.RequestError),
        ],
    )
    def test_request_error_status_codes(
        account: fio_banka.Account,
        requests_mock: _requests_mock.Mocker,
        status_code: int,
        exception: type[fio_banka.FioBankaError],
    ):
        """Test that a proper exception is raised in case of a request error."""
        requests_mock.get(_requests_mock.ANY, status_code=status_code)
        with pytest.raises(exception):
            account.fetch_transaction_report_for_period(
                datetime.date(2023, 1, 1),
                datetime.date(2023, 1, 1),
                fio_banka.TransactionReportFmt.JSON,
            )
