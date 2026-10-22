from routeiq.domain.geo import LatLon


def decode(encoded: str, precision: int = 6) -> list[LatLon]:
    """Decode a Google encoded polyline (OSRM `polyline6` uses precision 6)."""
    factor = 10**precision
    points: list[LatLon] = []
    index = lat = lon = 0
    length = len(encoded)
    while index < length:
        deltas = []
        for _ in range(2):
            shift = result = 0
            while True:
                byte = ord(encoded[index]) - 63
                index += 1
                result |= (byte & 0x1F) << shift
                shift += 5
                if byte < 0x20:
                    break
            deltas.append(~(result >> 1) if result & 1 else result >> 1)
        lat += deltas[0]
        lon += deltas[1]
        points.append(LatLon(lat / factor, lon / factor))
    return points
