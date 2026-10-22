from datetime import datetime, timedelta

from routeiq.domain.eta import EtaProfile
from routeiq.domain.models import CheckpointPlacement

ALLOWED_INTERVALS_MI = (10, 25, 50)

# A regular checkpoint this close to the destination adds no information, only a stub segment.
_MIN_FINAL_SEGMENT_MI = 1.0


def checkpoint_miles(total_miles: float, interval_mi: float) -> list[float]:
    miles = [0.0]
    mile = float(interval_mi)
    while mile < total_miles - _MIN_FINAL_SEGMENT_MI:
        miles.append(mile)
        mile += interval_mi
    miles.append(total_miles)
    return miles


def place_checkpoints(
    profile: EtaProfile, interval_mi: float, departure: datetime
) -> tuple[CheckpointPlacement, ...]:
    placements = []
    for index, mile in enumerate(checkpoint_miles(profile.total_miles, interval_mi)):
        point, seconds, path_index = profile.locate(mile)
        placements.append(
            CheckpointPlacement(
                index=index,
                mile=mile,
                point=point,
                eta=departure + timedelta(seconds=seconds),
                path_index=path_index,
            )
        )
    return tuple(placements)
