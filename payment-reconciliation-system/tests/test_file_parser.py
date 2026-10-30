import io
from types import SimpleNamespace

import pytest

from app.services.file_parser import ParseError, parse_csv


def upload(text: str):
    return SimpleNamespace(file=io.BytesIO(text.encode()))


def test_parses_and_normalises():
    df = parse_csv(upload(" Transaction_ID , Amount \n T1 ,\"1,234.50\"\nT2,10\n"))
    assert list(df["transaction_id"]) == ["T1", "T2"]
    assert list(df["amount_minor"]) == [123450, 1000]


def test_numeric_looking_ids_stay_strings():
    df = parse_csv(upload("transaction_id,amount\n001,5\n"))
    assert df["transaction_id"].iloc[0] == "001"  # leading zeros survive


@pytest.mark.parametrize(
    "text, fragment",
    [
        ("", "empty"),
        ("id,amt\n1,2\n", "missing required column"),
        ("transaction_id,amount\n", "no data rows"),
        ("transaction_id,amount\nT1,abc\n", "non-numeric amount on line\\(s\\) 2"),
        ("transaction_id,amount\nT1,\n", "non-numeric amount"),
        ("transaction_id,amount\n,5\n", "blank transaction_id on line\\(s\\) 2"),
    ],
)
def test_bad_input_raises_parse_error(text, fragment):
    with pytest.raises(ParseError, match=fragment):
        parse_csv(upload(text))
