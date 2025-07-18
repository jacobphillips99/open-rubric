"""
Visualization utilities for MultiStep Rubric workflows.

This module provides three specialized visualizers for different use cases:
1. RequirementsVisualizer - For analyzing requirement dependencies
2. RubricVisualizer - For visualizing complete rubrics with nodes
3. CompletedRubricVisualizer - For visualizing evaluated rubrics with results
"""

from typing import Any, Dict, List, Tuple

from verifiers.rubrics.multistep.multistep_rubric import MultiStepRubric
from verifiers.rubrics.multistep.requirement import (
    Requirement, DiscreteRequirement, ContinuousRequirement
)
from verifiers.rubrics.multistep.scenario import Scenario
from verifiers.rubrics.multistep.utils import topological_levels
from verifiers.rewards.judge_utils import DiscreteJudgeResponseFormat, ContinuousJudgeResponseFormat


class RequirementsVisualizer:
    """Visualizer focused on requirement dependencies and workflow structure."""

    def __init__(self, requirements: List[Requirement]):
        """
        Initialize visualizer with a list of requirements.

        Args:
            requirements: List of requirement objects
        """
        self.requirements = requirements
        self.name_to_req = {req.name: req for req in requirements}

        # Build dependency structure for topological sorting
        self.dependencies = {
            name: sum(req.dependencies.values(), []) if req.dependencies else None
            for name, req in self.name_to_req.items()
        }

        # Get topological levels
        self.levels = topological_levels(self.dependencies)
        self.levels.reverse()  # Start from root nodes

    def print_dependency_graph(self) -> None:
        """Print the dependency relationships between requirements."""
        print("REQUIREMENT DEPENDENCIES")
        print("=" * 60)

        for req_name, req in self.name_to_req.items():
            print(f"\n{req_name}:")
            print(f"  Question: {req.question}")
            
            # Enhanced format display
            if isinstance(req.judge_response_format, DiscreteJudgeResponseFormat):
                format_info = f"Discrete: {req.judge_response_format.options}"
                if req.judge_response_format.meanings:
                    meanings = ", ".join([f"{opt}={meaning}" for opt, meaning in req.judge_response_format.meanings.items()])
                    format_info += f" ({meanings})"
            elif isinstance(req.judge_response_format, ContinuousJudgeResponseFormat):
                bounds = req.judge_response_format.options
                format_info = f"Continuous: {bounds[0]} to {bounds[1]}"
                if req.judge_response_format.meanings:
                    meanings = req.judge_response_format.meanings
                    format_info += f" ({bounds[0]}={meanings.get(bounds[0], 'low')}, {bounds[1]}={meanings.get(bounds[1], 'high')})"
            else:
                format_info = f"{req.judge_response_format.options}"
            
            print(f"  Response Format: {format_info}")

            if req.terminal():
                print("  Dependencies: Terminal node (no dependencies)")
            else:
                print("  Dependencies:")
                if req.dependencies:
                    for answer, deps in req.dependencies.items():
                        if deps:
                            if isinstance(req, ContinuousRequirement):
                                print(f"    └─ If score ≥ {answer}: {', '.join(deps)}")
                            else:
                                print(f"    └─ If answer = {answer}: {', '.join(deps)}")
                        else:
                            print(f"    └─ If answer = {answer}: STOP (terminal)")
        print()

    def print_workflow_structure(self) -> None:
        """Print a level-based view of the workflow structure."""
        print("WORKFLOW LEVELS")
        print("=" * 60)
        print(f"Total Requirements: {len(self.requirements)}")
        print(f"Levels: {len(self.levels)}")
        print()

        for level_idx, level in enumerate(self.levels):
            print(f"Level {level_idx}:")
            for req_name in level:
                req = self.name_to_req[req_name]
                status = "Terminal" if req.terminal() else "Branches"
                print(f"  • {req_name} ({status})")

                if not req.terminal() and req.dependencies:
                    for answer, deps in req.dependencies.items():
                        deps_str = ", ".join(deps) if deps else "STOP"
                        print(f"    └─ {answer} → {deps_str}")
            print()

    def analyze_metrics(self) -> Dict[str, Any]:
        """Analyze and return metrics about the requirement structure."""
        terminal_nodes = [
            name for name, req in self.name_to_req.items() if req.terminal()
        ]

        branching_nodes = []
        multi_branch_nodes = []
        for name, req in self.name_to_req.items():
            if req.dependencies:
                branching_nodes.append(name)
                if len(req.dependencies) > 2:
                    multi_branch_nodes.append(name)

        # Calculate branching factor
        total_branches = sum(
            len(req.dependencies) if req.dependencies else 0
            for req in self.requirements
        )
        avg_branching_factor = (
            total_branches / len(branching_nodes) if branching_nodes else 0.0
        )

        # Count total edges
        total_edges = sum(
            len(deps) if deps is not None else 0 for deps in self.dependencies.values()
        )

        return {
            "total_requirements": len(self.requirements),
            "terminal_nodes": len(terminal_nodes),
            "branching_nodes": len(branching_nodes),
            "multi_branch_nodes": len(multi_branch_nodes),
            "max_depth": len(self.levels),
            "avg_branching_factor": avg_branching_factor,
            "total_edges": total_edges,
            "root_nodes": list(self.levels[0]) if self.levels else [],
            "terminal_node_names": terminal_nodes,
        }

    def print_metrics(self) -> None:
        """Print analyzed workflow metrics."""
        metrics = self.analyze_metrics()

        print("WORKFLOW METRICS")
        print("=" * 60)
        print(f"Total Requirements: {metrics['total_requirements']}")
        print(
            f"Root Nodes: {len(metrics['root_nodes'])} ({', '.join(metrics['root_nodes'])})"
        )
        print(
            f"Terminal Nodes: {metrics['terminal_nodes']} ({', '.join(metrics['terminal_node_names'])})"
        )
        print(f"Branching Nodes: {metrics['branching_nodes']}")
        print(f"Multi-Branch Nodes: {metrics['multi_branch_nodes']}")
        print(f"Maximum Depth: {metrics['max_depth']} levels")
        print(f"Average Branching Factor: {metrics['avg_branching_factor']:.2f}")
        print(f"Total Dependency Edges: {metrics['total_edges']}")
        print()

    def trace_evaluation_paths(
        self, answers: Dict[str, float]
    ) -> List[Tuple[int, List[str]]]:
        """Trace the evaluation path given a set of answers."""
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
                        next_requirements.update(
                            req.get_dependencies_from_answer(answer)
                        )

            current_requirements = list(next_requirements)
            current_level += 1

        return path

    def print_evaluation_path(self, answers: Dict[str, float]) -> None:
        """Print the evaluation path for given answers."""
        path = self.trace_evaluation_paths(answers)

        print("EVALUATION PATH")
        print("=" * 60)
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
                            deps = req.get_dependencies_from_answer(answer)
                            active_deps = [d for d in deps if d in next_level_reqs]
                            if active_deps:
                                print(
                                    f"  {req_name} ({answer}) → {', '.join(active_deps)}"
                                )
        print()


