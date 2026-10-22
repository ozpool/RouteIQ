from datetime import timedelta

import pytest

from routeiq.domain.checkpoints import checkpoint_miles, place_checkpoints
from routeiq.domain.eta import EtaProfile
from tests.factories import DEPARTURE, straight_candidate


def test_speed_cap_slows_car_profile_durations() -> None:
    profile = EtaProfile(straight_candidate(miles=130, mph=78), max_speed_mph=65)
    assert profile.total_miles == pytest.approx(130)
    assert profile.total_seconds == pytest.approx(2 * 3600)


def test_slower_provider_durations_are_kept() -> None:
    profile = EtaProfile(straight_candidate(miles=100, mph=50), max_speed_mph=65)
    assert profile.total_seconds == pytest.approx(2 * 3600)


def test_locate_interpolates_inside_a_segment() -> None:
    profile = EtaProfile(straight_candidate(miles=100, mph=50, segments=4), max_speed_mph=65)
    point, seconds, path_index = profile.locate(37.5)
    assert path_index == 1
    assert seconds == pytest.approx(37.5 / 50 * 3600)
    start, end = profile.points[1], profile.points[2]
    assert start.lon < point.lon < end.lon


@pytest.mark.parametrize(
    ("total", "interval", "expected"),
    [
        (100, 25, [0, 25, 50, 75, 100]),
        (60, 25, [0, 25, 50, 60]),
        (50.6, 25, [0, 25, 50.6]),
        (8, 10, [0, 8]),
    ],
)
def test_checkpoint_miles(total: float, interval: int, expected: list[float]) -> None:
    assert checkpoint_miles(total, interval) == pytest.approx(expected)


def test_checkpoint_eta_follows_truck_time() -> None:
    profile = EtaProfile(straight_candidate(miles=120, mph=60), max_speed_mph=65)
    placements = place_checkpoints(profile, 50, DEPARTURE)
    assert [p.mile for p in placements] == pytest.approx([0, 50, 100, 120])
    assert placements[1].eta == DEPARTURE + timedelta(minutes=50)
    assert placements[-1].eta == DEPARTURE + timedelta(hours=2)
    assert [p.index for p in placements] == [0, 1, 2, 3]
