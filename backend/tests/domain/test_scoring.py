import pytest

from routeiq.domain.eta import EtaProfile
from routeiq.domain.models import RiskLevel, Weather
from routeiq.domain.scoring import summarize
from tests.factories import CALM, checkpoint, straight_candidate

SEVERE_RAIN = Weather(wind_mph=5, gust_mph=None, rain_in_hr=0.7, snow_in_hr=0)
HIGH_WIND = Weather(wind_mph=40, gust_mph=None, rain_in_hr=0, snow_in_hr=0)


def test_each_checkpoint_covers_half_way_to_its_neighbours() -> None:
    profile = EtaProfile(straight_candidate(miles=75, mph=60, segments=3), max_speed_mph=65)
    checkpoints = [
        checkpoint(0, 0, CALM, path_index=0),
        checkpoint(1, 25, SEVERE_RAIN, path_index=1),
        checkpoint(2, 50, CALM, path_index=2),
        checkpoint(3, 75, HIGH_WIND, path_index=2),
    ]
    summary = summarize(checkpoints, profile)

    assert [(s.start_mile, s.end_mile, s.level) for s in summary.segments] == [
        (0, 12.5, RiskLevel.LOW),
        (12.5, 37.5, RiskLevel.SEVERE),
        (37.5, 62.5, RiskLevel.LOW),
        (62.5, 75, RiskLevel.HIGH),
    ]
    assert summary.miles_by_level[RiskLevel.SEVERE] == pytest.approx(25)
    assert summary.miles_by_level[RiskLevel.HIGH] == pytest.approx(12.5)
    assert summary.miles_by_level[RiskLevel.LOW] == pytest.approx(37.5)
    assert summary.average_risk == pytest.approx((3 * 25 + 2 * 12.5) / 75)
    assert summary.exposure == pytest.approx(3 * 25 + 2 * 12.5)
    assert summary.max_level == RiskLevel.SEVERE


def test_alternating_samples_count_half_the_miles() -> None:
    profile = EtaProfile(straight_candidate(miles=100, mph=60, segments=4), max_speed_mph=65)
    weathers = [CALM, SEVERE_RAIN, CALM, SEVERE_RAIN, CALM]
    checkpoints = [checkpoint(i, i * 25, w, path_index=min(i, 3)) for i, w in enumerate(weathers)]
    assert summarize(checkpoints, profile).miles_by_level[RiskLevel.SEVERE] == pytest.approx(50)


@pytest.mark.parametrize("interval", [10, 25, 50])
def test_storm_miles_stay_within_one_interval_of_the_truth(interval: int) -> None:
    # Severe rain from mile 100 to mile 200 of a 300 mi route.
    profile = EtaProfile(straight_candidate(miles=300, mph=60, segments=30), max_speed_mph=65)
    checkpoints = [
        checkpoint(
            i, mile, SEVERE_RAIN if 100 <= mile <= 200 else CALM, path_index=min(mile // 10, 29)
        )
        for i, mile in enumerate(range(0, 301, interval))
    ]
    severe = summarize(checkpoints, profile).miles_by_level[RiskLevel.SEVERE]
    assert abs(severe - 100) <= interval


def test_segment_geometry_follows_the_route_and_meets_at_midpoints() -> None:
    profile = EtaProfile(straight_candidate(miles=40, mph=60, segments=4), max_speed_mph=65)
    start, end = checkpoint(0, 0, CALM, 0), checkpoint(1, 40, CALM, 3)
    first, second = summarize([start, end], profile).segments
    assert first.points[0] == profile.locate(0)[0]
    assert first.points[-1] == second.points[0] == profile.locate(20)[0]
    assert second.points[-1] == profile.locate(40)[0]
