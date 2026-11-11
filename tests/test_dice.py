import random

import pytest

from app_dnd.dice import Advantage, roll, roll_d20


class FixedRng:
    def __init__(self, *values: int) -> None:
        self._values = iter(values)

    def randint(self, a: int, b: int) -> int:
        return next(self._values)


def test_basic_roll_with_modifier():
    r = roll("2d6+3", FixedRng(4, 5))
    assert r.rolls == (4, 5) and r.total == 12 and r.modifier == 3


def test_implicit_count_and_negative_modifier():
    assert roll("d20-1", FixedRng(10)).total == 9


def test_keep_highest_for_attributes():
    r = roll("4d6kh3", FixedRng(6, 1, 5, 4))
    assert sorted(r.kept) == [4, 5, 6] and r.total == 15


def test_keep_lowest():
    assert roll("2d20kl1", FixedRng(17, 4)).total == 4


def test_advantage_and_disadvantage():
    assert roll_d20(5, Advantage.ADVANTAGE, FixedRng(3, 15)).total == 20
    assert roll_d20(5, Advantage.DISADVANTAGE, FixedRng(3, 15)).total == 8
    assert roll_d20(-2, Advantage.NONE, FixedRng(10)).total == 8


@pytest.mark.parametrize("bad", ["", "abc", "2d7", "0d6", "101d6", "2d6kh3", "d20++1", "2d6 + x"])
def test_invalid_expressions(bad):
    with pytest.raises(ValueError):
        roll(bad)


def test_results_stay_in_range_with_real_rng():
    for _ in range(500):
        assert 1 <= roll("d20").total <= 20
    rng = random.Random(1)
    assert all(1 <= roll("d100", rng).total <= 100 for _ in range(200))
