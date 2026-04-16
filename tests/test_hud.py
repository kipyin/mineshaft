"""HUD slot math (MC-style: 10 icons, 2 points per icon at max 20)."""

from mineshaft.ui.render import icon_states


def test_icon_states_zero() -> None:
    assert icon_states(0, 20) == ["empty"] * 10


def test_icon_states_one() -> None:
    assert icon_states(1, 20)[0] == "half"
    assert icon_states(1, 20)[1:] == ["empty"] * 9


def test_icon_states_ten() -> None:
    s = icon_states(10, 20)
    assert s[:5] == ["full"] * 5
    assert s[5:] == ["empty"] * 5


def test_icon_states_full() -> None:
    assert icon_states(20, 20) == ["full"] * 10


def test_icon_states_clamps() -> None:
    assert icon_states(25, 20) == ["full"] * 10
    assert icon_states(-3, 20) == ["empty"] * 10
