import pandas as pd

from app.config import AMOUNT_TOLERANCE, MAX_DETAIL_ROWS


def _to_units(minor) -> float:
    return round(int(minor) / 100, 2)


def _records(df: pd.DataFrame, limit: int) -> list:
    out = []
    for row in df.head(limit).itertuples(index=False):
        rec = {"transaction_id": row.transaction_id}
        if hasattr(row, "amount_minor_internal") and pd.notna(row.amount_minor_internal):
            rec["internal_amount"] = _to_units(row.amount_minor_internal)
        if hasattr(row, "amount_minor_bank") and pd.notna(row.amount_minor_bank):
            rec["bank_amount"] = _to_units(row.amount_minor_bank)
        if hasattr(row, "amount_minor") and pd.notna(row.amount_minor):
            rec["amount"] = _to_units(row.amount_minor)
        if "internal_amount" in rec and "bank_amount" in rec:
            rec["difference"] = round(rec["internal_amount"] - rec["bank_amount"], 2)
        out.append(rec)
    return out


def reconcile_data(
    internal_df: pd.DataFrame,
    bank_df: pd.DataFrame,
    tolerance: float = AMOUNT_TOLERANCE,
    max_detail_rows: int = MAX_DETAIL_ROWS,
) -> dict:
    """Match internal records to bank records by transaction_id.

    A transaction_id that appears more than once on either side is ambiguous
    (a plain merge would multiply rows and inflate every count), so those
    rows are set aside under `duplicates_*` for manual review.
    """
    tol_minor = int(round(tolerance * 100))

    dup_ids = set(internal_df.loc[internal_df["transaction_id"].duplicated(keep=False), "transaction_id"])
    dup_ids |= set(bank_df.loc[bank_df["transaction_id"].duplicated(keep=False), "transaction_id"])

    dup_internal = internal_df[internal_df["transaction_id"].isin(dup_ids)]
    dup_bank = bank_df[bank_df["transaction_id"].isin(dup_ids)]
    clean_internal = internal_df[~internal_df["transaction_id"].isin(dup_ids)]
    clean_bank = bank_df[~bank_df["transaction_id"].isin(dup_ids)]

    merged = clean_internal.merge(
        clean_bank,
        on="transaction_id",
        how="outer",
        suffixes=("_internal", "_bank"),
        indicator=True,
    )

    both = merged["_merge"] == "both"
    diff = (merged["amount_minor_internal"] - merged["amount_minor_bank"]).abs()
    matched = merged[both & (diff <= tol_minor)]
    mismatched = merged[both & (diff > tol_minor)]
    missing_in_bank = merged[merged["_merge"] == "left_only"]
    missing_in_internal = merged[merged["_merge"] == "right_only"]

    reconciled_total = len(matched) + len(mismatched) + len(missing_in_bank) + len(missing_in_internal)
    match_rate = round(100 * len(matched) / reconciled_total, 2) if reconciled_total else 0.0

    summary = {
        "total_internal": len(internal_df),
        "total_bank": len(bank_df),
        "perfect_matches": len(matched),
        "amount_mismatch": len(mismatched),
        "missing_in_bank": len(missing_in_bank),
        "missing_in_internal": len(missing_in_internal),
        "duplicate_rows_internal": len(dup_internal),
        "duplicate_rows_bank": len(dup_bank),
        "match_rate_percent": match_rate,
        "total_internal_amount": _to_units(internal_df["amount_minor"].sum()),
        "total_bank_amount": _to_units(bank_df["amount_minor"].sum()),
        "net_difference": _to_units(internal_df["amount_minor"].sum() - bank_df["amount_minor"].sum()),
        "amount_tolerance": tolerance,
    }

    details = {
        "amount_mismatch": _records(mismatched, max_detail_rows),
        "missing_in_bank": _records(missing_in_bank, max_detail_rows),
        "missing_in_internal": _records(missing_in_internal, max_detail_rows),
        "duplicates_internal": _records(dup_internal, max_detail_rows),
        "duplicates_bank": _records(dup_bank, max_detail_rows),
    }
    summary["details_truncated"] = any(
        n > max_detail_rows
        for n in (
            len(mismatched),
            len(missing_in_bank),
            len(missing_in_internal),
            len(dup_internal),
            len(dup_bank),
        )
    )

    return {"summary": summary, "details": details}
