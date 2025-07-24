"""
Visualization utilities for MultiStep Rubric workflows.

This module provides three specialized visualizers for different use cases:
1. RequirementsVisualizer - For analyzing requirement dependencies
2. RubricVisualizer - For visualizing complete rubrics with nodes
3. CompletedRubricVisualizer - For visualizing evaluated rubrics with results
"""

from typing import Any, Dict, List, Tuple, Optional, Set
import plotly.graph_objects as go
import plotly.express as px
import numpy as np

from verifiers.rubrics.multistep.multistep_rubric import MultiStepRubric
from verifiers.rubrics.multistep.requirement import Requirement
from verifiers.rubrics.multistep.scenario import Scenario

from multistep_extras.inspection.base_inspector import (BaseRequirementsInspector, BaseRubricInspector,
                                         BaseEvaluationInspector)


class RequirementsVisualizer(BaseRequirementsInspector):
    """Visualizer focused on requirement dependencies and workflow structure."""

    def create_dependency_graph(
        self, 
        width: int = 1200, 
        height: int = 800,
        show_answer_labels: bool = True,
        highlight_path: Optional[Dict[str, float]] = None,
        show_terminal_states: bool = True,
        show_requirement_types: bool = True
    ) -> go.Figure:
        """
        Create an interactive Plotly graph showing requirement dependencies.

        Args:
            width: Graph width in pixels
            height: Graph height in pixels
            show_answer_labels: Whether to show answer values on edges
            highlight_path: Optional dict of requirement answers to highlight a specific path
            show_terminal_states: Whether to emphasize terminal states with special styling
            show_requirement_types: Whether to differentiate requirement types visually

        Returns:
            Plotly Figure object
        """
        # Build graph data
        nodes, edges = self._build_graph_data()
        
        # Calculate hierarchical positions
        positions = self._calculate_hierarchical_positions(nodes)

        # Create figure
        fig = go.Figure()

        # Add edges first (so they appear behind nodes)
        self._add_edges_to_figure(fig, edges, positions, show_answer_labels, highlight_path)
        
        # Add nodes with enhanced styling
        self._add_nodes_to_figure(fig, nodes, positions, highlight_path, show_terminal_states, show_requirement_types)

        # Configure layout with improved usability
        fig.update_layout(
            title={
                'text': "MultiStep Rubric Dependency Graph",
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 18, 'color': '#2c3e50'}
            },
            width=width,
            height=height,
            showlegend=True,
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
                bgcolor="rgba(255,255,255,0.8)",
                bordercolor="lightgray",
                borderwidth=1
            )
        )

        return fig

    def _build_graph_data(self) -> Tuple[List[Dict], List[Dict]]:
        """Build node and edge data structures for the graph."""
        nodes = []
        edges = []

        # Build nodes with enhanced metadata
        for req in self.requirements:
            req_type = req.__class__.__name__.replace("Requirement", "").lower()
            
            # Determine node properties
            is_terminal = req.terminal()
            judge_name = getattr(req, 'judge_name', None)
            
            # Calculate branching factor
            branching_factor = 0
            if req.dependencies:
                for answer, deps in req.dependencies.items():
                    branching_factor += len(deps)
            
            node = {
                "id": req.name,
                "label": req.name,
                "question": req.question,
                "type": req_type,
                "is_terminal": is_terminal,
                "judge_name": judge_name or "auto-select",
                "dependencies_count": len(req.dependencies) if req.dependencies else 0,
                "branching_factor": branching_factor,
                "has_multiple_paths": branching_factor > 1
            }
            nodes.append(node)

        # Build edges with enhanced metadata
        for req in self.requirements:
            if req.dependencies:
                for answer, deps in req.dependencies.items():
                    for dep in deps:
                        edge = {
                            "source": req.name,
                            "target": dep,
                            "answer": answer,
                            "label": str(answer),
                            "source_type": req.__class__.__name__.replace("Requirement", "").lower(),
                            "target_type": next((r.__class__.__name__.replace("Requirement", "").lower() 
                                               for r in self.requirements if r.name == dep), "unknown")
                        }
                        edges.append(edge)

        return nodes, edges

    def _calculate_hierarchical_positions(self, nodes: List[Dict]) -> Dict[str, Tuple[float, float]]:
        """Calculate positions using hierarchical layout based on topological levels."""
        positions = {}
        
        # Group nodes by level
        level_to_nodes = {}
        for level_idx, level in enumerate(self.levels):
            level_to_nodes[level_idx] = level

        # Calculate positions with better spacing
        max_level = len(self.levels) - 1
        for level_idx, node_names in level_to_nodes.items():
            y = max_level - level_idx  # Top to bottom
            
            # Spread nodes horizontally within the level with better spacing
            if len(node_names) == 1:
                x_positions = [0]
            else:
                # Use wider spacing for better visual separation
                x_positions = np.linspace(-1.5, 1.5, len(node_names))
            
            for i, node_name in enumerate(node_names):
                positions[node_name] = (x_positions[i], y)

        return positions

    def _add_nodes_to_figure(
        self, 
        fig: go.Figure, 
        nodes: List[Dict], 
        positions: Dict[str, Tuple[float, float]],
        highlight_path: Optional[Dict[str, float]] = None,
        show_terminal_states: bool = True,
        show_requirement_types: bool = True
    ) -> None:
        """Add nodes to the figure with enhanced styling."""
        
        # Enhanced color scheme for different node types and states
        type_colors = {
            "binary": "#3498db",      # Blue
            "discrete": "#e67e22",    # Orange  
            "continuous": "#27ae60",   # Green
            "unit_vector": "#e74c3c"  # Red
        }
        
        # Terminal state styling
        terminal_colors = {
            "binary": "#2980b9",      # Darker blue
            "discrete": "#d35400",    # Darker orange
            "continuous": "#229954",   # Darker green
            "unit_vector": "#c0392b"  # Darker red
        }

        # Group nodes by type and terminal status for better organization
        node_groups = {}
        for node in nodes:
            node_type = node["type"]
            is_terminal = node["is_terminal"]
            
            # Create composite key for grouping
            if show_terminal_states and is_terminal:
                group_key = f"{node_type}_terminal"
            else:
                group_key = f"{node_type}_non_terminal"
            
            if group_key not in node_groups:
                node_groups[group_key] = []
            node_groups[group_key].append(node)

        for group_key, group_nodes in node_groups.items():
            x_coords = []
            y_coords = []
            texts = []
            hover_texts = []
            colors = []
            sizes = []
            shapes = []

            for node in group_nodes:
                x, y = positions[node["id"]]
                x_coords.append(x)
                y_coords.append(y)
                texts.append(node["label"])
                
                # Enhanced hover text with more details
                hover_text = (
                    f"<b>{node['label']}</b><br>"
                    f"Type: {node['type'].title()}<br>"
                    f"Status: {'Terminal' if node['is_terminal'] else 'Non-Terminal'}<br>"
                    f"Question: {node['question'][:80]}{'...' if len(node['question']) > 80 else ''}<br>"
                    f"Judge: {node['judge_name']}<br>"
                    f"Outgoing Paths: {node['branching_factor']}<br>"
                    f"Multiple Paths: {'Yes' if node['has_multiple_paths'] else 'No'}"
                )
                hover_texts.append(hover_text)

                # Determine styling based on type and terminal status
                node_type = node["type"]
                is_terminal = node["is_terminal"]
                
                # Color selection
                if is_terminal and show_terminal_states:
                    base_color = terminal_colors.get(node_type, "#34495e")
                    # Use diamond shape for terminal nodes
                    shapes.append("diamond")
                    sizes.append(25)  # Larger for terminal nodes
                else:
                    base_color = type_colors.get(node_type, "#95a5a6")
                    # Use circle for non-terminal nodes
                    shapes.append("circle")
                    sizes.append(18)
                
                # Highlight if in path
                if highlight_path and node["id"] in highlight_path:
                    colors.append("#e74c3c")  # Red for highlighted
                    sizes.append(30)  # Even larger for highlighted
                else:
                    colors.append(base_color)

            # Create legend name
            if "terminal" in group_key:
                legend_name = f"{node_type.title()} (Terminal)"
            else:
                legend_name = f"{node_type.title()} (Non-Terminal)"

            # Add scatter trace for this node group
            fig.add_trace(go.Scatter(
                x=x_coords,
                y=y_coords,
                mode="markers+text",
                marker=dict(
                    size=sizes,
                    color=colors,
                    line=dict(width=2, color="white"),
                    opacity=0.9,
                    symbol=shapes
                ),
                text=texts,
                textposition="middle center",
                textfont=dict(size=9, color="white", family="Arial Bold"),
                hovertext=hover_texts,
                hoverinfo="text",
                name=legend_name,
                showlegend=True
            ))

    def _add_edges_to_figure(
        self, 
        fig: go.Figure, 
        edges: List[Dict], 
        positions: Dict[str, Tuple[float, float]],
        show_answer_labels: bool,
        highlight_path: Optional[Dict[str, float]] = None
    ) -> None:
        """Add edges to the figure with enhanced styling."""
        
        # Add each edge as a separate trace for better color control
        for edge in edges:
            x0, y0 = positions[edge["source"]]
            x1, y1 = positions[edge["target"]]
            
            # Determine edge styling
            source_req = edge["source"]
            answer = edge["answer"]
            
            # Check if this edge is part of highlighted path
            is_highlighted = (
                highlight_path and 
                source_req in highlight_path and 
                float(highlight_path[source_req]) == float(answer)
            )
            
            if is_highlighted:
                color = "#e74c3c"  # Red for highlighted
                width = 4
            else:
                # Color based on answer value
                if answer == 1.0:
                    color = "#27ae60"  # Green for positive
                elif answer == 0.0:
                    color = "#e74c3c"  # Red for negative
                else:
                    color = "#f39c12"  # Orange for other values
                width = 2

            # Add edge as separate trace
            fig.add_trace(go.Scatter(
                x=[x0, x1],
                y=[y0, y1],
                mode="lines",
                line=dict(color=color, width=width),
                hoverinfo="none",
                showlegend=False,
                name="Dependencies"
            ))

        # Add answer labels on edges if requested
        if show_answer_labels:
            label_x = []
            label_y = []
            label_text = []
            label_colors = []
            
            for edge in edges:
                x0, y0 = positions[edge["source"]]
                x1, y1 = positions[edge["target"]]
                
                # Position label at midpoint of edge
                mid_x = (x0 + x1) / 2
                mid_y = (y0 + y1) / 2
                
                label_x.append(mid_x)
                label_y.append(mid_y)
                label_text.append(str(edge["answer"]))
                
                # Color label based on answer
                answer = edge["answer"]
                if answer == 1.0:
                    label_colors.append("#27ae60")
                elif answer == 0.0:
                    label_colors.append("#e74c3c")
                else:
                    label_colors.append("#f39c12")

            fig.add_trace(go.Scatter(
                x=label_x,
                y=label_y,
                mode="text",
                text=label_text,
                textfont=dict(size=10, color=label_colors),
                hoverinfo="none",
                showlegend=False,
                name="Answer Labels"
            ))

    def create_path_visualization(
        self, 
        answers: Dict[str, float],
        width: int = 1200,
        height: int = 800,
        show_answer_labels: bool = True,
        show_terminal_states: bool = True
    ) -> go.Figure:
        """
        Create a visualization showing a specific evaluation path through the requirements.

        Args:
            answers: Dictionary mapping requirement names to answers
            width: Graph width in pixels  
            height: Graph height in pixels
            show_answer_labels: Whether to show answer labels on edges
            show_terminal_states: Whether to emphasize terminal states

        Returns:
            Plotly Figure with highlighted path
        """
        return self.create_dependency_graph(
            width=width,
            height=height,
            show_answer_labels=show_answer_labels,
            highlight_path=answers,
            show_terminal_states=show_terminal_states
        )

    def create_metrics_dashboard(self) -> go.Figure:
        """
        Create a dashboard showing various metrics about the requirement structure.

        Returns:
            Plotly Figure with metrics visualization
        """
        metrics = self.analyze_metrics()
        
        # Create subplots for different metrics
        from plotly.subplots import make_subplots
        
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                "Requirement Types & Terminal States", 
                "Workflow Structure",
                "Dependency Distribution",
                "Terminal State Analysis"
            ),
            specs=[[{"type": "pie"}, {"type": "bar"}],
                   [{"type": "histogram"}, {"type": "bar"}]]
        )

        # 1. Requirement types and terminal states pie chart
        type_terminal_counts = {}
        for req in self.requirements:
            req_type = req.__class__.__name__.replace("Requirement", "")
            is_terminal = req.terminal()
            key = f"{req_type} ({'Terminal' if is_terminal else 'Non-Terminal'})"
            type_terminal_counts[key] = type_terminal_counts.get(key, 0) + 1
        
        fig.add_trace(
            go.Pie(
                labels=list(type_terminal_counts.keys()),
                values=list(type_terminal_counts.values()),
                name="Types & States",
                textinfo="label+percent"
            ),
            row=1, col=1
        )

        # 2. Workflow structure bar chart
        structure_stats = [
            ("Total Requirements", metrics["total_requirements"]),
            ("Terminal Nodes", metrics["terminal_nodes"]),
            ("Branching Nodes", metrics["branching_nodes"]),
            ("Multi-branch Nodes", metrics["multi_branch_nodes"]),
            ("Root Nodes", len(metrics["root_nodes"]))
        ]
        
        fig.add_trace(
            go.Bar(
                x=[s[0] for s in structure_stats],
                y=[s[1] for s in structure_stats],
                name="Structure Stats",
                marker_color=["#3498db", "#e74c3c", "#f39c12", "#27ae60", "#9b59b6"]
            ),
            row=1, col=2
        )

        # 3. Dependency distribution
        dep_counts = []
        for req in self.requirements:
            if req.dependencies:
                dep_counts.append(len(req.dependencies))
            else:
                dep_counts.append(0)
        
        fig.add_trace(
            go.Histogram(
                x=dep_counts,
                nbinsx=10,
                name="Dependencies",
                marker_color="#3498db"
            ),
            row=2, col=1
        )

        # 4. Terminal state analysis
        terminal_analysis = [
            ("Terminal by Type", len([r for r in self.requirements if r.terminal()])),
            ("Non-Terminal by Type", len([r for r in self.requirements if not r.terminal()])),
            ("Max Depth", metrics["max_depth"]),
            ("Avg Branching", f"{metrics['avg_branching_factor']:.1f}")
        ]
        
        fig.add_trace(
            go.Bar(
                x=[s[0] for s in terminal_analysis],
                y=[s[1] if isinstance(s[1], (int, float)) else 0 for s in terminal_analysis],
                name="Terminal Analysis",
                marker_color=["#e74c3c", "#3498db", "#f39c12", "#27ae60"]
            ),
            row=2, col=2
        )

        fig.update_layout(
            title={
                'text': "MultiStep Rubric Metrics Dashboard",
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 18, 'color': '#2c3e50'}
            },
            height=800,
            showlegend=False
        )

        return fig

    def create_terminal_analysis(self) -> Dict[str, Any]:
        """
        Create detailed analysis of terminal states and workflow structure.
        
        Returns:
            Dictionary with terminal state analysis
        """
        terminal_nodes = [req for req in self.requirements if req.terminal()]
        non_terminal_nodes = [req for req in self.requirements if not req.terminal()]
        
        # Analyze terminal nodes by type
        terminal_by_type = {}
        for req in terminal_nodes:
            req_type = req.__class__.__name__.replace("Requirement", "")
            terminal_by_type[req_type] = terminal_by_type.get(req_type, 0) + 1
        
        # Analyze paths to terminal nodes
        paths_to_terminal = {}
        for terminal_req in terminal_nodes:
            # Find all paths that lead to this terminal node
            paths = self._find_paths_to_node(terminal_req.name)
            paths_to_terminal[terminal_req.name] = paths
        
        return {
            "terminal_nodes": len(terminal_nodes),
            "non_terminal_nodes": len(non_terminal_nodes),
            "terminal_by_type": terminal_by_type,
            "paths_to_terminal": paths_to_terminal,
            "terminal_percentage": len(terminal_nodes) / len(self.requirements) * 100
        }
    
    def _find_paths_to_node(self, target_node: str) -> List[List[str]]:
        """Find all possible paths that lead to a specific node."""
        paths = []
        
        def dfs(current_node: str, path: List[str], visited: Set[str]):
            if current_node in visited:
                return
            
            visited.add(current_node)
            path.append(current_node)
            
            if current_node == target_node:
                paths.append(path[:])
            else:
                # Find all requirements that have this node as a dependency
                for req in self.requirements:
                    if req.dependencies:
                        for answer, deps in req.dependencies.items():
                            if current_node in deps:
                                for dep in deps:
                                    if dep not in visited:
                                        dfs(dep, path, visited)
            
            visited.remove(current_node)
            path.pop()
        
        # Start from root nodes
        metrics = self.analyze_metrics()
        root_nodes = metrics['root_nodes']
        for root in root_nodes:
            dfs(root, [], set())
        
        return paths


