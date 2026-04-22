from math import radians, degrees, pi, cos, sin, asin, atan2, sqrt

R = 3958.899  # Radius of earth in miles


def str_to_tuple(tmp: str) -> tuple:
    """'lat,lon' -> (lat, lon)"""
    return tuple(float(x) for x in tmp.split(","))


def tuple_to_str(tmp: tuple) -> str:
    """(lat, lon) -> 'lat,lon'"""
    return f"{tmp[0]},{tmp[1]}"


def haversine_from_angle(theta: float) -> float:
    return 0.5 * (1 - cos(theta))


def haversine_from_coords(lat1: float, lat2: float, lon1: float, lon2: float) -> float:
    return sqrt(
        haversine_from_angle((lat2 - lat1) * pi / 180)
        + cos(lat1 * pi / 180)
        * cos(lat2 * pi / 180)
        * haversine_from_angle((lon2 - lon1) * pi / 180)
    )


def distance(latlon1: str, latlon2: str) -> float:
    """Haversine distance in miles between two 'lat,lon' strings."""
    lat1, lon1 = latlon1.split(",")
    lat2, lon2 = latlon2.split(",")
    lat1, lon1, lat2, lon2 = float(lat1), float(lon1), float(lat2), float(lon2)
    a = haversine_from_coords(lat1, lat2, lon1, lon2)
    return 2 * R * asin(a)


def midpoint(latlon1: str, latlon2: str) -> str:
    """Geographic midpoint between two 'lat,lon' strings."""
    lat1, lon1 = (float(x) for x in latlon1.split(","))
    lat2, lon2 = (float(x) for x in latlon2.split(","))
    lat1, lon1, lat2, lon2 = map(radians, (lat1, lon1, lat2, lon2))

    bx = cos(lat2) * cos(lon2 - lon1)
    by = cos(lat2) * sin(lon2 - lon1)

    lat_m = atan2(sin(lat1) + sin(lat2), sqrt((cos(lat1) + bx) ** 2 + by ** 2))
    lon_m = lon1 + atan2(by, cos(lat1) + bx)

    return tuple_to_str((degrees(lat_m), degrees(lon_m)))


def find_closest_node(latlon: str, nodes: list) -> str:
    """Find the node in `nodes` closest to `latlon`."""
    return min(nodes, key=lambda node: distance(latlon, node))
