"""Dijkstra-based multi-modal route planner."""

from __future__ import annotations

import heapq
from uuid import UUID

from .route_graph import RouteGraph

# Path node tuple: (node_id, mode, carrier_id, duration_h, cost_usd, carbon_kg)
PathNode = tuple[UUID, str, UUID, float, float, float]


class MultiModalPlanner:
    """Find top-N shortest paths using Dijkstra over a RouteGraph."""

    def find_routes(
        self,
        graph: RouteGraph,
        origin: UUID,
        destination: UUID,
        top_n: int = 5,
    ) -> list[list[PathNode]]:
        """Return up to top_n paths as lists of PathNode tuples."""
        # Yen's k-shortest paths (simplified): run Dijkstra repeatedly
        # collecting distinct paths.
        results: list[list[PathNode]] = []
        # heap: (cost, path_so_far)
        heap: list[tuple[float, list[PathNode]]] = [(0.0, [])]
        visited_paths: set[tuple[UUID, ...]] = set()

        while heap and len(results) < top_n:
            cost, path = heapq.heappop(heap)
            current = path[-1][0] if path else origin

            if current == destination and path:
                key = tuple(p[0] for p in path)
                if key not in visited_paths:
                    visited_paths.add(key)
                    results.append(path)
                continue

            for neighbor, weight, mode, carrier_id, duration_h, cost_usd, carbon_kg in graph.get_neighbors(current):
                new_path = path + [(neighbor, mode, carrier_id, duration_h, cost_usd, carbon_kg)]
                node_seq = tuple(p[0] for p in new_path)
                # Avoid cycles
                if len(set(node_seq)) == len(node_seq):
                    heapq.heappush(heap, (cost + weight, new_path))

        return results
