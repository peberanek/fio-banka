import os
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
import requests

from fio_banka import Account, AccountInfo
from fio_banka import AccountStatementFmt as ASFmt
from fio_banka import DataError, RequestError, Transaction
from fio_banka import TransactionsFmt as TFmt
from fio_banka import get_account_info, get_transactions, str_to_date

THIS_DIR = Path(os.path.dirname(os.path.realpath(__file__)))


class MockResponse:
    def __init__(self) -> None:
        self.content: bytes = b"content"
        self.text: str = "text"
        self.url: str | None = None
        self.error: tuple[str, int] | None = None
        self.status_code = 200

    def raise_for_status(self) -> None:
        if self.error is not None:
            self.status_code = self.error[1]
            raise requests.HTTPError(self.error[0], response=self)


# Prevent real API calls by autousing this fixture.
@pytest.fixture(name="mock_response", autouse=True)
def _mock_response(monkeypatch: pytest.MonkeyPatch) -> MockResponse:
    response = MockResponse()

    def mock_get(*args, **kwargs):
        response.url = args[0]
        return response

    monkeypatch.setattr(requests, "get", mock_get)
    return response


@pytest.fixture(name="transactions")
def _transactions():
    with (THIS_DIR / "transactions.json").open(encoding="utf-8") as file:
        return file.read()


def test_str_to_date():
    assert str_to_date("2023-01-01+0100") == date(2023, 1, 1)
    with pytest.raises(ValueError):
        str_to_date("2023-01")


def test_get_account_info(transactions):
    assert get_account_info(transactions) == AccountInfo(
        account_id="2000000000",
        bank_id="2010",
        currency="CZK",
        iban="CZ1000000000002000000000",
        bic="FIOBCZPPXXX",
        opening_balance=Decimal("1000.99"),
        closing_balance=Decimal("2000.10"),
        date_start=date(2023, 1, 1),
        date_end=date(2023, 1, 3),
        year_list=None,
        id_list=None,
        id_from=10000000000,
        id_to=10000000002,
        id_last_download=None,
    )
    with pytest.raises(ValueError, match="Expecting value"):
        get_account_info("")
    with pytest.raises(ValueError, match="Missing key"):
        get_account_info("{}")


def test_get_transactions(transactions):
    txns = list(get_transactions(transactions))
    # Check there are 3 unique transactions
    assert len({txn.transaction_id for txn in txns}) == len(txns) == 3
    for txn in txns:
        match txn.transaction_id:
            case "10000000000":
                assert txn == Transaction(
                    transaction_id="10000000000",
                    date=date(2023, 1, 1),
                    amount=Decimal("2000.00"),
                    currency="CZK",
                    account=None,
                    account_name="",
                    bank_id=None,
                    bank_name=None,
                    ks=None,
                    vs="1000",
                    ss=None,
                    user_identification="Nákup: example.com, dne 31.12.2022, částka  20.00 USD",
                    recipient_message="Nákup: example.com, dne 31.12.2022, částka  20.00 USD",
                    type="Platba kartou",
                    executor="Novák, Jan",
                    specification=None,
                    comment="Nákup: example.com, dne 31.12.2022, částka  20.00 USD",
                    bic=None,
                    order_id=30000000000,
                    payer_reference=None,
                )
            case "10000000001":
                assert txn == Transaction(
                    transaction_id="10000000001",
                    date=date(2023, 1, 2),
                    amount=Decimal("-1500.89"),
                    currency="CZK",
                    account="9876543210",
                    account_name="",
                    bank_id="0800",
                    bank_name="Česká spořitelna, a.s.",
                    ks="0558",
                    vs="0001",
                    ss="0002",
                    user_identification=None,
                    recipient_message=None,
                    type="Okamžitá odchozí platba",
                    executor="Novák, Jan",
                    specification=None,
                    comment=None,
                    bic=None,
                    order_id=30000000001,
                    payer_reference=None,
                )
            case "10000000002":
                assert txn == Transaction(
                    transaction_id="10000000002",
                    date=date(2023, 1, 3),
                    amount=Decimal("500.00"),
                    currency="CZK",
                    account="2345678901",
                    account_name="Pavel, Žák",
                    bank_id="2010",
                    bank_name="Fio banka, a.s.",
                    ks=None,
                    vs=None,
                    ss=None,
                    user_identification=None,
                    recipient_message=None,
                    type="Příjem převodem uvnitř banky",
                    executor=None,
                    specification="test specification",
                    comment=None,
                    bic="TESTBICXXXX",
                    order_id=30000000002,
                    payer_reference="test payer reference",
                )
            case _ as _id:
                pytest.fail(f"Unexpected transaction ID: {_id}")
    with pytest.raises(ValueError, match="Expecting value"):
        list(get_transactions(""))
    with pytest.raises(ValueError, match="Missing key"):
        list(get_transactions("{}"))


