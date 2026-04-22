import pytest

from core.astar import astar_search


def make_simple_graph():
    """A -> B -> C -> D with costs.

    Graph:
        A --1.0-- B --1.0-- C --1.0-- D
        A --3.5-- D (direct but expensive)
    """
    return {
        "A": [["B", 1.0], ["D", 3.5]],
        "B": [["A", 1.0], ["C", 1.0]],
        "C": [["B", 1.0], ["D", 1.0]],
        "D": [["C", 1.0], ["A", 3.5]],
    }


def make_branching_graph():
    """Graph with two paths:
        A -> B -> D (cost 2)
        A -> C -> D (cost 5)
    """
    return {
        "A": [["B", 1.0], ["C", 3.0]],
        "B": [["A", 1.0], ["D", 1.0]],
        "C": [["A", 3.0], ["D", 2.0]],
        "D": [["B", 1.0], ["C", 2.0]],
    }


# Use zero heuristic to test without geographic coordinates
@pytest.fixture(autouse=True)
def mock_distance(monkeypatch):
    """Replace geo.distance with a zero heuristic for non-geographic tests."""
    def fake_distance(a, b):
        return 0.0
    monkeypatch.setattr("core.astar.distance", fake_distance)


class TestAStarSearch:
    def test_start_equals_end(self):
        graph = {"A": [["A", 0.0]]}
        result = astar_search("A", "A", graph)
        assert result == ["A"]

    def test_direct_neighbor(self):
        graph = make_simple_graph()
        result = astar_search("A", "B", graph)
        assert result[0] == "A"
        assert result[-1] == "B"

    def test_finds_path(self):
        graph = make_simple_graph()
        result = astar_search("A", "D", graph)
        assert result[0] == "A"
        assert result[-1] == "D"
        assert len(result) >= 2

    def test_optimal_path_simple(self):
        """With zero heuristic, A* degrades to Dijkstra and finds optimal path."""
        graph = make_simple_graph()
        result = astar_search("A", "D", graph)
        # Optimal is A->B->C->D (cost 3) not A->D (cost 3.5)
        assert result == ["A", "B", "C", "D"]

    def test_path_is_valid(self):
        """Every consecutive pair in the path must be adjacent in the graph."""
        graph = make_simple_graph()
        result = astar_search("A", "D", graph)
        for i in range(len(result) - 1):
            neighbors = [adj[0] for adj in graph[result[i]]]
            assert result[i + 1] in neighbors

    def test_finds_valid_path_branching(self):
        graph = make_branching_graph()
        result = astar_search("A", "D", graph)
        assert result[0] == "A"
        assert result[-1] == "D"
        for i in range(len(result) - 1):
            neighbors = [adj[0] for adj in graph[result[i]]]
            assert result[i + 1] in neighbors

    def test_optimal_path_branching(self):
        """Should find A->B->D (cost 2) not A->C->D (cost 5)."""
        graph = make_branching_graph()
        result = astar_search("A", "D", graph)
        assert result == ["A", "B", "D"]

    def test_no_path_returns_empty(self):
        graph = {
            "A": [["B", 1.0]],
            "B": [["A", 1.0]],
            "C": [],
        }
        result = astar_search("A", "C", graph)
        assert result == []

    def test_start_not_in_graph_raises(self):
        graph = {"A": [["B", 1.0]]}
        with pytest.raises(ValueError, match="not in graph"):
            astar_search("Z", "A", graph)

    def test_max_iterations_returns_empty(self):
        graph = make_simple_graph()
        result = astar_search("A", "D", graph, max_iterations=1)
        assert result == []
