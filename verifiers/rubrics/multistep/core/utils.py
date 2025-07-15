from collections import defaultdict, deque


def topological_levels(dependencies: dict[str, list[str] | None]) -> list[list[str]]:
    """
    Topological sort of a DAG of dependencies which returns a list of levels,
    such that every node's dependencies live in earlier levels.
    """
    deps: dict[str, list[str]] = {k: (v or []) for k, v in dependencies.items()}
    out_edges: dict[str, list[str]] = defaultdict(list)
    in_degrees: dict[str, int] = defaultdict(int)

    for n, pres in deps.items():
        in_degrees.setdefault(n, 0)
        for p in pres:
            out_edges[p].append(n)
            in_degrees[n] += 1
            in_degrees.setdefault(p, 0)

    queue: deque[str] = deque([n for n, d in in_degrees.items() if d == 0])
    levels: list[list[str]] = []

    while queue:
        this_lvl = list(queue)
        levels.append(this_lvl)
        for _ in range(len(this_lvl)):
            n = queue.popleft()
            for m in out_edges[n]:
                in_degrees[m] -= 1
                if in_degrees[m] == 0:
                    queue.append(m)

    if sum(len(level) for level in levels) != len(in_degrees):
        raise ValueError("Cycle detected in dependencies; levelization impossible")
    return levels 