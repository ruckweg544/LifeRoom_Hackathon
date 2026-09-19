"""
Currency math utilities.

All money is stored and computed in integer CENTS to avoid floating-point
rounding errors. Only convert to/from dollars at the API boundary.
"""
from decimal import Decimal, ROUND_HALF_UP


def dollars_to_cents(amount: float) -> int:
    """Convert a dollar float (from user input) to integer cents, rounding to the nearest cent."""
    return int((Decimal(str(amount)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def cents_to_dollars(cents: int) -> float:
    return cents / 100


def split_equally(total_cents: int, num_participants: int) -> list[int]:
    """
    Split total_cents equally among num_participants, distributing any
    leftover cents (from integer division) one-by-one to the first N
    participants so the shares always sum exactly to total_cents.
    """
    if num_participants <= 0:
        raise ValueError("num_participants must be positive")
    base_share = total_cents // num_participants
    remainder = total_cents - (base_share * num_participants)

    shares = [base_share] * num_participants
    for i in range(remainder):
        shares[i] += 1

    assert sum(shares) == total_cents
    return shares


def format_cents_usd(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    return f"{sign}${abs(cents) / 100:,.2f}"
