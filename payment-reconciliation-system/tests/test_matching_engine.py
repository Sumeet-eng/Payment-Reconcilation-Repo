import pandas as pd

from app.services.matching_engine import reconcile_data


def frame(rows):
    return pd.DataFrame(rows, columns=["transaction_id", "amount_minor"])


def test_all_four_outcomes():
    internal = frame([("A", 10000), ("B", 5000), ("C", 1000)])
    bank = frame([("A", 10000), ("B", 5500), ("D", 700)])

    result = reconcile_data(internal, bank, tolerance=0)
    s, d = result["summary"], result["details"]

    assert s["perfect_matches"] == 1
    assert s["amount_mismatch"] == 1
    assert s["missing_in_bank"] == 1
    assert s["missing_in_internal"] == 1
    assert d["amount_mismatch"] == [
        {"transaction_id": "B", "internal_amount": 50.0, "bank_amount": 55.0, "difference": -5.0}
    ]
    assert d["missing_in_bank"][0]["transaction_id"] == "C"
    assert d["missing_in_internal"][0]["transaction_id"] == "D"
    assert s["net_difference"] == 100.0 + 50.0 + 10.0 - 100.0 - 55.0 - 7.0


def test_tolerance_turns_small_difference_into_match():
    internal = frame([("A", 10000)])
    bank = frame([("A", 10001)])  # one paisa apart
    assert reconcile_data(internal, bank, tolerance=0)["summary"]["amount_mismatch"] == 1
    assert reconcile_data(internal, bank, tolerance=0.01)["summary"]["perfect_matches"] == 1


def test_duplicates_are_set_aside_not_multiplied():
    internal = frame([("A", 100), ("A", 100), ("B", 200)])
    bank = frame([("A", 100), ("B", 200)])

    s = reconcile_data(internal, bank)["summary"]

    assert s["perfect_matches"] == 1  # only B; the old plain merge would have produced 3 rows
    assert s["duplicate_rows_internal"] == 2
    assert s["duplicate_rows_bank"] == 1  # A on the bank side is ambiguous too
    assert s["missing_in_bank"] == 0 and s["missing_in_internal"] == 0


def test_detail_lists_are_capped_but_counts_are_exact():
    internal = frame([(f"T{i}", 100) for i in range(10)])
    bank = frame([("X", 1)])

    result = reconcile_data(internal, bank, max_detail_rows=3)

    assert result["summary"]["missing_in_bank"] == 10
    assert len(result["details"]["missing_in_bank"]) == 3
    assert result["summary"]["details_truncated"] is True
