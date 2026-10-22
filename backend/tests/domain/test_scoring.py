import pytest

from routeiq.domain.eta import EtaProfile
from routeiq.domain.models import RiskLevel, Weather
from routeiq.domain.scoring import summarize
from tests.factories import CALM, checkpoint, straight_candidate

SEVERE_RAIN = Weather(wind_mph=5, gust_mph=None, rain_in_hr=0.7, snow_in_hr=0)
HIGH_WIND = Weather(wind_mph=40, gust_mph=None, rain_in_hr=0, snow_in_hr=0)


def test_segment_takes_the_worse_endpoint_and_miles_add_up() -> None:
    profile = EtaProfile(straight_candidate(miles=75, mph=60, segments=3), max_speed_mph=65)
    checkpoints = [
        checkpoint(0, 0, CALM, path_index=0),
        checkpoint(1, 25, SEVERE_RAIN, path_index=1),
        checkpoint(2, 50, CALM, path_index=2),
        checkpoint(3, 75, HIGH_WIND, path_index=2),
    ]
    summary = summarize(checkpoints, profile)

    assert [s.level for s in summary.segments] == [
        RiskLevel.SEVERE,
        RiskLevel.SEVERE,
        RiskLevel.HIGH,
    ]
    assert summary.miles_by_level[RiskLevel.SEVERE] == pytest.approx(50)
    assert summary.miles_by_level[RiskLevel.HIGH] == pytest.approx(25)
    assert summary.miles_by_level[RiskLevel.LOW] == 0
    assert summary.average_risk == pytest.approx((3 * 50 + 2 * 25) / 75)
    assert summary.max_level == RiskLevel.SEVERE


def test_segment_geometry_starts_and_ends_at_checkpoints() -> None:
    profile = EtaProfile(straight_candidate(miles=40, mph=60, segments=4), max_speed_mph=65)
    start, end = checkpoint(0, 0, CALM, 0), checkpoint(1, 40, CALM, 3)
    segment = summarize([start, end], profile).segments[0]
    assert segment.points[0] == start.placement.point
    assert segment.points[-1] == end.placement.point
