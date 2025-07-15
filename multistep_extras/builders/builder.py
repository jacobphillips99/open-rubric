# TODO FIX MEEEEEEEEE.

"""
Workflow builder utilities for creating MultiStep Rubrics.

This module provides a fluent builder interface and templates to make
creating complex multistep workflows easier and more intuitive.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from verifiers.rubrics.multistep.requirement import BinaryRequirement
from verifiers.rubrics.multistep.scenario import Scenario


@dataclass
class WorkflowNode:
    """Represents a node in a workflow being built."""

    name: str
    question: str
    dependencies: Dict[float, List[str]] = field(default_factory=dict)
    is_terminal: bool = False

    def depends_on(self, condition: float, *node_names: str) -> "WorkflowNode":
        """Add dependencies for a specific condition."""
        self.dependencies[condition] = list(node_names)
        return self

    def if_yes(self, *node_names: str) -> "WorkflowNode":
        """Add dependencies for positive condition (1.0)."""
        return self.depends_on(1.0, *node_names)

    def if_no(self, *node_names: str) -> "WorkflowNode":
        """Add dependencies for negative condition (0.0)."""
        return self.depends_on(0.0, *node_names)

    def terminal(self) -> "WorkflowNode":
        """Mark this node as terminal with no dependencies."""
        self.is_terminal = True
        self.dependencies = {}
        return self


class WorkflowBuilder:
    """
    Fluent builder for creating multistep workflows.

    Example:
        builder = WorkflowBuilder()
        builder.node("check_safety", "Is the scene safe?") \
               .if_yes("assess_patient") \
               .if_no("secure_scene")

        builder.node("assess_patient", "Is patient responsive?") \
               .terminal()

        workflow = builder.build()
    """

    def __init__(self):
        """Initialize the workflow builder."""
        self.nodes: Dict[str, WorkflowNode] = {}

    def node(self, name: str, question: str) -> WorkflowNode:
        """
        Create or get a workflow node.

        Args:
            name: Unique name for the node
            question: Question to evaluate for this node

        Returns:
            WorkflowNode that can be chained with dependency methods
        """
        if name not in self.nodes:
            self.nodes[name] = WorkflowNode(name=name, question=question)
        else:
            # Update question if different
            self.nodes[name].question = question
        return self.nodes[name]

    def build(self) -> List[BinaryRequirement]:
        """
        Build the workflow into a list of BinaryRequirement objects.

        Returns:
            List of BinaryRequirement objects ready for use with MultiStepRubric
        """
        requirements = []

        for node in self.nodes.values():
            if node.is_terminal:
                req = BinaryRequirement(name=node.name, question=node.question)
            else:
                req = BinaryRequirement(
                    name=node.name,
                    question=node.question,
                    dependencies=node.dependencies if node.dependencies else None,
                )
            requirements.append(req)

        return requirements

    def validate(self) -> List[str]:
        """
        Validate the workflow and return any issues found.

        Returns:
            List of validation error messages
        """
        errors = []

        # Check for missing dependencies
        all_names = set(self.nodes.keys())
        for node in self.nodes.values():
            for deps in node.dependencies.values():
                for dep_name in deps:
                    if dep_name not in all_names:
                        errors.append(
                            f"Node '{node.name}' depends on unknown node '{dep_name}'"
                        )

        # Check for self-dependencies
        for node in self.nodes.values():
            for deps in node.dependencies.values():
                if node.name in deps:
                    errors.append(
                        f"Node '{node.name}' has circular dependency on itself"
                    )

        # Check for orphaned nodes (no incoming dependencies)
        referenced_nodes = set()
        for node in self.nodes.values():
            for deps in node.dependencies.values():
                referenced_nodes.update(deps)

        # Find root nodes (not referenced by others)
        root_nodes = all_names - referenced_nodes
        if not root_nodes:
            errors.append(
                "No root nodes found - workflow may have circular dependencies"
            )

        return errors


class WorkflowTemplate:
    """Base class for workflow templates."""

    @classmethod
    def build(cls) -> List[BinaryRequirement]:
        """Build the template workflow."""
        raise NotImplementedError


class LinearWorkflowTemplate(WorkflowTemplate):
    """
    Template for creating linear (sequential) workflows.

    Example:
        steps = [
            ("step1", "First step question"),
            ("step2", "Second step question"),
            ("step3", "Third step question")
        ]
        workflow = LinearWorkflowTemplate.build_from_steps(steps)
    """

    @classmethod
    def build_from_steps(cls, steps: List[tuple[str, str]]) -> List[BinaryRequirement]:
        """
        Build a linear workflow from a list of steps.

        Args:
            steps: List of (name, question) tuples

        Returns:
            List of BinaryRequirement objects
        """
        builder = WorkflowBuilder()

        for i, (name, question) in enumerate(steps):
            if i == len(steps) - 1:
                # Last step is terminal
                builder.node(name, question).terminal()
            else:
                # Link to next step on success
                next_name = steps[i + 1][0]
                builder.node(name, question).if_yes(next_name)

        return builder.build()


class BranchingWorkflowTemplate(WorkflowTemplate):
    """
    Template for creating branching decision tree workflows.

    Example:
        tree = {
            "root": {
                "question": "Root decision?",
                "yes": ["branch1", "branch2"],
                "no": ["branch3"]
            },
            "branch1": {
                "question": "Branch 1 question?",
                "terminal": True
            }
        }
        workflow = BranchingWorkflowTemplate.build_from_tree(tree)
    """

    @classmethod
    def build_from_tree(
        cls, tree: Dict[str, Dict[str, Any]]
    ) -> List[BinaryRequirement]:
        """
        Build a branching workflow from a tree structure.

        Args:
            tree: Dictionary defining the tree structure

        Returns:
            List of BinaryRequirement objects
        """
        builder = WorkflowBuilder()

        for name, config in tree.items():
            question = config["question"]
            node = builder.node(name, question)

            if config.get("terminal", False):
                node.terminal()
            else:
                if "yes" in config:
                    node.if_yes(*config["yes"])
                if "no" in config:
                    node.if_no(*config["no"])

        return builder.build()


class ScenarioBuilder:
    """
    Builder for creating test scenarios.

    Example:
        scenario = ScenarioBuilder() \
            .prompt("What should we do?") \
            .completion("We should do X, Y, and Z") \
            .answer("step1", 1.0, "Clearly addresses step 1") \
            .answer("step2", 0.0, "Does not address step 2") \
            .build()
    """

    def __init__(self):
        """Initialize the scenario builder."""
        self._prompt: Optional[str] = None
        self._completion: Optional[str] = None
        self._answers: dict[str, float] = {}
        self._name: Optional[str] = None
        self._description: Optional[str] = None

    def prompt(self, text: str) -> "ScenarioBuilder":
        """Set the scenario prompt."""
        self._prompt = text
        return self

    def completion(self, text: str) -> "ScenarioBuilder":
        """Set the scenario completion."""
        self._completion = text
        return self

    def answer(self, requirement: str, value: float) -> "ScenarioBuilder":
        """Add an answer for a requirement."""
        self._answers[requirement] = value
        return self

    def name(self, text: str) -> "ScenarioBuilder":
        """Set the scenario name."""
        self._name = text
        return self

    def description(self, text: str) -> "ScenarioBuilder":
        """Set the scenario description."""
        self._description = text
        return self

    def build(self) -> Scenario:
        """Build the scenario."""
        if not self._prompt:
            raise ValueError("Scenario prompt is required")

        return Scenario(
            prompt=self._prompt,
            completion=self._completion,
            answers=self._answers,
            name=self._name,
            description=self._description,
        )


def quick_workflow(*steps: str) -> List[BinaryRequirement]:
    """
    Quickly create a linear workflow from step names.

    Args:
        *steps: Step names (questions will be auto-generated)

    Returns:
        List of BinaryRequirement objects

    Example:
        workflow = quick_workflow("check_safety", "assess_patient", "provide_care")
    """
    step_tuples = [
        (step, f"Does the response consider {step.replace('_', ' ')}?")
        for step in steps
    ]
    return LinearWorkflowTemplate.build_from_steps(step_tuples)


def quick_scenario(prompt: str, completion: str, **answers: float) -> Scenario:
    """
    Quickly create a scenario with simple answers.

    Args:
        prompt: Scenario prompt
        completion: Scenario completion
        **answers: Keyword arguments mapping requirement names to answer values

    Returns:
        Scenario object

    Example:
        scenario = quick_scenario(
            "What should we do?",
            "We should check safety first",
            check_safety=1.0,
            assess_patient=0.0
        )
    """
    return Scenario(prompt=prompt, completion=completion, answers=answers)
