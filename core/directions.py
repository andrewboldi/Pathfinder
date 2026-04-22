"""Turn-by-turn directions from route coordinates using TIGER road data."""

import os
import json
from math import radians, degrees, sin, cos, atan2

import warnings
import geopandas as gpd
from shapely.geometry import Point

from core.geo import distance, str_to_tuple
from core.config import DATA_DIR, OUTPUT_DIR

TIGER_SHAPEFILE = os.path.join(DATA_DIR, "tiger", "tl_2021_06081_roads.shp")

# MTFCC road class labels for unnamed roads
MTFCC_LABELS = {
    "S1100": "Primary Road",
    "S1200": "Secondary Road",
    "S1400": "Local Road",
    "S1500": "Vehicular Trail",
    "S1630": "Ramp",
    "S1640": "Service Drive",
    "S1710": "Walkway",
    "S1720": "Stairway",
    "S1730": "Alley",
    "S1740": "Private Road",
    "S1780": "Parking Lot Road",
}

_road_gdf_cache = None


def build_road_index(shapefile_path=None):
    """Load TIGER shapefile and build spatial index. Cached after first call."""
    global _road_gdf_cache
    if _road_gdf_cache is None:
        path = shapefile_path or TIGER_SHAPEFILE
        _road_gdf_cache = gpd.read_file(path)
        _ = _road_gdf_cache.sindex  # force spatial index build
    return _road_gdf_cache


def _road_name(row):
    """Get road name from a GeoDataFrame row, with MTFCC fallback."""
    name = row.get("FULLNAME")
    if name and str(name).strip():
        return str(name).strip()
    mtfcc = row.get("MTFCC", "")
    return MTFCC_LABELS.get(mtfcc, "Unnamed road")


def reverse_geocode_route(coords, road_gdf=None, buffer_deg=0.0005):
    """Map each (lat, lon) coordinate to the nearest TIGER road segment.

    Args:
        coords: list of (lat, lon) tuples
        road_gdf: GeoDataFrame with road data (loaded if None)
        buffer_deg: search buffer in degrees (~50m at this latitude)

    Returns:
        list of dicts with keys: lat, lon, road_name, mtfcc, distance_to_road
    """
    if road_gdf is None:
        road_gdf = build_road_index()

    results = []
    for lat, lon in coords:
        pt = Point(lon, lat)  # shapefile uses (lon, lat) order
        # Query spatial index with buffer
        candidates_idx = list(road_gdf.sindex.query(pt.buffer(buffer_deg)))
        if not candidates_idx:
            # Widen search
            candidates_idx = list(road_gdf.sindex.query(pt.buffer(buffer_deg * 4)))

        if candidates_idx:
            candidates = road_gdf.iloc[candidates_idx]
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                dists = candidates.geometry.distance(pt)
            nearest_idx = dists.idxmin()
            row = road_gdf.loc[nearest_idx]
            results.append({
                "lat": lat,
                "lon": lon,
                "road_name": _road_name(row),
                "mtfcc": row.get("MTFCC", ""),
                "distance_to_road": dists[nearest_idx],
            })
        else:
            results.append({
                "lat": lat,
                "lon": lon,
                "road_name": "Unknown road",
                "mtfcc": "",
                "distance_to_road": float("inf"),
            })
    return results


def compute_bearing(lat1, lon1, lat2, lon2):
    """Compute forward azimuth bearing in degrees (0-360) between two points."""
    lat1, lon1, lat2, lon2 = map(radians, (lat1, lon1, lat2, lon2))
    dlon = lon2 - lon1
    x = sin(dlon) * cos(lat2)
    y = cos(lat1) * sin(lat2) - sin(lat1) * cos(lat2) * cos(dlon)
    bearing = degrees(atan2(x, y))
    return (bearing + 360) % 360


def classify_turn(bearing_change):
    """Classify a bearing change (degrees) into a turn instruction.

    Positive = right, negative = left.
    """
    # Normalize to -180..180
    delta = ((bearing_change + 180) % 360) - 180

    abs_delta = abs(delta)
    if abs_delta < 15:
        return "Continue straight"
    elif abs_delta < 60:
        return "Bear right" if delta > 0 else "Bear left"
    elif abs_delta < 120:
        return "Turn right" if delta > 0 else "Turn left"
    elif abs_delta < 170:
        return "Sharp right" if delta > 0 else "Sharp left"
    else:
        return "U-turn"


