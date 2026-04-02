"""Filter a RouteGraph by removing restricted/disrupted nodes."""

from __future__ import annotations

from uuid import UUID

from .route_graph import RouteGraph


class RestrictionFilter:
    """Return a copy of the graph with restricted/disrupted edges removed."""

    def filter_graph(
        self,
        graph: RouteGraph,
        restricted_regions: set[UUID],
        disrupted_nodes: set[UUID],
    ) -> RouteGraph:
        filtered = graph.copy()
        for node_id in disrupted_nodes:
            filtered.remove_edges_for_node(node_id)
        # restricted_regions are region UUIDs; nodes belonging to them should
        # already have been removed via update_from_war_state, but we honour
        # the explicit set here too by removing any node whose ID appears in it.
        for region_id in restricted_regions:
            filtered.remove_edges_for_node(region_id)
        return filtered