class RubricVisualizer:
    """Visualizer for complete MultiStepRubric with nodes and judge rewarders."""

    def __init__(self, rubric: MultiStepRubric):
        """
        Initialize visualizer with a MultiStepRubric.

        Args:
            rubric: MultiStepRubric object to visualize
        """
        self.rubric = rubric
        self.requirements_viz = RequirementsVisualizer(list(rubric.requirements))

    def print_rubric_overview(self) -> None:
        """Print an overview of the rubric configuration."""
        print("RUBRIC OVERVIEW")
        print("=" * 60)
        print(f"Rubric Type: {type(self.rubric).__name__}")
        print(f"Judge Rewarder: {type(self.rubric.judge_rewarder).__name__}")
        print(f"Reward Strategy: {self.rubric.reward_strategy.name}")
        print(f"Total Requirements: {len(self.rubric.requirements)}")
        print(f"Total Nodes: {len(self.rubric.name_to_node)}")
        print(f"Topological Levels: {len(self.rubric.levels)}")
        print()

    def print_node_structure(self) -> None:
        """Print the node structure with their types and capabilities."""
        print("RUBRIC NODES")
        print("=" * 60)

        for level_idx, level in enumerate(self.rubric.levels):
            print(f"\nLevel {level_idx}:")
            for req_name in level:
                if req_name not in self.rubric.name_to_node:
                    breakpoint()
                node = self.rubric.name_to_node[req_name]
                req = self.rubric.name_to_req[req_name]

                print(f"  • {req_name}:")
                print(f"    Node Type: {type(node).__name__}")
                print(f"    Question: {req.question}")
                print(f"    Response Format: {req.judge_response_format.options}")
                print(f"    Terminal: {node.terminal()}")

                if not node.terminal() and req.dependencies:
                    print("    Dependencies:")
                    for answer, deps in req.dependencies.items():
                        deps_str = ", ".join(deps) if deps else "STOP"
                        print(f"      └─ {answer} → {deps_str}")
        print()

    def print_judge_configuration(self) -> None:
        """Print details about the judge rewarder configuration."""
        print("JUDGE CONFIGURATION")
        print("=" * 60)
        judge = self.rubric.judge_rewarder
        print(f"Judge Type: {type(judge).__name__}")

        # Print judge-specific attributes if available
        if hasattr(judge, "model"):
            print(f"Model: {judge.model}")
        if hasattr(judge, "client"):
            print(f"Client: {type(judge.client).__name__}")
        if hasattr(judge, "response_format"):
            print(f"Response Format: {judge.response_format}")

        print()

    def print_reward_strategy_info(self) -> None:
        """Print information about the reward calculation strategy."""
        print("REWARD STRATEGY")
        print("=" * 60)
        strategy = self.rubric.reward_strategy
        print(f"Strategy: {strategy.name}")
        print(f"Type: {type(strategy).__name__}")

        # Print strategy-specific parameters if available
        if hasattr(strategy, "base_weight"):
            print(f"Base Weight: {strategy.base_weight}")
        if hasattr(strategy, "level_multiplier"):
            print(f"Level Multiplier: {strategy.level_multiplier}")
        if hasattr(strategy, "max_level_bonus"):
            print(f"Max Level Bonus: {strategy.max_level_bonus}")

        print()

    def print_complete_structure(self) -> None:
        """Print a complete view of the rubric."""
        self.print_rubric_overview()
        self.print_judge_configuration()
        self.print_reward_strategy_info()
        self.print_node_structure()
        self.requirements_viz.print_metrics()


