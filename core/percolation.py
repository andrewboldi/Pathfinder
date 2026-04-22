import os
import json
import statistics as stats
from random import shuffle
from math import radians, degrees, cos, sin, atan2, sqrt
from collections import defaultdict, deque

import tqdm

from core.geo import R, str_to_tuple, tuple_to_str, distance, midpoint, find_closest_node
from core.astar import astar_search
from core.config import DATA_DIR, OUTPUT_DIR


def load_adjacency_tree(basename: str, dropout: bool = False) -> dict:
    suffix = "dropout_dropout" if dropout else ""
    filename = f"{basename}{suffix}.txt"
    path = os.path.join(DATA_DIR, "adjacency_lists", filename)
    return dict(json.loads(open(path).read()))


def filter_by_ellipse(original_tree: dict, start: str, end: str,
                      eccentricity: float, total_distance: float) -> dict:
    """Filter nodes to those within an ellipse bounded by start and end."""
    endpoints_midpoint = midpoint(start, end)

    lat_start, lon_start = (float(x) for x in start.split(","))
    lat_end, lon_end = (float(x) for x in end.split(","))
    lat_mid, lon_mid = (float(x) for x in endpoints_midpoint.split(","))

    a = total_distance / 2
    b = sqrt((a ** 2) * (1 - eccentricity ** 2))
    rot = atan2(
        sin(lon_end - lon_start) * cos(lat_end),
        cos(lat_start) * sin(lat_end) - sin(lat_start) * cos(lat_end) * cos(lon_end - lon_start),
    )

    tree = {}
    theta = radians(90 - lat_mid)
    phi = radians(lon_mid)
    alpha = -rot
    c = sqrt(a ** 2 - b ** 2)
    gamma = c / R

    for item in tqdm.tqdm(original_tree.items(), desc="Finding Coordinates in Range"):
        coord = str_to_tuple(item[0])
        lat2, lon2 = coord[0], coord[1]

        f1_x = R * (cos(alpha) * sin(gamma) * cos(phi) * cos(theta) - sin(alpha) * sin(gamma) * sin(phi) + cos(gamma) * cos(phi) * sin(theta))
        f1_y = R * (cos(alpha) * sin(gamma) * sin(phi) * cos(theta) + sin(alpha) * sin(gamma) * cos(phi) + cos(gamma) * sin(phi) * sin(theta))
        f1_z = R * (cos(gamma) * cos(theta) - cos(alpha) * sin(gamma) * sin(theta))

        f2_x = R * (-cos(alpha) * sin(gamma) * cos(phi) * cos(theta) + sin(alpha) * sin(gamma) * sin(phi) + cos(gamma) * cos(phi) * sin(theta))
        f2_y = R * (-cos(alpha) * sin(gamma) * sin(phi) * cos(theta) - sin(alpha) * sin(gamma) * cos(phi) + cos(gamma) * sin(phi) * sin(theta))
        f2_z = R * (cos(gamma) * cos(theta) + cos(alpha) * sin(gamma) * sin(theta))

        f1 = (atan2(f1_y, f1_x), atan2(f1_z, sqrt(f1_x ** 2 + f1_y ** 2)))
        f2 = (atan2(f2_y, f2_x), atan2(f2_z, sqrt(f2_x ** 2 + f2_y ** 2)))

        f1 = (degrees(f1[1]), degrees(f1[0]))
        f2 = (degrees(f2[1]), degrees(f2[0]))

        d1 = distance(tuple_to_str(coord), tuple_to_str(f1))
        d2 = distance(tuple_to_str(coord), tuple_to_str(f2))

        if d1 + d2 <= 2 * a:
            tree[item[0]] = item[1]

    print(f"# of Coordinates in Range: {len(tree)}")
    return tree