class TestAccount:
    BASE_URL = "https://www.fio.cz/ib_api/rest"

    @pytest.fixture(name="account")
    @staticmethod
    def _account() -> Account:
        return Account(
            "testKeyXZVZPOJ4pMrdnPleaUcdUlqy2LqFFVqI4dagXgi1eB1cgLzNjwsWS36bG"
        )

    @staticmethod
    def test___init__():
        Account("x" * 64)
        for token in ("x" * 63, "x" * 65):
            with pytest.raises(ValueError, match="Token has to"):
                Account(token)

    def test__request(self, mock_response: MockResponse, account: Account):
        url = "/foo"
        account._request(url, None)
        assert mock_response.url == self.BASE_URL + url
        assert account._request(url, ASFmt.PDF) == mock_response.content
        assert account._request(url, ASFmt.GPC) == mock_response.text

        error_msg = "Not found"
        error_code = 404
        mock_response.error = (error_msg, error_code)
        with pytest.raises(RequestError, match=error_msg) as excinfo:
            account._request(url, None)
        assert excinfo.value.status_code == error_code

    def test_periods(self, mock_response: MockResponse, account: Account):
        from_date = date(2023, 1, 1)
        to_date = from_date
        fmt = TFmt.JSON
        assert account.periods(from_date, to_date, fmt) == mock_response.text
        assert mock_response.url == (
            f"{self.BASE_URL}/periods/{account._token}"
            f"/{from_date.isoformat()}/{to_date.isoformat()}/transactions.{fmt}"
        )

    @pytest.mark.parametrize(
        "fmt,response_attr", [(ASFmt.PDF, "content"), (ASFmt.XML, "text")]
    )
    def test_by_id(
        self,
        fmt: ASFmt,
        response_attr: str,
        mock_response: MockResponse,
        account: Account,
    ):
        year = 2023
        _id = 1
        assert account.by_id(year, _id, fmt) == getattr(mock_response, response_attr)
        assert mock_response.url == (
            f"{self.BASE_URL}/by-id/{account._token}/{year}/{_id}/transactions.{fmt}"
        )

    def test_last(self, mock_response: MockResponse, account: Account):
        fmt = TFmt.XML
        assert account.last(fmt) == mock_response.text
        assert mock_response.url == (
            f"{self.BASE_URL}/last/{account._token}/transactions.{fmt}"
        )

    def test_set_last_id(self, mock_response: MockResponse, account: Account):
        _id = 1147608196
        account.set_last_id(_id)
        assert (
            mock_response.url == f"{self.BASE_URL}/set-last-id/{account._token}/{_id}/"
        )

    def test_set_last_date(self, mock_response: MockResponse, account: Account):
        _date = date(2023, 1, 1)
        account.set_last_date(_date)
        assert mock_response.url == (
            f"{self.BASE_URL}/set-last-date/{account._token}/{_date.isoformat()}/"
        )

    def test_last_statement(self, mock_response: MockResponse, account: Account):
        year = 2023
        _id = 1
        mock_response.text = f"{year},{_id}"
        assert account.last_statement() == (year, _id)
        assert mock_response.url == (
            f"{self.BASE_URL}/lastStatement/{account._token}/statement"
        )

    def test_request_error(self, mock_response: MockResponse, account: Account):
        error_msg = "Invalid token"
        error_code = 500
        mock_response.error = (error_msg, error_code)
        with pytest.raises(RequestError, match=error_msg) as excinfo:
            account.last(TFmt.JSON)
        assert excinfo.value.status_code == error_code

    def test_data_error(self, mock_response: MockResponse, account: Account):
        mock_response.text = b"bytes"  # type: ignore[assignment]
        with pytest.raises(DataError):
            account.last(TFmt.XML)
