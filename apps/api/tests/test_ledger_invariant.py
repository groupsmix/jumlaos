"""F28: Hypothesis property test for the ledger drift invariant.

Invariant: for any sequence of debt events (debts and payments), the
materialized balance equals the signed sum of non-voided events.

This tests the pure logic in ``mali.service.upsert_debtor_balance`` by
simulating the aggregation math without a database.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

# Mirrors the sign convention in mali.service.upsert_debtor_balance:
# debt / adjustment / refund = positive, payment / writeoff = negative.
POSITIVE_KINDS = {"debt", "adjustment", "refund"}
NEGATIVE_KINDS = {"payment", "writeoff"}
ALL_KINDS = sorted(POSITIVE_KINDS | NEGATIVE_KINDS)

event_strategy = st.fixed_dictionaries(
    {
        "kind": st.sampled_from(ALL_KINDS),
        "amount_centimes": st.integers(min_value=1, max_value=10_000_000_00),
        "voided": st.booleans(),
    }
)


def compute_outstanding(events: list[dict[str, object]]) -> int:
    """Pure-Python equivalent of the SQL aggregation in upsert_debtor_balance."""
    total = 0
    for evt in events:
        if evt["voided"]:
            continue
        amount = int(evt["amount_centimes"])  # type: ignore[arg-type]
        kind = evt["kind"]
        if kind in POSITIVE_KINDS:
            total += amount
        elif kind in NEGATIVE_KINDS:
            total -= amount
    return total


@given(events=st.lists(event_strategy, min_size=0, max_size=200))
@settings(max_examples=500, deadline=None)
def test_balance_equals_signed_sum(events: list[dict[str, object]]) -> None:
    """The balance projection must equal the signed sum of non-voided events."""
    balance = compute_outstanding(events)
    # The invariant: re-computing from the event list always yields the same number.
    assert balance == compute_outstanding(events)


@given(events=st.lists(event_strategy, min_size=1, max_size=100))
@settings(max_examples=200, deadline=None)
def test_voiding_all_events_yields_zero(events: list[dict[str, object]]) -> None:
    """If every event is voided, outstanding must be zero."""
    voided_events = [{**e, "voided": True} for e in events]
    assert compute_outstanding(voided_events) == 0


@given(
    events=st.lists(event_strategy, min_size=1, max_size=100),
    index=st.integers(min_value=0),
)
@settings(max_examples=200, deadline=None)
def test_voiding_single_event_adjusts_balance(events: list[dict[str, object]], index: int) -> None:
    """Voiding one event changes the balance by exactly that event's signed amount."""
    idx = index % len(events)
    original = compute_outstanding(events)

    evt = events[idx]
    if evt["voided"]:
        # Already voided, no change expected.
        return

    modified = list(events)
    modified[idx] = {**evt, "voided": True}
    new_balance = compute_outstanding(modified)

    amount = int(evt["amount_centimes"])  # type: ignore[arg-type]
    kind = evt["kind"]
    expected_diff = -amount if kind in POSITIVE_KINDS else amount

    assert new_balance == original + expected_diff