def demolish_dead_ends(tree: dict) -> dict:
    """Iteratively remove dead-end nodes (nodes with <=1 neighbor).

    Uses a reverse adjacency index and queue for O(n) performance
    instead of the O(n^2) brute-force scan.
    """
    # Build reverse index: for each node, which nodes have it as a neighbor?
    reverse = defaultdict(set)
    for node, neighbors in tree.items():
        for nb, _ in neighbors:
            reverse[nb].add(node)

    # Seed queue with all current dead ends
    queue = deque()
    for node, neighbors in tree.items():
        if len(neighbors) <= 1:
            queue.append(node)

    before = len(tree)
    while queue:
        node = queue.popleft()
        if node not in tree:
            continue
        if len(tree[node]) > 1:
            continue  # no longer a dead end (was fixed by another removal)

        # Remove this node from all parents' neighbor lists
        for parent in reverse.get(node, set()):
            if parent not in tree:
                continue
            tree[parent] = [nb for nb in tree[parent] if nb[0] != node]
            if len(tree[parent]) <= 1:
                queue.append(parent)

        del tree[node]

    print(f"Removed {before - len(tree)} dead ends")
    return tree


def filter_scenic_nodes(tree: dict, critical_value: float, start: str, end: str) -> dict:
    """Remove edges below the scenicness critical value."""
    print(f"# of Regular Nodes: {len(tree)}")
    for x in tqdm.tqdm(list(tree.items()), desc="Finding Scenic Nodes"):
        if x[0] == start or x[0] == end:
            continue
        for y in x[1].copy():
            if y[1] < critical_value:
                if x[0] in tree:
                    tree[x[0]].remove(y)
                    if len(tree[x[0]]) == 0:
                        del tree[x[0]]
    print(f"# of Scenic Nodes: {len(tree)}")
    return tree


def find_scenic_clusters(tree: dict, scenic_tuple_nodes: list) -> list:
    """Find clusters of adjacent scenic nodes."""
    clusters = []
    for scenic_node in tqdm.tqdm(scenic_tuple_nodes, desc="Finding Scenic Clusters"):
        tmp = [scenic_node]
        for adjacent_scenic_node in tree[tuple_to_str(scenic_node)]:
            candidate = tuple(float(x) for x in str_to_tuple(adjacent_scenic_node[0]))
            if candidate in scenic_tuple_nodes:
                tmp.append(candidate)
        tmp.sort()
        if tmp not in clusters:
            clusters.append(tmp)
    print(f"# of Scenic Clusters: {len(clusters)}")
    return clusters


def select_percolated_clusters(clusters: list, n_clusters: int) -> list:
    """Randomly select n_clusters from the available clusters."""
    percolated = list(clusters)
    shuffle(percolated)
    shuffle(percolated)
    shuffle(percolated)
    return percolated[: min(len(percolated), n_clusters)]


def remove_backtracking(path: list, near_threshold_mi: float = 0.03) -> list:
    """Remove backtracking loops where the route revisits a node or near-node.

    Pass 1 (exact): When path goes A -> B -> C -> B -> D, detects B is
    revisited and trims to A -> B -> D.

    Pass 2 (near): When path goes A -> B -> C -> D -> A' where A' is within
    near_threshold_mi of A, trims the short detour. This catches cases where
    the route exits a side street at a slightly different point on the main road.
    """
    # Pass 1: exact node match
    seen = {}
    result = []
    for node in path:
        key = (round(node[0], 6), round(node[1], 6))
        if key in seen:
            idx = seen[key]
            removed = result[idx + 1:]
            result = result[:idx + 1]
            for r in removed:
                rkey = (round(r[0], 6), round(r[1], 6))
                if rkey in seen and seen[rkey] > idx:
                    del seen[rkey]
        else:
            seen[key] = len(result)
            result.append(node)

    # Pass 2: near-node match (short detours back to ~same spot)
    changed = True
    while changed:
        changed = False
        i = 0
        new_result = []
        while i < len(result):
            # Look ahead for a node close to result[i] (within threshold)
            found_near = -1
            for j in range(i + 3, min(i + 20, len(result))):
                d = distance(
                    f"{result[i][0]},{result[i][1]}",
                    f"{result[j][0]},{result[j][1]}"
                )
                if d < near_threshold_mi:
                    # Check that the detour path distance is short
                    detour_dist = 0.0
                    for k in range(i, j):
                        detour_dist += distance(
                            f"{result[k][0]},{result[k][1]}",
                            f"{result[k+1][0]},{result[k+1][1]}"
                        )
                    # Only trim if the detour is < 0.3 mi (short side street)
                    if detour_dist < 0.3:
                        found_near = j
                        break
            if found_near > 0:
                new_result.append(result[i])
                i = found_near  # skip the detour
                changed = True
            else:
                new_result.append(result[i])
                i += 1
        result = new_result

    return result