class CompletedRubricVisualizer:
    """Visualizer for rubrics that have been evaluated with results."""

    def __init__(self, rubric: MultiStepRubric):
        """
        Initialize visualizer with a rubric.

        Args:
            rubric: The MultiStepRubric to visualize
        """
        self.rubric = rubric
        self.rubric_viz = RubricVisualizer(rubric)

    def print_scenario_info(self, scenario: Scenario) -> None:
        """Print information about the evaluated scenario."""
        print("EVALUATED SCENARIO")
        print("=" * 60)
        print(f"Name: {scenario.name or 'Unnamed'}")
        print(f"Description: {scenario.description or 'No description'}")
        print(
            f"Prompt: {scenario.prompt[:200]}{'...' if len(scenario.prompt) > 200 else ''}"
        )
        print(
            f"Completion: {scenario.completion[:200] if scenario.completion else 'None'}{'...' if scenario.completion and len(scenario.completion) > 200 else ''}"
        )

        if scenario.answers:
            print(f"Ground Truth Answers: {len(scenario.answers)} requirements")
            for req_name, answer_data in scenario.answers.items():
                if isinstance(answer_data, dict):
                    answer = answer_data.get("answer", "N/A")
                    reasoning = answer_data.get("reasoning", "No reasoning provided")
                    print(
                        f"  • {req_name}: {answer} ({reasoning[:100]}{'...' if len(reasoning) > 100 else ''})"
                    )
                else:
                    print(f"  • {req_name}: {answer_data}")
        print()

    def print_evaluation_results(self, scenario: Scenario, results: Dict[str, Any]) -> None:
        """Print the detailed evaluation results."""
        print("EVALUATION RESULTS")
        print("=" * 60)

        total_evaluated = 0
        total_correct = 0
        for level_key, level_results in results.items():
            if level_key.isdigit():  # Only process numeric level keys
                level_num = int(level_key)
                print(f"\nLevel {level_num}:")

                for req_name, result_data in level_results.items():
                    total_evaluated += 1
                    req = self.rubric.name_to_req[req_name]

                    # Handle both dict and direct value formats
                    if isinstance(result_data, dict):
                        judge_answer = result_data.get("answer", "N/A")
                        judge_reasoning = result_data.get(
                            "reasoning", "No reasoning provided"
                        )
                    else:
                        judge_answer = result_data
                        judge_reasoning = "Direct value result"

                    # Determine correctness based on requirement type
                    if isinstance(req, DiscreteRequirement):
                        is_correct = judge_answer == 1.0
                        score_display = f"{judge_answer}"
                        if req.judge_response_format.meanings and judge_answer in req.judge_response_format.meanings:
                            meaning = req.judge_response_format.meanings[judge_answer]
                            score_display += f" ({meaning})"
                    elif isinstance(req, ContinuousRequirement):
                        # For continuous, consider >0.5 as "correct" for summary stats
                        is_correct = judge_answer > 0.5
                        bounds = req.judge_response_format.options
                        percentage = (judge_answer - bounds[0]) / (bounds[1] - bounds[0]) * 100
                        score_display = f"{judge_answer}/{bounds[1]} ({percentage:.0f}%)"
                    else:
                        # Fallback for base Requirement class
                        is_correct = judge_answer == 1.0
                        score_display = f"{judge_answer}"

                    if is_correct:
                        total_correct += 1

                    status = "✓ CORRECT" if is_correct else "✗ INCORRECT"
                    print(f"  • {req_name}: {score_display} {status}")
                    print(
                        f"    Reasoning: {judge_reasoning[:150]}{'...' if len(judge_reasoning) > 150 else ''}"
                    )

        # Summary statistics
        print("\nSUMMARY:")
        print(f"Total Evaluated: {total_evaluated}")
        print(f"Correct: {total_correct}")
        print(
            f"Accuracy: {total_correct / total_evaluated * 100:.1f}%"
            if total_evaluated > 0
            else "No evaluations"
        )
        print()

    def print_evaluation_path_taken(self, scenario: Scenario, results: Dict[str, Any]) -> None:
        """Print the actual path taken during evaluation."""
        print("EVALUATION PATH TAKEN")
        print("=" * 60)

        if not scenario.answers:
            print("No ground truth answers available to trace path.")
            return

        # Extract ground truth answers for path tracing
        gt_answers = {}
        for req_name, answer_data in scenario.answers.items():
            if isinstance(answer_data, dict):
                gt_answers[req_name] = answer_data.get("answer")
            else:
                gt_answers[req_name] = answer_data

        # Trace the path based on ground truth and judge results
        for level_key in sorted(results.keys()):
            if level_key.isdigit():
                level_num = int(level_key)
                level_results = results[level_key]
                evaluated_reqs = list(level_results.keys())

                print(f"Level {level_num}: {', '.join(evaluated_reqs)}")

                # Show what happened for each requirement
                for req_name in evaluated_reqs:
                    result_data = level_results[req_name]
                    judge_answer = (
                        result_data.get("answer", "N/A")
                        if isinstance(result_data, dict)
                        else result_data
                    )
                    gt_answer = gt_answers.get(req_name, "N/A")
                    req = self.rubric.name_to_req[req_name]

                    # Determine if this leads to next steps
                    if isinstance(req, DiscreteRequirement):
                        is_correct = judge_answer == 1.0
                    elif isinstance(req, ContinuousRequirement):
                        is_correct = judge_answer > 0.5  # Or whatever threshold makes sense
                    else:
                        is_correct = judge_answer == 1.0

                    if is_correct and not req.terminal() and req.dependencies and gt_answer in req.dependencies:
                        next_deps = req.get_dependencies_from_answer(gt_answer)
                        if next_deps:
                            print(f"  {req_name}: ✓ Correct → leads to {', '.join(next_deps)}")
                        else:
                            print(f"  {req_name}: ✓ Correct → TERMINAL")
                    elif is_correct:
                        print(f"  {req_name}: ✓ Correct → TERMINAL")
                    else:
                        print(f"  {req_name}: ✗ Incorrect → path stops here")
                print()

    def print_revealed_information(self, scenario: Scenario, results: Dict[str, Any]) -> None:
        """Print any information that was revealed during evaluation."""
        if not scenario.revealed_info:
            return

        print("REVEALED INFORMATION")
        print("=" * 60)

        for req_name, info in scenario.revealed_info.items():
            # Check if this requirement was evaluated and correct
            req_evaluated = False
            req_correct = False

            for level_results in results.values():
                if isinstance(level_results, dict) and req_name in level_results:
                    req_evaluated = True
                    result = level_results[req_name]
                    judge_answer = (
                        result.get("answer", 0.0)
                        if isinstance(result, dict)
                        else result
                    )
                    req_correct = judge_answer == 1.0
                    break

            status = ""
            if req_evaluated:
                status = (
                    " [REVEALED]"
                    if req_correct
                    else " [NOT REVEALED - incorrect answer]"
                )
            else:
                status = " [NOT EVALUATED]"

            print(f"• {req_name}{status}:")
            print(f"  {info}")
            print()

    def print_complete_evaluation(self, scenario: Scenario, results: Dict[str, Any]) -> None:
        """Print a complete view of the evaluation."""
        self.print_scenario_info(scenario)
        self.print_evaluation_results(scenario, results)
        self.print_evaluation_path_taken(scenario, results)
        self.print_revealed_information(scenario, results)


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
