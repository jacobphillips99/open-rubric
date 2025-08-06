"""Visualization tools for multistep rubrics and requirements."""
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

# layout/sizing heuristic (streamlit-friendly; small graphs)
_MIN_BOX_W: float = 0.9
_MAX_BOX_W: float = 3.2
_CHAR_W: float = 0.09
_BOX_H: float = 0.45
_X_SEP: float = 0.35
_Y_STEP: float = 2.2
_TERMINAL_Y_GAP: float = 1.4


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


def _get_contrasting_text_color(hex_color: str) -> str:
    """Return black or white hex color for best contrast against a hex background."""
    try:
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
    except Exception:
        return "#000000"  # default to black
    luminance = 0.299 * r + 0.587 * g + 0.114 * b
    return "#ffffff" if luminance < 140 else "#000000"


def _maybe_truncate(text: str, n: int = 80) -> str:
    return (text[: n - 3] + "...") if len(text) > n else text


def _estimate_box_size(name: str) -> Tuple[float, float]:
    """Estimate a rectangle size that fits the node label reasonably."""
    # More responsive sizing: increased character width multiplier and wider range
    char_width_multiplier = 0.12  # increased from 0.09
    min_chars = 8  # minimum character assumption for readability
    padding = 0.4  # horizontal padding

    # Calculate width based on name length with more responsive scaling
    base_width = char_width_multiplier * max(min_chars, len(name)) + padding

    # More flexible min/max bounds for better responsiveness
    min_width = 0.8  # slightly smaller minimum
    max_width = 4.0  # larger maximum for long names

    w = min(max_width, max(min_width, base_width))
    return w, _BOX_H


