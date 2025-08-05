"""
visualization utilities for multistep rubric workflows.

improvements vs original:
- clearer separation of data prep vs rendering
- simpler layout calc
- fixed path-finding logic (previous version walked edges backwards + duplicated nodes)
- optional collapsing of requirement types into a single legend entry
- less duplication of color/shape logic
- stricter type hints + docstrings
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from multistep_extras.inspection.base_inspector import (
    BaseEvaluationInspector, BaseRequirementsInspector, BaseRubricInspector)
from verifiers.rubrics.multistep.multistep_rubric import MultiStepRubric
from verifiers.rubrics.multistep.requirement import Requirement

# palette + glyph config
_TYPE_COLORS: Dict[str, str] = {
    "binary": "#3498db",
    "discrete": "#e67e22",
    "continuous": "#27ae60",
    "unit_vector": "#e74c3c",
}
_TERMINAL_DARKEN: float = 0.85  # multiply rgb to get darker shade
_FALLBACK_COLOR = "#7f8c8d"


def _darken_hex(hex_color: str, factor: float) -> str:
    """Darken a #rrggbb color by multiplying channels by factor."""
    try:
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
    except Exception:
        return hex_color
    r = int(max(0, min(255, r * factor)))
    g = int(max(0, min(255, g * factor)))
    b = int(max(0, min(255, b * factor)))
    return f"#{r:02x}{g:02x}{b:02x}"


def _maybe_truncate(text: str, n: int = 80) -> str:
    return (text[: n - 3] + "...") if len(text) > n else text