def detect_turns(annotated_coords):
    """Detect turns in a route based on road name changes.

    Args:
        annotated_coords: list of dicts from reverse_geocode_route

    Returns:
        list of direction step dicts
    """
    if not annotated_coords:
        return []

    directions = []
    current_road = annotated_coords[0]["road_name"]
    segment_start_idx = 0
    cumulative_mi = 0.0

    # Start instruction
    directions.append({
        "action": "Start",
        "road": current_road,
        "distance_mi": 0.0,
        "cumulative_mi": 0.0,
        "coord": (annotated_coords[0]["lat"], annotated_coords[0]["lon"]),
        "bearing": 0.0,
    })

    for i in range(1, len(annotated_coords)):
        prev = annotated_coords[i - 1]
        curr = annotated_coords[i]

        # Accumulate distance
        seg_dist = distance(
            f"{prev['lat']},{prev['lon']}",
            f"{curr['lat']},{curr['lon']}"
        )
        cumulative_mi += seg_dist

        # Check for road name change
        if curr["road_name"] != current_road:
            # Compute bearing change at this turn
            if i >= 2:
                pp = annotated_coords[i - 2]
                bearing_in = compute_bearing(pp["lat"], pp["lon"], prev["lat"], prev["lon"])
            else:
                bearing_in = 0.0
            bearing_out = compute_bearing(prev["lat"], prev["lon"], curr["lat"], curr["lon"])
            bearing_change = bearing_out - bearing_in

            # Distance along the previous road segment
            road_dist = 0.0
            for j in range(segment_start_idx, i):
                if j + 1 < len(annotated_coords):
                    a = annotated_coords[j]
                    b = annotated_coords[j + 1] if j + 1 <= i else annotated_coords[i]
                    if j + 1 <= i - 1:
                        road_dist += distance(
                            f"{a['lat']},{a['lon']}",
                            f"{b['lat']},{b['lon']}"
                        )

            action = classify_turn(bearing_change)
            directions.append({
                "action": action,
                "road": curr["road_name"],
                "distance_mi": round(road_dist, 2),
                "cumulative_mi": round(cumulative_mi, 2),
                "coord": (curr["lat"], curr["lon"]),
                "bearing": round(bearing_out, 1),
            })

            current_road = curr["road_name"]
            segment_start_idx = i

    # Arrive instruction
    last = annotated_coords[-1]
    last_dist = 0.0
    for j in range(segment_start_idx, len(annotated_coords) - 1):
        a = annotated_coords[j]
        b = annotated_coords[j + 1]
        last_dist += distance(f"{a['lat']},{a['lon']}", f"{b['lat']},{b['lon']}")

    directions.append({
        "action": "Arrive",
        "road": current_road,
        "distance_mi": round(last_dist, 2),
        "cumulative_mi": round(cumulative_mi, 2),
        "coord": (last["lat"], last["lon"]),
        "bearing": 0.0,
    })

    return directions


# --- Output generators ---

