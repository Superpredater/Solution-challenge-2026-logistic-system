"""In-memory weighted directed graph for multi-modal routing."""

from __future__ import annotations

import copy
from uuid import UUID

# Edge tuple: (neighbor_id, weight, mode, carrier_id, duration_h, cost_usd, carbon_kg)
EdgeTuple = tuple[UUID, float, str, UUID, float, float, float]


class RouteGraph:
    """Adjacency-list graph of transit nodes and transport links."""

    def __init__(self) -> None:
        self._adj: dict[UUID, list[EdgeTuple]] = {}
        self._disrupted: set[UUID] = set()

    # ------------------------------------------------------------------
    # Mutation helpers
    # ------------------------------------------------------------------

    def add_edge(
        self,
        origin: UUID,
        neighbor: UUID,
        weight: float,
        mode: str,
        carrier_id: UUID,
        duration_h: float,
        cost_usd: float,
        carbon_kg: float,
    ) -> None:
        self._adj.setdefault(origin, [])
        self._adj.setdefault(neighbor, [])
        self._adj[origin].append(
            (neighbor, weight, mode, carrier_id, duration_h, cost_usd, carbon_kg)
        )

    def remove_edges_for_node(self, node_id: UUID) -> None:
        """Remove all outgoing edges from node_id and incoming edges to node_id."""
        self._adj.pop(node_id, None)
        for edges in self._adj.values():
            edges[:] = [e for e in edges if e[0] != node_id]

    def get_neighbors(self, node_id: UUID) -> list[EdgeTuple]:
        return list(self._adj.get(node_id, []))

    # ------------------------------------------------------------------
    # State-driven updates
    # ------------------------------------------------------------------

    def update_from_war_state(
        self,
        region_id: UUID,
        war_state: str,
        node_ids: list[UUID],
    ) -> None:
        """Remove edges for nodes in Restricted regions."""
        if war_state == "Restricted":
            for node_id in node_ids:
                self.remove_edges_for_node(node_id)

    def update_from_disruption(self, node_ids: list[UUID]) -> None:
        """Mark nodes as disrupted and remove their edges."""
        for node_id in node_ids:
            self._disrupted.add(node_id)
            self.remove_edges_for_node(node_id)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def nodes(self) -> set[UUID]:
        return set(self._adj.keys())

    def copy(self) -> "RouteGraph":
        g = RouteGraph()
        g._adj = copy.deepcopy(self._adj)
        g._disrupted = set(self._disrupted)
        return g
