"""Utility functions for MultiStep Rubric workflows."""

from collections import defaultdict
from typing import Dict, List


def topological_levels(graph: Dict[str, List[str]]) -> List[List[str]]:
    """
    Topological levels of a graph. Based on the idea that {a: [b, c]} means "a enables b and c".
    Work should be done in the order [[a], [b, c]].

    Args:
        graph: A dictionary mapping nodes to their dependencies.

    Returns:
        A list of lists, where each inner list represents a level of the graph.
    """
    graph = {k: (v if v is not None else []) for k, v in graph.items()}

    # build in-degree (how many prerequisites each node has)
    in_degree = defaultdict(int)
    children = defaultdict(list)

    for parent, unlocks in graph.items():
        for child in unlocks:
            in_degree[child] += 1
            children[parent].append(child)
        in_degree[parent] += 0  # ensure key exists

    # start with nodes that have no prerequisites
    layer = [node for node in graph if in_degree[node] == 0]
    result = []

    while layer:
        result.append(sorted(layer))
        next_layer = []
        for node in layer:
            for child in children[node]:
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    next_layer.append(child)
        layer = next_layer
    return result
