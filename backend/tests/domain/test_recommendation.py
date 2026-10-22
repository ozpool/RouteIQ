from routeiq.domain.recommendation import recommend
from tests.factories import route


def test_fewest_severe_miles_beats_faster_route() -> None:
    fast_but_stormy = route("a", 5.0, severe=12.5)
    slow_but_safe = route("b", 7.5, high=40)
    result = recommend([fast_but_stormy, slow_but_safe])
    assert result.route_id == "b"
    assert result.reason == "Fewest Severe miles: 0.0 mi vs 12.5 mi on Route A."


def test_no_travel_miles_rank_before_severe() -> None:
    result = recommend([route("a", 5, no_travel=5), route("b", 6, severe=80)])
    assert result.route_id == "b"
    assert result.warnings == ("The recommended route still has 80.0 mi of Severe risk.",)


def test_ties_fall_through_in_order_and_reason_names_the_ties() -> None:
    a = route("a", 5, severe=10, high=20, average=0.9)
    b = route("b", 6, severe=10, high=20, average=0.7)
    c = route("c", 4, severe=10, high=30, average=0.1)
    result = recommend([a, b, c])
    assert result.ranking == ("b", "a", "c")
    assert result.reason == (
        "Tied on Severe miles, High miles. Lowest average risk: 0.70 vs 0.90 on Route A."
    )


def test_float_noise_does_not_decide() -> None:
    a = route("a", 5, high=10.0000001)
    b = route("b", 6, high=10.0)
    assert recommend([a, b]).route_id == "a"


def test_travel_time_is_the_last_tie_breaker() -> None:
    result = recommend([route("a", 6), route("b", 5)])
    assert result.route_id == "b"
    assert result.reason.endswith("Shortest travel time: 5h 00m vs 6h 00m on Route A.")
    assert result.warnings == ()


def test_all_routes_no_travel_warns() -> None:
    result = recommend([route("a", 5, no_travel=3), route("b", 5, no_travel=9)])
    assert result.route_id == "a"
    assert "Every option crosses No Travel" in result.warnings[0]


def test_single_route() -> None:
    result = recommend([route("a", 5)])
    assert result.ranking == ("a",)
    assert result.reason == "Only one route option is available."
