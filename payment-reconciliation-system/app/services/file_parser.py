import numpy as np
import pandas as pd

REQUIRED_COLUMNS = ("transaction_id", "amount")


class ParseError(ValueError):
    """The uploaded file is not a usable transactions CSV."""


def parse_csv(file, label: str = "file") -> pd.DataFrame:
    """Read and validate a transactions CSV.

    Required columns: transaction_id, amount. Extra columns are ignored.
    Returns a frame with a string `transaction_id` and an integer
    `amount_minor` (amount in minor units, e.g. paise/cents) so money is
    compared exactly instead of as floating point.
    """
    try:
        df = pd.read_csv(file.file, dtype=str, skipinitialspace=True)
    except pd.errors.EmptyDataError:
        raise ParseError(f"{label}: file is empty")
    except (pd.errors.ParserError, UnicodeDecodeError) as exc:
        raise ParseError(f"{label}: not a valid CSV ({exc})")

    df.columns = [str(c).strip().lower() for c in df.columns]
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ParseError(
            f"{label}: missing required column(s) {missing}; found {list(df.columns)}"
        )

    df = df.dropna(how="all").copy()
    if df.empty:
        raise ParseError(f"{label}: no data rows")

    ids = df["transaction_id"].str.strip()
    bad_ids = ids.isna() | (ids == "")
    if bad_ids.any():
        raise ParseError(f"{label}: blank transaction_id on line(s) {_lines(df, bad_ids)}")
    df["transaction_id"] = ids

    amounts = pd.to_numeric(df["amount"].str.replace(",", "", regex=False), errors="coerce")
    bad_amounts = ~np.isfinite(amounts)
    if bad_amounts.any():
        raise ParseError(
            f"{label}: missing or non-numeric amount on line(s) {_lines(df, bad_amounts)}"
        )
    df["amount_minor"] = (amounts * 100).round().astype("int64")

    return df[["transaction_id", "amount_minor"]].reset_index(drop=True)


def _lines(df: pd.DataFrame, mask: pd.Series, limit: int = 5) -> str:
    # +2: one for the header row, one because CSV lines are 1-indexed.
    lines = [int(i) + 2 for i in df.index[mask][:limit]]
    extra = int(mask.sum()) - len(lines)
    return ", ".join(map(str, lines)) + (f" (+{extra} more)" if extra > 0 else "")