def generate_google_maps_url(coords, directions):
    """Generate a Google Maps directions URL with up to 25 waypoints.

    Prioritizes turn points; fills remaining slots with evenly-spaced points.
    """
    # Always include start and end
    start = coords[0]
    end = coords[-1]

    # Collect turn-point indices (skip Start and Arrive)
    turn_coords = [d["coord"] for d in directions if d["action"] not in ("Start", "Arrive")]

    if len(turn_coords) > 23:
        # Keep the sharpest turns (those with biggest bearing change, i.e. not "Continue straight")
        scored = []
        for d in directions:
            if d["action"] in ("Start", "Arrive", "Continue straight"):
                continue
            # Score: sharper turns get higher priority
            score = {"Bear": 1, "Turn": 2, "Sharp": 3, "U-turn": 4}
            s = 0
            for k, v in score.items():
                if k in d["action"]:
                    s = v
            scored.append((s, d["coord"]))
        scored.sort(key=lambda x: -x[0])
        turn_coords = [c for _, c in scored[:23]]
    elif len(turn_coords) < 23:
        # Fill with evenly-spaced intermediate points
        remaining = 23 - len(turn_coords)
        turn_set = set(turn_coords)
        step = max(1, len(coords) // (remaining + 1))
        for i in range(step, len(coords) - 1, step):
            if coords[i] not in turn_set and len(turn_coords) < 23:
                turn_coords.append(coords[i])

    # Build ordered waypoint list: start, waypoints in route order, end
    waypoint_set = set(turn_coords)
    ordered_waypoints = [start]
    for c in coords[1:-1]:
        if c in waypoint_set:
            ordered_waypoints.append(c)
            waypoint_set.discard(c)
    ordered_waypoints.append(end)

    parts = [f"{lat},{lon}" for lat, lon in ordered_waypoints]
    return "https://www.google.com/maps/dir/" + "/".join(parts)


def generate_street_view_urls(directions):
    """Generate Google Street View URLs for each turn point."""
    urls = []
    for d in directions:
        lat, lon = d["coord"]
        heading = d["bearing"]
        url = (
            f"https://www.google.com/maps/@{lat},{lon},3a,75y,"
            f"{heading}h,90t/data=!3m6!1e1!3m4!1s!2e0!7i16384!8i8192"
        )
        urls.append({"action": d["action"], "road": d["road"], "url": url})
    return urls


def generate_kml(coords, directions, output_path):
    """Generate a KML file for Google Earth."""
    import simplekml

    kml = simplekml.Kml(name="Pathfinder Scenic Route")

    # Route line
    line_coords = [(lon, lat) for lat, lon in coords]  # KML uses lon,lat order
    line = kml.newlinestring(name="Scenic Route", coords=line_coords)
    line.style.linestyle.color = simplekml.Color.green
    line.style.linestyle.width = 4

    # Start marker
    start = coords[0]
    pnt = kml.newpoint(name="Start", coords=[(start[1], start[0])])
    pnt.style.iconstyle.color = simplekml.Color.green

    # Turn markers
    for d in directions:
        if d["action"] in ("Start", "Arrive"):
            continue
        lat, lon = d["coord"]
        desc = f"{d['action']} onto {d['road']} ({d['cumulative_mi']} mi)"
        kml.newpoint(name=d["action"], description=desc, coords=[(lon, lat)])

    # End marker
    end = coords[-1]
    pnt = kml.newpoint(name="Destination", coords=[(end[1], end[0])])
    pnt.style.iconstyle.color = simplekml.Color.red

    kml.save(output_path)
    return output_path


def generate_pdf(directions, maps_url, sv_urls, route_metadata, output_path):
    """Generate a PDF with turn-by-turn directions."""
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Page 1: Summary
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 15, "Pathfinder Scenic Route", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 11)
    total_mi = directions[-1]["cumulative_mi"] if directions else 0
    est_time = total_mi / 25 * 60  # minutes at 25mph
    n_turns = sum(1 for d in directions if d["action"] not in ("Start", "Arrive"))

    pdf.cell(0, 8, f"From: {route_metadata.get('start', 'N/A')}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"To: {route_metadata.get('end', 'N/A')}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Total Distance: {total_mi:.1f} miles", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Estimated Time: {est_time:.0f} minutes (at 25 mph scenic pace)", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Number of Turns: {n_turns}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "Google Maps:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 6, maps_url, new_x="LMARGIN", new_y="NEXT")

    # Page 2+: Directions
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 12, "Turn-by-Turn Directions", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    pdf.set_font("Helvetica", "", 10)
    for i, d in enumerate(directions):
        step_text = f"{i+1}. {d['action']}"
        if d["action"] == "Start":
            step_text += f" on {d['road']}"
        elif d["action"] == "Arrive":
            step_text += f" at destination on {d['road']} ({d['distance_mi']} mi)"
        else:
            step_text += f" onto {d['road']} (go {d['distance_mi']} mi, total {d['cumulative_mi']} mi)"

        pdf.multi_cell(0, 7, step_text, new_x="LMARGIN", new_y="NEXT")

    pdf.output(output_path)
    return output_path


def generate_interactive_map(coords, directions, sv_urls, output_path):
    """Generate an interactive HTML map using Folium (Leaflet.js)."""
    import folium

    center_lat = sum(c[0] for c in coords) / len(coords)
    center_lon = sum(c[1] for c in coords) / len(coords)

    m = folium.Map(location=[center_lat, center_lon], zoom_start=14)

    # Tile layers
    folium.TileLayer("OpenStreetMap", name="Street Map").add_to(m)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri", name="Satellite", overlay=False,
    ).add_to(m)
    folium.LayerControl().add_to(m)

    # Route line
    folium.PolyLine(
        locations=[(lat, lon) for lat, lon in coords],
        color="#2196F3", weight=5, opacity=0.8,
    ).add_to(m)

    # Start marker
    start = coords[0]
    folium.Marker(
        location=start, icon=folium.Icon(color="green", icon="play", prefix="fa"),
        popup=f"<b>Start</b><br>{directions[0]['road']}",
    ).add_to(m)

    # End marker
    end = coords[-1]
    folium.Marker(
        location=end, icon=folium.Icon(color="red", icon="flag-checkered", prefix="fa"),
        popup=f"<b>Destination</b><br>{directions[-1]['road']}",
    ).add_to(m)

    # Turn markers with Street View links
    sv_map = {(s["action"], s["road"]): s["url"] for s in sv_urls}
    for d in directions:
        if d["action"] in ("Start", "Arrive"):
            continue
        lat, lon = d["coord"]
        sv_url = sv_map.get((d["action"], d["road"]), "")
        popup_html = (
            f"<b>{d['action']}</b><br>"
            f"onto <b>{d['road']}</b><br>"
            f"{d['distance_mi']} mi (total {d['cumulative_mi']} mi)<br>"
            f'<a href="{sv_url}" target="_blank">Street View</a>'
        )
        icon_color = "blue"
        if "Sharp" in d["action"] or "U-turn" in d["action"]:
            icon_color = "orange"

        folium.CircleMarker(
            location=(lat, lon), radius=6, color=icon_color,
            fill=True, fill_opacity=0.8,
            popup=folium.Popup(popup_html, max_width=250),
        ).add_to(m)

    m.save(output_path)
    return output_path