class RequirementsVisualizer(BaseRequirementsInspector):
    """Visualizer focused on requirement dependencies and workflow structure."""

    # ---- public api -----------------------------------------------------

    def create_dependency_graph(
        self,
        width: int = 1200,
        height: int = 800,
        show_answer_labels: bool = True,
        highlight_path: Optional[Dict[str, Any]] = None,
        show_terminal_states: bool = True,
        show_requirement_types: bool = True,
    ) -> go.Figure:
        """
        Build an interactive dependency graph.

        args:
            width: figure width in px.
            height: figure height in px.
            show_answer_labels: show answer values at edge midpoints.
            highlight_path: mapping {requirement_name: answer_value} to highlight the path taken.
            show_terminal_states: visually emphasize terminal nodes.
            show_requirement_types: if false, collapse all types into one legend entry.

        returns:
            plotly figure.
        """
        nodes, edges = self._build_graph_data()
        positions = self._calculate_hierarchical_positions(nodes)

        fig = go.Figure()
        self._add_edges_to_figure(
            fig,
            edges,
            positions,
            show_answer_labels=show_answer_labels,
            highlight_path=highlight_path,
        )
        self._add_nodes_to_figure(
            fig,
            nodes,
            positions,
            highlight_path=highlight_path,
            show_terminal_states=show_terminal_states,
            show_requirement_types=show_requirement_types,
        )

        fig.update_layout(
            title=dict(
                text="Dependency Graph",
                x=0.5,
                xanchor="center",
                font=dict(size=18, color="#2c3e50"),
            ),
            width=width,
            height=height,
            hovermode="closest",
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            plot_bgcolor="white",
            margin=dict(l=20, r=20, t=60, b=20),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                bgcolor="rgba(255,255,255,0.85)",
                bordercolor="lightgray",
                borderwidth=1,
                font=dict(size=10),
            ),
        )
        return fig

    def create_path_visualization(
        self,
        answers: Dict[str, Any],
        width: int = 1200,
        height: int = 800,
        show_answer_labels: bool = True,
        show_terminal_states: bool = True,
    ) -> go.Figure:
        """Visualize a specific evaluation path."""
        return self.create_dependency_graph(
            width=width,
            height=height,
            show_answer_labels=show_answer_labels,
            highlight_path=answers,
            show_terminal_states=show_terminal_states,
        )

    def create_metrics_dashboard(self) -> go.Figure:
        """Dashboard with structural metrics."""
        metrics = self.analyze_metrics()

        fig = make_subplots(
            rows=2,
            cols=2,
            subplot_titles=(
                "requirement types & terminal states",
                "workflow structure",
                "dependency distribution",
                "summary",
            ),
            specs=[
                [{"type": "pie"}, {"type": "bar"}],
                [{"type": "histogram"}, {"type": "bar"}],
            ],
        )

        # 1. type + terminal counts
        type_terminal_counts: Dict[str, int] = {}
        for req in self.requirements:
            t = req.__class__.__name__.replace("Requirement", "")
            label = f"{t} ({'terminal' if req.terminal() else 'non-terminal'})"
            type_terminal_counts[label] = type_terminal_counts.get(label, 0) + 1
        fig.add_trace(
            go.Pie(
                labels=list(type_terminal_counts.keys()),
                values=list(type_terminal_counts.values()),
            ),
            row=1,
            col=1,
        )

        # 2. structure stats
        structure_stats = {
            "total requirements": metrics["total_requirements"],
            "terminal nodes": metrics["terminal_nodes"],
            "branching nodes": metrics["branching_nodes"],
            "multi-branch nodes": metrics["multi_branch_nodes"],
            "root nodes": len(metrics["root_nodes"]),
        }
        fig.add_trace(
            go.Bar(x=list(structure_stats.keys()), y=list(structure_stats.values())),
            row=1,
            col=2,
        )

        # 3. dependency distribution (# answer->deps keys per requirement)
        dep_counts = [
            len(req.dependencies) if getattr(req, "dependencies", None) else 0
            for req in self.requirements
        ]
        fig.add_trace(
            go.Histogram(x=dep_counts, nbinsx=min(10, len(dep_counts))), row=2, col=1
        )

        # 4. summary bar: terminals vs non-terminals + max depth + avg branching (encoded as value)
        terminal = metrics["terminal_nodes"]
        non_terminal = metrics["total_requirements"] - terminal
        summary_keys = ["terminal", "non-terminal", "max depth", "avg branching"]
        summary_vals = [
            terminal,
            non_terminal,
            metrics["max_depth"],
            float(f"{metrics['avg_branching_factor']:.2f}"),
        ]
        fig.add_trace(go.Bar(x=summary_keys, y=summary_vals), row=2, col=2)

        fig.update_layout(
            title=dict(
                text="multistep rubric metrics dashboard",
                x=0.5,
                xanchor="center",
                font=dict(size=18, color="#2c3e50"),
            ),
            height=800,
            showlegend=False,
        )
        return fig

    def create_terminal_analysis(self) -> Dict[str, Any]:
        """Detailed terminal state analysis."""
        terminal_nodes = [req for req in self.requirements if req.terminal()]
        non_terminal_nodes = [req for req in self.requirements if not req.terminal()]

        terminal_by_type: Dict[str, int] = {}
        for req in terminal_nodes:
            t = req.__class__.__name__.replace("Requirement", "")
            terminal_by_type[t] = terminal_by_type.get(t, 0) + 1

        # compute all root->terminal paths for each terminal node
        paths_to_terminal: Dict[str, List[List[str]]] = {}
        forward_adj = self._forward_adjacency()
        root_names = set(self.analyze_metrics()["root_nodes"])
        for t_req in terminal_nodes:
            paths_to_terminal[t_req.name] = self._paths_to_target(
                roots=root_names, target=t_req.name, forward_adj=forward_adj
            )

        return {
            "terminal_nodes": len(terminal_nodes),
            "non_terminal_nodes": len(non_terminal_nodes),
            "terminal_by_type": terminal_by_type,
            "paths_to_terminal": paths_to_terminal,
            "terminal_percentage": (
                len(terminal_nodes) / max(1, len(self.requirements))
            )
            * 100.0,
        }

    # ---- internal data prep ---------------------------------------------

    def _build_graph_data(self) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Extract node + edge metadata (plain dicts)."""
        name_to_req = {r.name: r for r in self.requirements}
        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []

        for req in self.requirements:
            req_type = req.__class__.__name__.replace("Requirement", "").lower()
            judge_name = getattr(req, "judge_name", "auto-select") or "auto-select"

            branching_factor = 0
            dep_map = getattr(req, "dependencies", None) or {}
            for deps in dep_map.values():
                branching_factor += len(deps)

            nodes.append(
                dict(
                    name=req.name,
                    question=req.question,
                    req_type=req_type,
                    is_terminal=req.terminal(),
                    judge_name=judge_name,
                    branching_factor=branching_factor,
                    dependencies_count=len(dep_map),
                )
            )

            for answer_val, deps in dep_map.items():
                for dep in deps:
                    if dep not in name_to_req:
                        pass  # dangling ok
                    edges.append(dict(source=req.name, target=dep, answer=answer_val))

        return nodes, edges

    def _calculate_hierarchical_positions(
        self, nodes: Sequence[Dict[str, Any]]
    ) -> Dict[str, Tuple[float, float]]:
        """
        Compute simple topological layout with all terminal requirements at the bottom.

        Each 'level' from BaseRequirementsInspector is a horizontal layer; we space nodes within.
        Terminal requirements are grouped at the bottom regardless of their topological level.
        """
        positions: Dict[str, Tuple[float, float]] = {}
        max_level_index = len(self.levels) - 1
        
        # Collect terminal requirement names
        terminal_names = {node["name"] for node in nodes if node["is_terminal"]}
        
        # Position non-terminal requirements using topological levels
        for lvl_idx, level in enumerate(self.levels):
            # Filter out terminal requirements from this level
            non_terminal_names = [name for name in level if name not in terminal_names]
            y = max_level_index - lvl_idx  # roots top
            
            if not non_terminal_names:
                continue
                
            xs = (
                np.linspace(-1.5, 1.5, len(non_terminal_names))
                if len(non_terminal_names) > 1
                else [0.0]
            )
            for x, name in zip(xs, non_terminal_names):
                positions[name] = (float(x), float(y))
        
        # Position all terminal requirements at the bottom
        if terminal_names:
            terminal_list = list(terminal_names)
            y_terminal = -1  # Below all other levels
            xs_terminal = (
                np.linspace(-1.5, 1.5, len(terminal_list))
                if len(terminal_list) > 1
                else [0.0]
            )
            for x, name in zip(xs_terminal, terminal_list):
                positions[name] = (float(x), float(y_terminal))
        
        # Fallback for any missed nodes
        for node in nodes:
            positions.setdefault(node["name"], (0.0, 0.0))
            
        return positions

    # ---- drawing helpers -------------------------------------------------

    def _add_nodes_to_figure(
        self,
        fig: go.Figure,
        nodes: Sequence[Dict[str, Any]],
        positions: Dict[str, Tuple[float, float]],
        highlight_path: Optional[Dict[str, Any]],
        show_terminal_states: bool,
        show_requirement_types: bool,
    ) -> None:
        """Add node traces."""

        def group_key(n: Dict[str, Any]) -> str:
            return n["req_type"] if show_requirement_types else "all"

        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for n in nodes:
            grouped.setdefault(group_key(n), []).append(n)

        for key, group_nodes in grouped.items():
            xs: List[float] = []
            ys: List[float] = []
            texts: List[str] = []
            hover_texts: List[str] = []
            sizes: List[int] = []
            colors: List[str] = []
            symbols: List[str] = []

            for n in group_nodes:
                x, y = positions[n["name"]]
                xs.append(x)
                ys.append(y)
                texts.append(n["name"])
                colors.append(self._node_color(n, show_terminal_states))
                symbols.append(
                    "diamond"
                    if (show_terminal_states and n["is_terminal"])
                    else "circle"
                )
                sizes.append(
                    28
                    if (highlight_path and n["name"] in highlight_path)
                    else (24 if n["is_terminal"] else 18)
                )
                hover_texts.append(
                    "<br>".join(
                        [
                            f"<b>{n['name']}</b>",
                            f"type: {n['req_type']}",
                            f"status: {'terminal' if n['is_terminal'] else 'non-terminal'}",
                            f"judge: {n['judge_name']}",
                            f"question: {_maybe_truncate(n['question'])}",
                            f"outgoing paths: {n['branching_factor']}",
                            f"multiple paths: {'yes' if n['branching_factor'] > 1 else 'no'}",
                        ]
                    )
                )

            legend_name = "all requirements" if key == "all" else key
            fig.add_trace(
                go.Scatter(
                    x=xs,
                    y=ys,
                    mode="markers+text",
                    text=texts,
                    textposition="middle center",
                    textfont=dict(size=10, color="white"),
                    hovertext=hover_texts,
                    hoverinfo="text",
                    marker=dict(
                        size=sizes,
                        color=colors,
                        line=dict(width=2, color="white"),
                        symbol=symbols,
                        opacity=0.9,
                    ),
                    name=legend_name,
                )
            )

    def _node_color(self, node: Dict[str, Any], show_terminal_states: bool) -> str:
        base = _TYPE_COLORS.get(node["req_type"], _FALLBACK_COLOR)
        if show_terminal_states and node["is_terminal"]:
            return _darken_hex(base, _TERMINAL_DARKEN)
        return base

    def _add_edges_to_figure(
        self,
        fig: go.Figure,
        edges: Sequence[Dict[str, Any]],
        positions: Dict[str, Tuple[float, float]],
        show_answer_labels: bool,
        highlight_path: Optional[Dict[str, Any]],
    ) -> None:
        """Add edges + (optional) answer labels."""
        for e in edges:
            x0, y0 = positions[e["source"]]
            x1, y1 = positions[e["target"]]

            is_highlight = (
                highlight_path is not None
                and e["source"] in highlight_path
                and str(highlight_path[e["source"]]) == str(e["answer"])
            )

            color, width = self._edge_style(e["answer"], is_highlight)
            fig.add_trace(
                go.Scatter(
                    x=[x0, x1],
                    y=[y0, y1],
                    mode="lines",
                    line=dict(color=color, width=width),
                    hoverinfo="none",
                    showlegend=False,
                )
            )

        if show_answer_labels:
            label_x: List[float] = []
            label_y: List[float] = []
            label_text: List[str] = []
            label_colors: List[str] = []
            for e in edges:
                x0, y0 = positions[e["source"]]
                x1, y1 = positions[e["target"]]
                label_x.append((x0 + x1) / 2)
                label_y.append((y0 + y1) / 2)
                label_text.append(str(e["answer"]))
                label_colors.append(self._edge_style(e["answer"], False)[0])
            fig.add_trace(
                go.Scatter(
                    x=label_x,
                    y=label_y,
                    mode="text",
                    text=label_text,
                    textfont=dict(size=10, color=label_colors),
                    hoverinfo="none",
                    showlegend=False,
                )
            )

    def _edge_style(self, answer: Any, is_highlight: bool) -> Tuple[str, int]:
        """Color + width for an edge given its answer + highlight state."""
        if is_highlight:
            return "#e74c3c", 4
        try:
            val = float(answer)
        except Exception:
            return "#f39c12", 2
        if val == 1.0:
            return "#27ae60", 2
        if val == 0.0:
            return "#e74c3c", 2
        return "#f39c12", 2

    # ---- path finding ---------------------------------------------------

    def _forward_adjacency(self) -> Dict[str, List[str]]:
        adj: Dict[str, List[str]] = {}
        for req in self.requirements:
            for deps in (getattr(req, "dependencies", None) or {}).values():
                adj.setdefault(req.name, []).extend(deps)
        return adj

    def _paths_to_target(
        self, roots: Iterable[str], target: str, forward_adj: Dict[str, List[str]]
    ) -> List[List[str]]:
        """Enumerate all simple paths from any root in `roots` to `target` using dfs along forward edges."""
        paths: List[List[str]] = []

        def dfs(node: str, path: List[str], visited: Set[str]) -> None:
            if node in visited:
                return
            path.append(node)
            visited.add(node)
            if node == target:
                paths.append(path.copy())
            else:
                for nxt in forward_adj.get(node, []):
                    dfs(nxt, path, visited)
            visited.remove(node)
            path.pop()

        for r in roots:
            dfs(r, [], set())
        return paths


class RubricVisualizer(BaseRubricInspector):
    """visualizer for a complete multistep rubric (currently a placeholder)."""

    pass


class CompletedRubricVisualizer(BaseEvaluationInspector):
    """visualizer for evaluated rubrics + results (currently a placeholder)."""

    pass


# convenience functions ----------------------------------------------------


def visualize_requirements(requirements: Sequence[Requirement]) -> None:
    """Print summary information for quick inspection."""
    viz = RequirementsVisualizer(list(requirements))
    viz.print_dependency_graph()
    viz.print_workflow_structure()
    viz.print_metrics()


def create_dependency_graph(
    requirements: Sequence[Requirement], **kwargs: Any
) -> go.Figure:
    """Create a dependency graph for a list of requirements."""
    return RequirementsVisualizer(list(requirements)).create_dependency_graph(**kwargs)


def create_rubric_dependency_graph(rubric: MultiStepRubric, **kwargs: Any) -> go.Figure:
    """Create a dependency graph for a multistep rubric."""
    return RequirementsVisualizer(list(rubric.requirements)).create_dependency_graph(
        **kwargs
    )


def create_path_visualization(
    requirements: Sequence[Requirement], answers: Dict[str, Any], **kwargs: Any
) -> go.Figure:
    """Highlight a specific evaluation path through the requirements."""
    return RequirementsVisualizer(list(requirements)).create_path_visualization(
        answers, **kwargs
    )


def create_metrics_dashboard(requirements: Sequence[Requirement]) -> go.Figure:
    """Build metrics dashboard."""
    return RequirementsVisualizer(list(requirements)).create_metrics_dashboard()


def compare_requirements(
    workflow1: Sequence[Requirement],
    workflow2: Sequence[Requirement],
    names: Tuple[str, str] = ("workflow 1", "workflow 2"),
) -> None:
    """Print side-by-side metric comparison."""
    print(f"comparing requirements: {names[0]} vs {names[1]}")
    print("=" * 80)

    viz1 = RequirementsVisualizer(list(workflow1))
    viz2 = RequirementsVisualizer(list(workflow2))
    metrics1 = viz1.analyze_metrics()
    metrics2 = viz2.analyze_metrics()

    header = f"{'metric':<25} {names[0]:<20} {names[1]:<20}"
    print(header)
    print("-" * len(header))

    comparison_metrics = [
        "total_requirements",
        "terminal_nodes",
        "branching_nodes",
        "multi_branch_nodes",
        "max_depth",
        "avg_branching_factor",
        "total_edges",
    ]
    for metric in comparison_metrics:
        v1 = metrics1[metric]
        v2 = metrics2[metric]
        if isinstance(v1, float):
            print(f"{metric:<25} {v1:<20.2f} {v2:<20.2f}")
        else:
            print(f"{metric:<25} {v1:<20} {v2:<20}")
    print()