class RequirementsVisualizer(BaseRequirementsInspector):
    """Visualizer focused on requirement dependencies and workflow structure."""

    # ---- public api -----------------------------------------------------

    def create_dependency_graph(
        self,
        width: int = 1200,
        height: int = 800,
        show_answer_labels: bool = False,  # default off: cleaner; labels on edge hover instead
        highlight_path: Optional[Dict[str, Any]] = None,
        show_terminal_states: bool = True,
        show_requirement_types: bool = True,
    ) -> go.Figure:
        """
        Build an interactive dependency graph.

        Args:
            width: figure width in px.
            height: figure height in px.
            show_answer_labels: draw static edge labels at midpoints (hover covers most needs).
            highlight_path: mapping {requirement_name: answer_value} to highlight the path taken.
            show_terminal_states: visually emphasize terminal nodes (draw diamonds).
            show_requirement_types: if false, collapse all types into one legend entry.

        returns:
            plotly figure.
        """
        nodes, edges = self._build_graph_data()
        positions = self._calculate_hierarchical_positions(nodes)

        fig = go.Figure()

        # draw elements in order: edges, then shapes, then text
        self._add_edges_to_figure(
            fig,
            edges,
            positions,
            show_answer_labels=show_answer_labels,
            highlight_path=highlight_path,
        )
        self._add_rectangle_nodes(
            fig, nodes, positions, highlight_path, show_terminal_states
        )
        self._add_nodes_to_figure(
            fig,
            nodes,
            positions,
            highlight_path=highlight_path,
            show_terminal_states=show_terminal_states,
            show_requirement_types=show_requirement_types,
        )

        self._add_unified_legend(fig, show_requirement_types, show_terminal_states)

        # fixed reasonable margins
        margin_sides = 80
        margin_top = 60
        margin_bottom = 40

        fig.update_layout(
            width=width,
            height=height,
            hovermode="closest",
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            plot_bgcolor="white",
            margin=dict(l=margin_sides, r=margin_sides, t=margin_top, b=margin_bottom),
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
        show_answer_labels: bool = False,
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

        # 4. summary bar
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
        """Extract node + edge metadata (plain dicts), ignoring dangling edge targets."""
        name_to_req = {r.name: r for r in self.requirements}
        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []

        for req in self.requirements:
            req_type = req.__class__.__name__.replace("Requirement", "").lower()
            judge_name = getattr(req, "judge_name", "auto-select") or "auto-select"

            dep_map = getattr(req, "dependencies", None) or {}
            branching_factor = sum(len(deps) for deps in dep_map.values())

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
                    if dep in name_to_req:  # ignore dangling targets cleanly
                        edges.append(
                            dict(source=req.name, target=dep, answer=answer_val)
                        )

        return nodes, edges

    # ---- layout helpers --------------------------------------------------

    def _adj(self) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
        """Forward and reverse adjacency."""
        fwd: Dict[str, List[str]] = {}
        rev: Dict[str, List[str]] = {}
        for req in self.requirements:
            for deps in (getattr(req, "dependencies", None) or {}).values():
                if not deps:
                    continue
                fwd.setdefault(req.name, []).extend(deps)
                for d in deps:
                    rev.setdefault(d, []).append(req.name)
        # ensure keys exist
        for r in self.requirements:
            fwd.setdefault(r.name, [])
            rev.setdefault(r.name, [])
        return fwd, rev

    def _order_levels_barycenter(
        self,
        levels: List[List[str]],
        fwd: Dict[str, List[str]],
        rev: Dict[str, List[str]],
        iters: int = 2,
    ) -> List[List[str]]:
        """Perform simple sugiyama-style crossing reduction by barycenter; cheap and good-enough."""
        L: List[List[str]] = [lvl[:] for lvl in levels]
        for _ in range(iters):
            # downward: order by parents (rev)
            for i in range(1, len(L)):
                prev = {n: idx for idx, n in enumerate(L[i - 1])}

                def score_down(n: str, prev=prev, level_len=len(L[i - 1])) -> float:
                    ps = rev.get(n, [])
                    return (
                        float(np.mean([prev.get(p, 0) for p in ps]))
                        if ps
                        else float(level_len) / 2
                    )

                L[i].sort(key=score_down)
            # upward: order by children (fwd)
            for i in range(len(L) - 2, -1, -1):
                nxt = {n: idx for idx, n in enumerate(L[i + 1])}

                def score_up(n: str, nxt=nxt, level_len=len(L[i + 1])) -> float:
                    cs = fwd.get(n, [])
                    return (
                        float(np.mean([nxt.get(c, 0) for c in cs]))
                        if cs
                        else float(level_len) / 2
                    )

                L[i].sort(key=score_up)
        return L

    def _calculate_hierarchical_positions(
        self, nodes: Sequence[Dict[str, Any]], spacing_factor: float = 1.0
    ) -> Dict[str, Tuple[float, float]]:
        """
        Compute topological layout with all terminal requirements at the bottom.
        - keep topo levels (roots at level 0, etc.)
        - remove terminals from their native level and put them on a single bottom row
        - reduce crossings by a light barycenter pass on non-terminal levels
        """
        # name_to_node: Dict[str, Dict[str, Any]] = {n["name"]: n for n in nodes}  # unused
        fwd, rev = self._adj()

        terminals = [n for n in nodes if n["is_terminal"]]
        terminal_names = set(n["name"] for n in terminals)

        # strip terminals from levels; keep only non-terminals for layered layout
        nonterm_levels: List[List[str]] = []
        for lvl in self.levels:
            non = [n for n in lvl if n not in terminal_names]
            if non:
                nonterm_levels.append(non)

        # crossing reduction
        ordered_levels = self._order_levels_barycenter(nonterm_levels, fwd, rev)

        positions: Dict[str, Tuple[float, float]] = {}

        # compute layout dimensions
        max_width = max(len(lvl) for lvl in ordered_levels) if ordered_levels else 1
        if terminals:
            max_width = max(max_width, len(terminals))

        # adaptive horizontal spacing based on node count + new estimate_box_size
        base_spread = max(4.0, max_width * 1.5) * spacing_factor

        # position non-terminal levels (top-down)
        for i, lvl in enumerate(ordered_levels):
            y = float(len(ordered_levels) - 1 - i) * _Y_STEP
            if len(lvl) == 1:
                positions[lvl[0]] = (0.0, y)
            else:
                xs = np.linspace(-base_spread / 2, base_spread / 2, len(lvl))
                for x, name in zip(xs, lvl):
                    positions[name] = (float(x), y)

        # position terminals at bottom
        if terminals:
            y_terminal = -_Y_STEP if ordered_levels else 0.0
            if not ordered_levels:
                y_terminal -= _TERMINAL_Y_GAP

            if len(terminals) == 1:
                positions[terminals[0]["name"]] = (0.0, y_terminal)
            else:
                xs = np.linspace(-base_spread / 2, base_spread / 2, len(terminals))
                for x, term_node in zip(xs, terminals):
                    positions[term_node["name"]] = (float(x), y_terminal)

        # fallback for missed nodes
        for node in nodes:
            positions.setdefault(node["name"], (0.0, 0.0))

        return positions

    def _add_unified_legend(
        self, fig: go.Figure, show_requirement_types: bool, show_terminal_states: bool
    ) -> None:
        """Add a single, clean legend for all visual elements."""

        def add_legend_item(name, mode, **kwargs):
            fig.add_trace(
                go.Scatter(
                    x=[None], y=[None], name=name, mode=mode, showlegend=True, **kwargs
                )
            )

        # Node Shapes
        if show_terminal_states:
            add_legend_item(
                "Non-Terminal",
                "markers",
                marker=dict(symbol="square", color=_FALLBACK_COLOR, size=10),
            )
            add_legend_item(
                "Terminal",
                "markers",
                marker=dict(
                    symbol="diamond",
                    color=_darken_hex(_FALLBACK_COLOR, _TERMINAL_DARKEN),
                    size=10,
                ),
            )
        else:
            add_legend_item(
                "Requirement",
                "markers",
                marker=dict(symbol="square", color=_FALLBACK_COLOR, size=10),
            )

        # Node Colors
        if show_requirement_types:
            for req_type, color in _TYPE_COLORS.items():
                add_legend_item(
                    f"Type: {req_type.capitalize()}",
                    "markers",
                    marker=dict(symbol="square", color=color, size=10),
                )

        # Edge Colors
        edge_styles = {
            "Correct Path": self._edge_style_for_type("correct")[0],
            "Incorrect Path": self._edge_style_for_type("incorrect")[0],
            "Other Path": self._edge_style_for_type("partial")[0],
            "Highlighted Path": "#e74c3c",
        }
        for name, color in edge_styles.items():
            add_legend_item(name, "lines", line=dict(color=color, width=3))

    # ---- drawing helpers --------------------------------------------------

    def _node_color(self, node: Dict[str, Any], show_terminal_states: bool) -> str:
        base = _TYPE_COLORS.get(node["req_type"], _FALLBACK_COLOR)
        if show_terminal_states and node["is_terminal"]:
            return _darken_hex(base, _TERMINAL_DARKEN)
        return base

    def _add_nodes_to_figure(
        self,
        fig: go.Figure,
        nodes: Sequence[Dict[str, Any]],
        positions: Dict[str, Tuple[float, float]],
        highlight_path: Optional[Dict[str, Any]],
        show_terminal_states: bool,
        show_requirement_types: bool,
    ) -> None:
        """Add node traces (text labels for clean overlays on shapes)."""

        def group_key(n: Dict[str, Any]) -> str:
            return n["req_type"] if show_requirement_types else "all"

        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for n in nodes:
            grouped.setdefault(group_key(n), []).append(n)

        for _key, group_nodes in grouped.items():
            xs: List[float] = []
            ys: List[float] = []
            texts: List[str] = []
            hover_texts: List[str] = []
            colors: List[str] = []
            text_colors: List[str] = []

            for n in group_nodes:
                x, y = positions[n["name"]]
                xs.append(x)
                ys.append(y)

                # use readable truncated name
                name = n["name"]
                texts.append(name)

                node_color = self._node_color(n, show_terminal_states)
                colors.append(node_color)
                text_colors.append("#ffffff")

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

            # text layer with better visibility
            fig.add_trace(
                go.Scatter(
                    x=xs,
                    y=ys,
                    mode="text",
                    text=texts,
                    textfont=dict(
                        size=10,
                        color=text_colors,
                        family="Arial",
                    ),
                    textposition="middle center",
                    hovertext=hover_texts,
                    hoverinfo="text",
                    showlegend=False,
                )
            )

    def _add_rectangle_nodes(
        self,
        fig: go.Figure,
        nodes: Sequence[Dict[str, Any]],
        positions: Dict[str, Tuple[float, float]],
        highlight_path: Optional[Dict[str, Any]],
        show_terminal_states: bool,
    ) -> None:
        """Add rectangle/diamond shapes for nodes with text-fitting dimensions."""
        for node in nodes:
            x, y = positions[node["name"]]
            name = node["name"]

            # estimate dimensions
            w, h = _estimate_box_size(name)

            # adjust for highlight/terminal status
            if highlight_path and node["name"] in highlight_path:
                w *= 1.1
                h *= 1.1
                line_width = 3
            elif node["is_terminal"]:
                w *= 1.05
                h *= 1.05
                line_width = 2
            else:
                line_width = 2

            color = self._node_color(node, show_terminal_states)

            # shape type based on terminal status
            if show_terminal_states and node["is_terminal"]:
                self._add_diamond_shape(fig, x, y, w, h, color, line_width)
            else:
                fig.add_shape(
                    type="rect",
                    x0=x - w / 2,
                    y0=y - h / 2,
                    x1=x + w / 2,
                    y1=y + h / 2,
                    fillcolor=color,
                    line=dict(color="white", width=line_width),
                    opacity=1.0,
                    layer="below",
                )

    def _add_diamond_shape(
        self,
        fig: go.Figure,
        x: float,
        y: float,
        width: float,
        height: float,
        color: str,
        line_width: int,
    ) -> None:
        """Add a diamond shape for terminal nodes."""
        half_width = width / 2
        half_height = height / 2

        # diamond points: top, right, bottom, left
        diamond_x = [x, x + half_width, x, x - half_width, x]
        diamond_y = [y + half_height, y, y - half_height, y, y + half_height]

        # create path string
        path = f"M {diamond_x[0]},{diamond_y[0]}"
        for i in range(1, len(diamond_x)):
            path += f" L {diamond_x[i]},{diamond_y[i]}"
        path += " Z"

        fig.add_shape(
            type="path",
            path=path,
            fillcolor=color,
            line=dict(color="white", width=line_width),
            opacity=1.0,
            layer="below",
        )

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

    def _answer_type_for_legend(self, answer: Any) -> str:
        """Categorize answer for legend purposes."""
        try:
            val = float(answer)
            if val == 1.0:
                return "correct (1.0)"
            elif val == 0.0:
                return "incorrect (0.0)"
            else:
                return "partial"
        except Exception:
            return "other"

    def _edge_style_for_type(self, answer_type: str) -> Tuple[str, int]:
        """Get color and width for a specific answer type."""
        if "correct" in answer_type:
            return "#27ae60", 2
        elif "incorrect" in answer_type:
            return "#e74c3c", 2
        elif "partial" in answer_type:
            return "#f39c12", 2
        else:
            return "#f39c12", 2

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
    """Visualizer for a complete multistep rubric (currently a placeholder)."""

    pass


class CompletedRubricVisualizer(BaseEvaluationInspector):
    """Visualizer for evaluated rubrics + results (currently a placeholder)."""

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