def save_directions_json(directions, maps_url, sv_urls, output_path):
    """Save directions as machine-readable JSON."""
    data = {
        "google_maps_url": maps_url,
        "street_view_urls": sv_urls,
        "directions": directions,
    }
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)
    return output_path


# --- Main orchestrator ---

def generate_route_directions(final_path, start, end):
    """Generate all direction outputs for a computed route.

    Args:
        final_path: list of [lat, lon] from the percolation pipeline
        start: 'lat,lon' string
        end: 'lat,lon' string

    Returns:
        dict with keys: pdf, kml, json, maps_url
    """
    coords = [(c[0], c[1]) for c in final_path]
    if len(coords) < 2:
        print("Route too short for directions.")
        return {}

    print("Generating directions...")

    # 1. Reverse geocode
    print("  Reverse-geocoding coordinates to road names...")
    road_gdf = build_road_index()
    annotated = reverse_geocode_route(coords, road_gdf)

    # 2. Detect turns
    directions = detect_turns(annotated)
    print(f"  Found {sum(1 for d in directions if d['action'] not in ('Start', 'Arrive'))} turns")

    # 3. Google Maps URL
    maps_url = generate_google_maps_url(coords, directions)

    # 4. Street View URLs
    sv_urls = generate_street_view_urls(directions)

    # 5. Output paths
    dir_out = os.path.join(OUTPUT_DIR, "directions")
    os.makedirs(dir_out, exist_ok=True)
    base = f"{start}_{end}".replace(",", "_")

    # 6. KML
    kml_path = os.path.join(dir_out, f"{base}_route.kml")
    generate_kml(coords, directions, kml_path)
    print(f"  KML: {kml_path}")

    # 7. PDF
    pdf_path = os.path.join(dir_out, f"{base}_directions.pdf")
    metadata = {"start": start, "end": end}
    generate_pdf(directions, maps_url, sv_urls, metadata, pdf_path)
    print(f"  PDF: {pdf_path}")

    # 8. JSON
    json_path = os.path.join(dir_out, f"{base}_turns.json")
    save_directions_json(directions, maps_url, sv_urls, json_path)
    print(f"  JSON: {json_path}")

    # 9. Interactive map
    map_path = os.path.join(dir_out, f"{base}_map.html")
    generate_interactive_map(coords, directions, sv_urls, map_path)
    print(f"  Interactive map: {map_path}")

    print(f"  Google Maps: {maps_url}")

    return {"pdf": pdf_path, "kml": kml_path, "json": json_path, "map": map_path, "maps_url": maps_url}