class RubricVisualizer(BaseRubricInspector):
    """Visualizer for complete MultiStepRubric with nodes and judge rewarders."""
    pass


class CompletedRubricVisualizer(BaseEvaluationInspector):
    """Visualizer for rubrics that have been evaluated with results."""
    pass


# Convenience functions for backward compatibility and easy usage
def visualize_requirements(requirements: List[Requirement]) -> None:
    """
    Visualize requirement dependencies and structure.

    Args:
        requirements: List of requirement objects
    """
    viz = RequirementsVisualizer(requirements)
    viz.print_dependency_graph()
    viz.print_workflow_structure()
    viz.print_metrics()


def create_dependency_graph(
    requirements: List[Requirement], 
    **kwargs
) -> go.Figure:
    """
    Create a dependency graph visualization for requirements.
    
    Args:
        requirements: List of requirement objects
        **kwargs: Additional arguments passed to create_dependency_graph
        
    Returns:
        Plotly Figure object
    """
    viz = RequirementsVisualizer(requirements)
    return viz.create_dependency_graph(**kwargs)


def create_rubric_dependency_graph(
    rubric: MultiStepRubric,
    **kwargs
) -> go.Figure:
    """
    Create a dependency graph visualization for a MultiStepRubric.
    
    Args:
        rubric: MultiStepRubric object
        **kwargs: Additional arguments passed to create_dependency_graph
        
    Returns:
        Plotly Figure object
    """
    viz = RequirementsVisualizer(list(rubric.requirements))
    return viz.create_dependency_graph(**kwargs)


