import math
import pytest

from core.geo import (
    R,
    str_to_tuple,
    tuple_to_str,
    haversine_from_angle,
    haversine_from_coords,
    distance,
    midpoint,
    find_closest_node,
)


class TestStrToTuple:
    def test_basic(self):
        assert str_to_tuple("37.5,-122.3") == (37.5, -122.3)

    def test_integers(self):
        assert str_to_tuple("0,0") == (0.0, 0.0)

    def test_high_precision(self):
        result = str_to_tuple("37.538288,-122.308576")
        assert result == (37.538288, -122.308576)

    def test_negative_values(self):
        assert str_to_tuple("-33.8688,151.2093") == (-33.8688, 151.2093)


class TestTupleToStr:
    def test_basic(self):
        assert tuple_to_str((37.5, -122.3)) == "37.5,-122.3"

    def test_roundtrip(self):
        original = "37.538288,-122.308576"
        assert tuple_to_str(str_to_tuple(original)) == original

    def test_zero(self):
        assert tuple_to_str((0.0, 0.0)) == "0.0,0.0"


class TestHaversineFromAngle:
    def test_zero(self):
        assert haversine_from_angle(0) == 0.0

    def test_pi(self):
        assert haversine_from_angle(math.pi) == pytest.approx(1.0)

    def test_half_pi(self):
        assert haversine_from_angle(math.pi / 2) == pytest.approx(0.5)


class TestHaversineFromCoords:
    def test_same_point(self):
        assert haversine_from_coords(37.5, 37.5, -122.3, -122.3) == 0.0

    def test_symmetric(self):
        h1 = haversine_from_coords(37.5, 38.0, -122.3, -122.0)
        h2 = haversine_from_coords(38.0, 37.5, -122.0, -122.3)
        assert h1 == pytest.approx(h2)


class TestDistance:
    def test_same_point(self):
        assert distance("37.5,-122.3", "37.5,-122.3") == 0.0

    def test_symmetric(self):
        d1 = distance("37.5,-122.3", "37.6,-122.2")
        d2 = distance("37.6,-122.2", "37.5,-122.3")
        assert d1 == pytest.approx(d2)

    def test_known_distance(self):
        # San Francisco to San Jose is roughly 42 miles
        sf = "37.7749,-122.4194"
        sj = "37.3382,-121.8863"
        d = distance(sf, sj)
        assert 35 < d < 50

    def test_short_distance(self):
        # Two nearby points in San Mateo County
        d = distance("37.538288,-122.308576", "37.539,-122.309")
        assert 0 < d < 1  # Less than 1 mile

    def test_antipodal_points(self):
        # Roughly opposite sides of earth should be ~12,400 miles
        d = distance("0,0", "0,180")
        assert 12000 < d < 13000

    def test_positive_always(self):
        d = distance("37.5,-122.3", "37.6,-122.2")
        assert d > 0


class TestMidpoint:
    def test_same_point(self):
        result = midpoint("37.5,-122.3", "37.5,-122.3")
        lat, lon = str_to_tuple(result)
        assert lat == pytest.approx(37.5, abs=0.001)
        assert lon == pytest.approx(-122.3, abs=0.001)

    def test_midpoint_is_between(self):
        p1 = "37.5,-122.3"
        p2 = "37.6,-122.2"
        mid = midpoint(p1, p2)
        d_total = distance(p1, p2)
        d1 = distance(p1, mid)
        d2 = distance(mid, p2)
        # Midpoint should be roughly equidistant
        assert d1 == pytest.approx(d2, rel=0.01)
        # And sum should equal total
        assert d1 + d2 == pytest.approx(d_total, rel=0.01)

    def test_equator_midpoint(self):
        mid = midpoint("0,0", "0,10")
        lat, lon = str_to_tuple(mid)
        assert lat == pytest.approx(0.0, abs=0.001)
        assert lon == pytest.approx(5.0, abs=0.001)


class TestFindClosestNode:
    def test_exact_match(self):
        nodes = ["37.5,-122.3", "37.6,-122.2", "37.7,-122.1"]
        assert find_closest_node("37.5,-122.3", nodes) == "37.5,-122.3"

    def test_nearest(self):
        nodes = ["37.5,-122.3", "37.6,-122.2", "38.0,-121.0"]
        result = find_closest_node("37.55,-122.25", nodes)
        # Should pick one of the closer two, not the far one
        assert result in ("37.5,-122.3", "37.6,-122.2")

    def test_single_node(self):
        nodes = ["37.5,-122.3"]
        assert find_closest_node("0,0", nodes) == "37.5,-122.3"


class TestConstants:
    def test_earth_radius(self):
        # Earth radius in miles should be ~3959
        assert 3950 < R < 3970
