import pytest
import os
import json

from core.directions import (
    compute_bearing,
    classify_turn,
    detect_turns,
    generate_google_maps_url,
    generate_street_view_urls,
)


class TestComputeBearing:
    def test_north(self):
        b = compute_bearing(37.0, -122.0, 38.0, -122.0)
        assert abs(b - 0) < 2  # ~0 degrees

    def test_east(self):
        b = compute_bearing(37.0, -122.0, 37.0, -121.0)
        assert abs(b - 90) < 5

    def test_south(self):
        b = compute_bearing(38.0, -122.0, 37.0, -122.0)
        assert abs(b - 180) < 2

    def test_west(self):
        b = compute_bearing(37.0, -121.0, 37.0, -122.0)
        assert abs(b - 270) < 5

    def test_range_0_360(self):
        b = compute_bearing(37.0, -122.0, 37.5, -121.5)
        assert 0 <= b < 360


class TestClassifyTurn:
    def test_straight(self):
        assert classify_turn(5) == "Continue straight"
        assert classify_turn(-10) == "Continue straight"

    def test_bear_right(self):
        assert classify_turn(30) == "Bear right"

    def test_bear_left(self):
        assert classify_turn(-30) == "Bear left"

    def test_turn_right(self):
        assert classify_turn(90) == "Turn right"

    def test_turn_left(self):
        assert classify_turn(-90) == "Turn left"

    def test_sharp_right(self):
        assert classify_turn(150) == "Sharp right"

    def test_sharp_left(self):
        assert classify_turn(-150) == "Sharp left"

    def test_uturn(self):
        assert classify_turn(175) == "U-turn"
        assert classify_turn(-175) == "U-turn"


class TestDetectTurns:
    def test_empty(self):
        assert detect_turns([]) == []

    def test_same_road_no_turns(self):
        coords = [
            {"lat": 37.5, "lon": -122.3, "road_name": "Main St", "mtfcc": "S1400", "distance_to_road": 0.0},
            {"lat": 37.501, "lon": -122.301, "road_name": "Main St", "mtfcc": "S1400", "distance_to_road": 0.0},
            {"lat": 37.502, "lon": -122.302, "road_name": "Main St", "mtfcc": "S1400", "distance_to_road": 0.0},
        ]
        dirs = detect_turns(coords)
        actions = [d["action"] for d in dirs]
        assert actions[0] == "Start"
        assert actions[-1] == "Arrive"
        # No turns between Start and Arrive
        assert all(a in ("Start", "Arrive") for a in actions)

    def test_one_turn(self):
        coords = [
            {"lat": 37.5, "lon": -122.3, "road_name": "Main St", "mtfcc": "S1400", "distance_to_road": 0.0},
            {"lat": 37.501, "lon": -122.301, "road_name": "Main St", "mtfcc": "S1400", "distance_to_road": 0.0},
            {"lat": 37.502, "lon": -122.302, "road_name": "Oak Ave", "mtfcc": "S1400", "distance_to_road": 0.0},
            {"lat": 37.503, "lon": -122.303, "road_name": "Oak Ave", "mtfcc": "S1400", "distance_to_road": 0.0},
        ]
        dirs = detect_turns(coords)
        actions = [d["action"] for d in dirs]
        assert actions[0] == "Start"
        assert actions[-1] == "Arrive"
        # Should have exactly 1 turn action between Start and Arrive
        turn_actions = [a for a in actions if a not in ("Start", "Arrive")]
        assert len(turn_actions) == 1
        assert dirs[1]["road"] == "Oak Ave"

    def test_cumulative_distance_increases(self):
        coords = [
            {"lat": 37.5, "lon": -122.3, "road_name": "A St", "mtfcc": "S1400", "distance_to_road": 0.0},
            {"lat": 37.51, "lon": -122.31, "road_name": "B St", "mtfcc": "S1400", "distance_to_road": 0.0},
            {"lat": 37.52, "lon": -122.32, "road_name": "C St", "mtfcc": "S1400", "distance_to_road": 0.0},
        ]
        dirs = detect_turns(coords)
        cumulative = [d["cumulative_mi"] for d in dirs]
        assert cumulative == sorted(cumulative)


class TestGoogleMapsUrl:
    def test_format(self):
        coords = [(37.5, -122.3), (37.51, -122.31), (37.52, -122.32)]
        dirs = [
            {"action": "Start", "road": "A", "coord": coords[0], "bearing": 0},
            {"action": "Arrive", "road": "A", "coord": coords[-1], "bearing": 0},
        ]
        url = generate_google_maps_url(coords, dirs)
        assert url.startswith("https://www.google.com/maps/dir/")
        assert "37.5,-122.3" in url
        assert "37.52,-122.32" in url

    def test_max_25_waypoints(self):
        # Create 50 coords with 30 "turns"
        coords = [(37.5 + i * 0.001, -122.3 + i * 0.001) for i in range(50)]
        dirs = [{"action": "Start", "road": "A", "coord": coords[0], "bearing": 0}]
        for i in range(1, 30):
            dirs.append({"action": "Turn right", "road": f"Rd {i}", "coord": coords[i], "bearing": 90.0})
        dirs.append({"action": "Arrive", "road": "Z", "coord": coords[-1], "bearing": 0})

        url = generate_google_maps_url(coords, dirs)
        # Count waypoints in URL (separated by /)
        parts = url.replace("https://www.google.com/maps/dir/", "").split("/")
        assert len(parts) <= 25


class TestStreetViewUrls:
    def test_generates_urls(self):
        dirs = [
            {"action": "Start", "road": "Main St", "coord": (37.5, -122.3), "bearing": 45.0},
            {"action": "Turn right", "road": "Oak Ave", "coord": (37.51, -122.31), "bearing": 135.0},
        ]
        urls = generate_street_view_urls(dirs)
        assert len(urls) == 2
        assert "37.5,-122.3" in urls[0]["url"]
        assert "45.0h" in urls[0]["url"]
