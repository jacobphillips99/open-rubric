"""
Visualization utilities for MultiStep Rubric workflows.

This module provides tools to visualize workflow structures, dependencies,
and evaluation paths to help users understand complex rubrics.
"""

from typing import Any, Dict, List, Optional, Tuple

from verifiers.rubrics.multistep.requirement import Requirement
from verifiers.rubrics.multistep.utils import topological_levels


class WorkflowVisualizer:
    """Utility class for visualizing multistep workflows and their dependencies."""

    def __init__(self, requirements: List[Requirement]):
        """
        Initialize visualizer with a list of requirements.

        Args:
            requirements: List of requirement objects
        """
        self.requirements = requirements
        self.name_to_req = {req.name: req for req in requirements}

        # Build dependency structure
        self.dependencies = {
            name: sum(req.dependencies.values(), []) if req.dependencies else []
            for name, req in self.name_to_req.items()
        }

        # Get topological levels
        self.levels = topological_levels(self.dependencies)
        self.levels.reverse()  # Start from root nodes

    def print_workflow_structure(self) -> None:
        """Print a text-based visualization of the workflow structure."""
        print("WORKFLOW STRUCTURE")
        print("=" * 50)
        print(f"Total Requirements: {len(self.requirements)}")
        print(f"Levels: {len(self.levels)}")
        print()

        for level_idx, level in enumerate(self.levels):
            print(f"Level {level_idx}:")
            for req_name in level:
                req = self.name_to_req[req_name]
                status = "Terminal" if req.terminal() else "Branches"
                print(f"  • {req_name} ({status})")

                if not req.terminal():
                    if req.dependencies:  # Check if dependencies is not None
                        for answer, deps in req.dependencies.items():
                            deps_str = ", ".join(deps) if deps else "STOP"
                            print(f"    └─ If {answer}: {deps_str}")
            print()

    def print_dependency_graph(self) -> None:
        """Print the dependency relationships in graph format."""
        print("DEPENDENCY GRAPH")
        print("=" * 50)

        for req_name, req in self.name_to_req.items():
            print(f"{req_name}:")
            if req.terminal():
                print("  └─ Terminal node (no dependencies)")
            else:
                if req.dependencies:  # Check if dependencies is not None
                    for answer, deps in req.dependencies.items():
                        if deps:
                            print(f"  └─ {answer} → {', '.join(deps)}")
                        else:
                            print(f"  └─ {answer} → STOP")
            print()

    def analyze_workflow_metrics(self) -> Dict[str, Any]:
        """
        Analyze and return metrics about the workflow structure.

        Returns:
            Dict with workflow metrics
        """
        terminal_nodes = [req for req in self.requirements if req.terminal()]
        branching_nodes = [req for req in self.requirements if not req.terminal()]

        # Calculate branching factor
        total_branches = sum(
            len(req.dependencies) if req.dependencies else 0 for req in branching_nodes
        )
        avg_branching_factor = (
            total_branches / len(branching_nodes) if branching_nodes else 0
        )

        # Calculate max depth
        max_depth = len(self.levels)

        # Find nodes with most dependencies
        dependency_counts = {
            name: len(deps) for name, deps in self.dependencies.items()
        }
        max_dependencies = max(dependency_counts.values()) if dependency_counts else 0

        # Calculate connectivity
        total_edges = sum(len(deps) for deps in self.dependencies.values())

        metrics = {
            "total_requirements": len(self.requirements),
            "terminal_nodes": len(terminal_nodes),
            "branching_nodes": len(branching_nodes),
            "max_depth": max_depth,
            "avg_branching_factor": avg_branching_factor,
            "max_dependencies": max_dependencies,
            "total_edges": total_edges,
            "levels": len(self.levels),
            "terminal_node_names": [req.name for req in terminal_nodes],
            "root_nodes": self.levels[0] if self.levels else [],
        }

        return metrics

    def print_workflow_metrics(self) -> None:
        """Print analyzed workflow metrics."""
        metrics = self.analyze_workflow_metrics()

        print("WORKFLOW METRICS")
        print("=" * 50)
        print(f"Total Requirements: {metrics['total_requirements']}")
        print(f"Terminal Nodes: {metrics['terminal_nodes']}")
        print(f"Branching Nodes: {metrics['branching_nodes']}")
        print(f"Maximum Depth: {metrics['max_depth']} levels")
        print(f"Average Branching Factor: {metrics['avg_branching_factor']:.2f}")
        print(f"Total Dependency Edges: {metrics['total_edges']}")
        print()
        print(f"Root Nodes: {', '.join(metrics['root_nodes'])}")
        print(f"Terminal Nodes: {', '.join(metrics['terminal_node_names'])}")
        print()

    def trace_evaluation_path(
        self, answers: Dict[str, float]
    ) -> List[Tuple[int, List[str]]]:
        """
        Trace the evaluation path given a set of answers.

        Args:
            answers: Dictionary mapping requirement names to answers

        Returns:
            List of (level, requirements) tuples showing the evaluation path
        """
        path = []
        current_level = 0
        current_requirements = self.levels[0] if self.levels else []

        while current_requirements and current_level < len(self.levels):
            path.append((current_level, current_requirements.copy()))

            # Determine next level based on answers
            next_requirements: set[str] = set()
            for req_name in current_requirements:
                if req_name in answers:
                    req = self.name_to_req[req_name]
                    answer = answers[req_name]
                    if (
                        not req.terminal()
                        and req.dependencies
                        and answer in req.dependencies
                    ):
                        next_requirements.update(req.dependencies[answer])

            current_requirements = list(next_requirements)
            current_level += 1

        return path

    def print_evaluation_path(self, answers: Dict[str, float]) -> None:
        """
        Print the evaluation path for given answers.

        Args:
            answers: Dictionary mapping requirement names to answers
        """
        path = self.trace_evaluation_path(answers)

        print("EVALUATION PATH")
        print("=" * 50)
        print("Given answers:", answers)
        print()

        for level, requirements in path:
            print(f"Level {level}: {', '.join(requirements)}")

            # Show which answers lead to next level
            if level < len(path) - 1:
                next_level_reqs = path[level + 1][1] if level + 1 < len(path) else []
                for req_name in requirements:
                    if req_name in answers:
                        req = self.name_to_req[req_name]
                        answer = answers[req_name]
                        if (
                            not req.terminal()
                            and req.dependencies
                            and answer in req.dependencies
                        ):
                            deps = req.dependencies[answer]
                            active_deps = [d for d in deps if d in next_level_reqs]
                            if active_deps:
                                print(
                                    f"  {req_name} ({answer}) → {', '.join(active_deps)}"
                                )
        print()

    def find_possible_paths(self, max_depth: int = 10) -> List[List[str]]:
        """
        Find all possible evaluation paths through the workflow.

        Args:
            max_depth: Maximum depth to explore

        Returns:
            List of paths, where each path is a list of requirement names
        """
        paths = []

        def dfs(current_path: List[str], current_level: int):
            if current_level >= max_depth or current_level >= len(self.levels):
                paths.append(current_path.copy())
                return

            level_reqs = self.levels[current_level]
            for req_name in level_reqs:
                req = self.name_to_req[req_name]
                current_path.append(req_name)

                if req.terminal():
                    paths.append(current_path.copy())
                else:
                    # Explore all possible answers
                    if req.dependencies:  # Check if dependencies is not None
                        for _answer, deps in req.dependencies.items():
                            if deps:  # If there are dependencies, continue
                                dfs(current_path, current_level + 1)
                            else:  # If no dependencies, this is a terminal path
                                paths.append(current_path.copy())

                current_path.pop()

        if self.levels:
            dfs([], 0)

        return paths

    def print_all_possible_paths(self, max_paths: int = 20) -> None:
        """
        Print all possible evaluation paths through the workflow.

        Args:
            max_paths: Maximum number of paths to display
        """
        paths = self.find_possible_paths()

        print("ALL POSSIBLE PATHS")
        print("=" * 50)
        print(f"Total possible paths: {len(paths)}")

        if len(paths) > max_paths:
            print(f"Showing first {max_paths} paths:")
        print()

        for i, path in enumerate(paths[:max_paths]):
            print(f"Path {i + 1}: {' → '.join(path)}")

        if len(paths) > max_paths:
            print(f"... and {len(paths) - max_paths} more paths")
        print()

    def compare_workflows(self, other_visualizer: "WorkflowVisualizer") -> None:
        """
        Compare this workflow with another workflow.

        Args:
            other_visualizer: Another WorkflowVisualizer to compare against
        """
        metrics1 = self.analyze_workflow_metrics()
        metrics2 = other_visualizer.analyze_workflow_metrics()

        print("WORKFLOW COMPARISON")
        print("=" * 50)
        print(f"{'Metric':<25} {'Workflow 1':<15} {'Workflow 2':<15}")
        print("-" * 55)

        comparison_metrics = [
            "total_requirements",
            "terminal_nodes",
            "branching_nodes",
            "max_depth",
            "avg_branching_factor",
            "total_edges",
        ]

        for metric in comparison_metrics:
            val1 = metrics1[metric]
            val2 = metrics2[metric]

            if isinstance(val1, float):
                print(f"{metric:<25} {val1:<15.2f} {val2:<15.2f}")
            else:
                print(f"{metric:<25} {val1:<15} {val2:<15}")
        print()


def visualize_workflow(
    requirements: List[Requirement], answers: Optional[Dict[str, float]] = None
) -> None:
    """
    Visualize a workflow.

    Args:
        requirements: List of requirement objects
        answers: Optional answers to trace evaluation path
    """
    visualizer = WorkflowVisualizer(requirements)

    visualizer.print_workflow_structure()
    visualizer.print_workflow_metrics()

    if answers:
        visualizer.print_evaluation_path(answers)
    else:
        visualizer.print_all_possible_paths()


def compare_workflows(
    workflow1: List[Requirement],
    workflow2: List[Requirement],
    names: Tuple[str, str] = ("Workflow 1", "Workflow 2"),
) -> None:
    """
    Compare two workflows side by side.

    Args:
        workflow1: First workflow requirements
        workflow2: Second workflow requirements
        names: Names for the workflows
    """
    print(f"COMPARING: {names[0]} vs {names[1]}")
    print("=" * 60)

    viz1 = WorkflowVisualizer(workflow1)
    viz2 = WorkflowVisualizer(workflow2)

    viz1.compare_workflows(viz2)