def create_path_visualization(
    requirements: List[Requirement],
    answers: Dict[str, float],
    **kwargs
) -> go.Figure:
    """
    Create a path visualization showing evaluation flow through requirements.
    
    Args:
        requirements: List of requirement objects
        answers: Dictionary mapping requirement names to answers
        **kwargs: Additional arguments passed to create_path_visualization
        
    Returns:
        Plotly Figure with highlighted path
    """
    viz = RequirementsVisualizer(requirements)
    return viz.create_path_visualization(answers, **kwargs)


def create_metrics_dashboard(requirements: List[Requirement]) -> go.Figure:
    """
    Create a metrics dashboard for requirements analysis.
    
    Args:
        requirements: List of requirement objects
        
    Returns:
        Plotly Figure with metrics dashboard
    """
    viz = RequirementsVisualizer(requirements)
    return viz.create_metrics_dashboard()


def compare_requirements(
    workflow1: List[Requirement],
    workflow2: List[Requirement],
    names: Tuple[str, str] = ("Workflow 1", "Workflow 2"),
) -> None:
    """
    Compare two requirement workflows side by side.

    Args:
        workflow1: First workflow requirements
        workflow2: Second workflow requirements
        names: Names for the workflows
    """
    print(f"COMPARING REQUIREMENTS: {names[0]} vs {names[1]}")
    print("=" * 80)

    viz1 = RequirementsVisualizer(workflow1)
    viz2 = RequirementsVisualizer(workflow2)

    metrics1 = viz1.analyze_metrics()
    metrics2 = viz2.analyze_metrics()

    print(f"{'Metric':<25} {names[0]:<20} {names[1]:<20}")
    print("-" * 65)

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
        val1 = metrics1[metric]
        val2 = metrics2[metric]

        if isinstance(val1, float):
            print(f"{metric:<25} {val1:<20.2f} {val2:<20.2f}")
        else:
            print(f"{metric:<25} {val1:<20} {val2:<20}")
    print()
