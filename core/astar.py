import heapq

from core.geo import distance


def astar_search(start: str, end: str, tree: dict, all_nodes=None,
                 max_iterations: int = 500_000) -> list:
    """A* search from start to end using the given adjacency tree.

    Args:
        start: 'lat,lon' string for start node
        end: 'lat,lon' string for end node
        tree: adjacency dict {node: [[adjacent_node, cost], ...]}
        all_nodes: unused, kept for API compatibility
        max_iterations: safety limit to prevent infinite loops

    Returns:
        List of 'lat,lon' strings representing the path, or empty list if
        no path is found.
    """
    if start == end:
        return [start]

    if start not in tree:
        raise ValueError(f"Start node {start} not in graph")

    # Lazy heuristic: only compute distance when we actually visit a node
    h_cache = {}

    def h(node):
        if node not in h_cache:
            h_cache[node] = distance(node, end)
        return h_cache[node]

    # g-cost: best known cost to reach each node
    g = {start: 0.0}

    # Parent pointers for path reconstruction
    parent = {start: None}

    # Min-heap of (f_value, tiebreaker, node)
    # Tiebreaker ensures stable ordering when f-values are equal
    counter = 0
    open_heap = [(h(start), counter, start)]

    # Set of fully processed nodes
    closed = set()

    iterations = 0
    while open_heap:
        f_val, _, node = heapq.heappop(open_heap)

        if node in closed:
            continue
        closed.add(node)

        if node == end:
            return _reconstruct_path(parent, end)

        for neighbor, edge_cost in tree.get(node, []):
            if neighbor in closed:
                continue

            new_g = g[node] + edge_cost

            # Only update if this is a shorter path to the neighbor
            if neighbor not in g or new_g < g[neighbor]:
                g[neighbor] = new_g
                parent[neighbor] = node
                counter += 1
                heapq.heappush(open_heap, (new_g + h(neighbor), counter, neighbor))

        iterations += 1
        if iterations >= max_iterations:
            print(f"A* hit iteration limit ({max_iterations}) searching "
                  f"{start} -> {end}. Explored {len(closed)} nodes.")
            return []

    # Open list exhausted without finding end
    print(f"A* found no path from {start} to {end} "
          f"(explored {len(closed)} nodes)")
    return []


def _reconstruct_path(parent: dict, end: str) -> list:
    """Walk parent pointers back from end to start."""
    path = []
    node = end
    while node is not None:
        path.append(node)
        node = parent[node]
    path.reverse()
    return path
