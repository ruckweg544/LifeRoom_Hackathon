from app.services.money import cents_to_dollars, dollars_to_cents, format_cents_usd, split_equally


def test_dollars_to_cents_basic():
    assert dollars_to_cents(90.00) == 9000
    assert dollars_to_cents(24.5) == 2450


def test_dollars_to_cents_rounds_floating_point_error():
    # 19.99 is not exactly representable in binary float; this must still land on 1999.
    assert dollars_to_cents(19.99) == 1999


def test_split_equally_even():
    shares = split_equally(9000, 4)
    assert shares == [2250, 2250, 2250, 2250]
    assert sum(shares) == 9000


def test_split_equally_uneven_distributes_remainder():
    # 100 cents / 3 people = 33.33... -> remainder cents go to the first participants.
    shares = split_equally(100, 3)
    assert shares == [34, 33, 33]
    assert sum(shares) == 100


def test_split_equally_single_participant():
    assert split_equally(500, 1) == [500]


def test_split_equally_rejects_zero_participants():
    try:
        split_equally(100, 0)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_format_cents_usd():
    assert format_cents_usd(9000) == "$90.00"
    assert format_cents_usd(2450) == "$24.50"
    assert format_cents_usd(-150) == "-$1.50"


def test_cents_to_dollars_roundtrip():
    assert cents_to_dollars(dollars_to_cents(12.34)) == 12.34
