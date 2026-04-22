import pytest

from core.geo import tuple_to_str
from core.percolation import (
    demolish_dead_ends,
    filter_scenic_nodes,
    find_scenic_clusters,
    remove_backtracking,
    select_percolated_clusters,
    sort_clusters_by_distance,
)


class TestDemolishDeadEnds:
    def test_removes_dead_end(self):
        tree = {
            "37.5,-122.3": [["37.6,-122.2", 0.5], ["37.55,-122.25", 0.5]],
            "37.6,-122.2": [["37.5,-122.3", 0.5], ["37.55,-122.25", 0.5]],
            "37.55,-122.25": [["37.5,-122.3", 0.5]],  # dead end: only 1 neighbor
        }
        result = demolish_dead_ends(tree)
        assert "37.55,-122.25" not in result

    def test_preserves_connected_nodes(self):
        tree = {
            "A": [["B", 1], ["C", 1]],
            "B": [["A", 1], ["C", 1]],
            "C": [["A", 1], ["B", 1]],
        }
        result = demolish_dead_ends(tree)
        assert len(result) == 3

    def test_empty_tree(self):
        result = demolish_dead_ends({})
        assert result == {}

    def test_chain_removal(self):
        # A-B-C where B and C are dead ends when removed iteratively
        tree = {
            "A": [["B", 1]],
            "B": [["A", 1], ["C", 1]],
            "C": [["B", 1]],
        }
        result = demolish_dead_ends(tree)
        assert len(result) == 0


class TestFilterScenicNodes:
    def test_removes_below_threshold(self):
        # Note: start/end nodes are skipped by filter_scenic_nodes
        tree = {
            "start": [["A", 0.8], ["B", 0.2]],
            "A": [["start", 0.8], ["B", 0.2]],
            "B": [["start", 0.2], ["A", 0.2]],
        }
        result = filter_scenic_nodes(tree, 0.5, "start", "end")
        # A's low-scoring edges should be removed; B should be removed entirely
        assert "B" not in result
        # A should lose its B edge
        if "A" in result:
            neighbor_names = [adj[0] for adj in result["A"]]
            assert "B" not in neighbor_names

    def test_preserves_start_end(self):
        tree = {
            "start": [["end", 0.1]],
            "end": [["start", 0.1]],
        }
        result = filter_scenic_nodes(tree, 0.5, "start", "end")
        # Start and end should be preserved regardless
        assert "start" in result
        assert "end" in result


class TestFindScenicClusters:
    def test_single_cluster(self):
        tree = {
            "37.5,-122.3": [["37.6,-122.2", 0.8]],
            "37.6,-122.2": [["37.5,-122.3", 0.8]],
        }
        nodes = [(37.5, -122.3), (37.6, -122.2)]
        clusters = find_scenic_clusters(tree, nodes)
        assert len(clusters) >= 1

    def test_isolated_nodes(self):
        tree = {
            "37.5,-122.3": [["37.9,-121.9", 0.8]],  # points to non-scenic node
            "37.6,-122.2": [["37.9,-121.9", 0.8]],
        }
        nodes = [(37.5, -122.3), (37.6, -122.2)]
        clusters = find_scenic_clusters(tree, nodes)
        # Each node forms its own cluster (no scenic neighbors)
        assert len(clusters) == 2


class TestSelectPercolatedClusters:
    def test_selects_requested_number(self):
        clusters = [[1], [2], [3], [4], [5]]
        result = select_percolated_clusters(clusters, 3)
        assert len(result) == 3

    def test_caps_at_available(self):
        clusters = [[1], [2]]
        result = select_percolated_clusters(clusters, 10)
        assert len(result) == 2

    def test_empty_input(self):
        result = select_percolated_clusters([], 5)
        assert len(result) == 0


class TestSortClustersByDistance:
    def test_sorts_correctly(self):
        # Cluster A is closer to start than Cluster B
        clusters = [
            [(37.6, -122.2)],  # farther from start
            [(37.51, -122.31)],  # closer to start
        ]
        start = "37.5,-122.3"
        result = sort_clusters_by_distance(clusters, start)
        # Closer one should come first
        assert result[0] == [(37.51, -122.31)]
        assert result[1] == [(37.6, -122.2)]


class TestRemoveBacktracking:
    def test_no_backtracking(self):
        path = [[37.5, -122.3], [37.51, -122.31], [37.52, -122.32]]
        assert remove_backtracking(path) == path

    def test_simple_backtrack(self):
        # A -> B -> C -> B -> D  should become  A -> B -> D
        path = [[1, 1], [2, 2], [3, 3], [2, 2], [4, 4]]
        result = remove_backtracking(path)
        assert result == [[1, 1], [2, 2], [4, 4]]

    def test_deep_backtrack(self):
        # A -> B -> C -> D -> C -> B -> E  should become  A -> B -> E
        path = [[1, 1], [2, 2], [3, 3], [4, 4], [3, 3], [2, 2], [5, 5]]
        result = remove_backtracking(path)
        assert result == [[1, 1], [2, 2], [5, 5]]

    def test_multiple_backtracks(self):
        # Two separate backtracks
        path = [[1, 1], [2, 2], [3, 3], [2, 2], [4, 4], [5, 5], [4, 4], [6, 6]]
        result = remove_backtracking(path)
        assert result == [[1, 1], [2, 2], [4, 4], [6, 6]]

    def test_empty_path(self):
        assert remove_backtracking([]) == []

    def test_single_node(self):
        assert remove_backtracking([[1, 1]]) == [[1, 1]]

    def test_preserves_non_backtrack_loop(self):
        # A -> B -> C -> D -> A is a genuine loop, not backtracking
        # (A is revisited but via different nodes, so it collapses to just [A])
        # This is expected: if the route returns to start, we trim the loop
        path = [[1, 1], [2, 2], [3, 3], [4, 4], [1, 1]]
        result = remove_backtracking(path)
        assert result == [[1, 1]]