def sort_clusters_by_distance(clusters: list, start: str):
    """Sort clusters by distance from start."""
    if not clusters:
        return []
    dist_start = [distance(tuple_to_str(c[0]), start) for c in clusters]
    dist_start, clusters = zip(*sorted(zip(dist_start, clusters), key=lambda x: x[0]))
    return list(clusters)


def run_percolation_pipeline(start: str, end: str, eccentricity: float,
                             p: float, n_clusters: int, dropout: bool = False):
    """Full percolation-based scenic routing pipeline."""
    from datetime import datetime

    critical_value = p
    basefilename = "100vegetation"

    starttime = datetime.now()
    print("Loading Data...")
    original_tree = load_adjacency_tree(basefilename, dropout)
    endtime = datetime.now()
    print(f"Data loading took {endtime - starttime}s!\n")

    # Snap start/end to nearest nodes in the graph
    print("Finding closest start and end points to input...")
    nodes_in_scope = list(original_tree.keys())
    old_start, old_end = start, end
    start = find_closest_node(start, nodes_in_scope)
    end = find_closest_node(end, nodes_in_scope)
    print(f"Transformed starting point {old_start} -> {start}.")
    print(f"Transformed ending point {old_end} -> {end}.")

    total_distance = distance(start, end)

    # Filter to ellipse
    tree = filter_by_ellipse(original_tree, start, end, eccentricity, total_distance)

    # Remove dead ends
    tree = demolish_dead_ends(tree)

    # Filter scenic nodes
    tree = filter_scenic_nodes(tree, critical_value, start, end)

    # Build scenic node lists
    scenic_nodes = [[float(x.split(",")[0]), float(x.split(",")[1])] for x in tree.keys()]
    scenic_tuple_nodes = [tuple(x) for x in scenic_nodes]

    # Find clusters
    clusters = find_scenic_clusters(tree, scenic_tuple_nodes)

    # Select and sort clusters
    percolated_clusters = select_percolated_clusters(clusters, n_clusters)
    percolated_clusters = sort_clusters_by_distance(percolated_clusters, start)

    # Run A* between clusters using distance-weighted tree
    distance_tree = json.loads(
        open(os.path.join(DATA_DIR, "adjacency_lists",
                          f"100distance{'dropout_dropout' if dropout else ''}.txt")).read()
    )

    if not percolated_clusters:
        print("No scenic clusters found. Running direct A* from start to end.")
        path = astar_search(start, end, distance_tree)
        if not path:
            print("ERROR: No path found between start and end.")
            return []
        final_path = [list(str_to_tuple(loc)) for loc in path]
        return final_path

    # Build waypoint sequence: start -> cluster0 -> cluster1 -> ... -> end
    waypoints = [start]
    for cluster in percolated_clusters:
        waypoints.append(tuple_to_str(cluster[0]))
    waypoints.append(end)

    paths = []
    for i in range(len(waypoints) - 1):
        segment = astar_search(waypoints[i], waypoints[i + 1], distance_tree)
        if not segment:
            print(f"WARNING: No path from {waypoints[i]} to {waypoints[i+1]}, skipping cluster.")
            continue
        # Avoid duplicating the junction node between segments
        if paths and paths[-1] and segment[0] == paths[-1][-1]:
            segment = segment[1:]
        if segment:
            paths.append(segment)

    # Collect final path
    final_path = []
    os.makedirs(os.path.join(OUTPUT_DIR, "routes"), exist_ok=True)
    result_path = os.path.join(
        OUTPUT_DIR, "routes", f"{start},{end},{p},{eccentricity},{n_clusters}.txt"
    )
    with open(result_path, "w") as f:
        for path in paths:
            for location in path:
                final_path.append(list(str_to_tuple(location)))
                f.write(str(list(str_to_tuple(str(location)))) + "\n")

    if not final_path:
        print("ERROR: Could not construct any path.")
        return []

    # Remove backtracking (dead-end detours where route revisits nodes)
    before = len(final_path)
    final_path = remove_backtracking(final_path)
    removed = before - len(final_path)
    if removed:
        print(f"Removed {removed} backtracking nodes ({before} -> {len(final_path)})")

    return final_path
