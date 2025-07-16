"""MultiStep rubric implementation for evaluating requirements with dependencies."""

import asyncio
from collections import defaultdict
from collections.abc import Sequence
from copy import deepcopy
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple, Union

from verifiers.rewards.judge_reward import JudgeRewarder
from verifiers.rubrics.multistep.enums import EvaluationMode, TerminalCondition
from verifiers.rubrics.multistep.nodes import RequirementRewardNode
from verifiers.rubrics.multistep.requirement import Requirement
from verifiers.rubrics.multistep.results import EvaluationResult
from verifiers.rubrics.multistep.reward_strategies import (
    LevelWeightedRewardStrategy, RewardStrategy)
from verifiers.rubrics.multistep.scenario import Scenario
from verifiers.rubrics.multistep.utils import topological_levels
from verifiers.rubrics.rubric import Rubric


class MultiStepRubric(Rubric):
    """
    Rubric that evaluates requirements with dependencies using different traversal modes.

    Supports evaluation modes including adaptive evaluation that stops gracefully
    when no valid path forward exists.
    """

    def __init__(
        self,
        requirements: Sequence[Requirement],
        judge_rewarder: JudgeRewarder,
        node_factory: Callable = RequirementRewardNode,
        reward_strategy: Optional[RewardStrategy] = None,
    ):
        """
        Initialize MultiStepRubric.

        Args:
            requirements: List of requirement objects with name, dependencies, etc.
            judge_rewarder: Rewarder for evaluating requirements
            node_factory: Optional factory function to create custom nodes
            reward_strategy: Strategy for calculating rewards from evaluation results
        """
        self.requirements = requirements
        self.judge_rewarder = judge_rewarder
        self.reward_strategy = reward_strategy or LevelWeightedRewardStrategy()

        # Build lookup structures
        self.name_to_req = {req.name: req for req in requirements}

        # Use custom node factory if provided, otherwise use default
        self.name_to_node = {
            name: node_factory(req, judge_rewarder)
            for name, req in self.name_to_req.items()
        }

        # Build dependency structure for topological sorting
        self.name_to_dependency_options: Dict[str, Optional[List[str]]] = {
            name: sum(req.dependencies.values(), []) if req.dependencies else None
            for name, req in self.name_to_req.items()
        }

        # Get topological levels (reversed to start from root nodes)
        self.levels = topological_levels(self.name_to_dependency_options)
        self.levels.reverse()

    def validate(
        self, scenario: Scenario, mode: Optional[EvaluationMode] = None, **kwargs
    ) -> None:
        """
        Validate that the scenario is compatible with this rubric's requirements.

        Args:
            scenario: The scenario to validate
            mode: The evaluation mode (for mode-specific validation)
            **kwargs: Additional arguments that may contain ground_truth_answers

        Raises:
            ValueError: If validation fails
        """
        # Mode-specific validation first
        if mode == EvaluationMode.REFERENCE_GUIDED:
            if not scenario.answers:
                raise ValueError(
                    "scenario.answers is required for REFERENCE_GUIDED mode"
                )

        # Only validate answers when they exist and are not None
        if scenario.answers:
            self._validate_answers(scenario.answers)

    def _validate_answers(self, answers: Mapping[str, Any]) -> None:
        """
        Validate answer structure and values.

        Args:
            answers: Dictionary of answers to validate

        Raises:
            ValueError: If validation fails
        """
        # Check for unknown requirements
        unknown_requirements = set(answers.keys()) - set(self.name_to_req.keys())
        if unknown_requirements:
            raise ValueError(
                f"Scenario contains answers for unknown requirements: {unknown_requirements}"
            )

        # Check individual answer entries
        for req_name, answer_data in answers.items():
            # Skip validation if answer_data is None
            if answer_data is None:
                continue

            requirement = self.name_to_req[req_name]
            valid_options = requirement.judge_response_format.options

            # Handle different answer formats
            if isinstance(answer_data, dict):
                # New format: {"answer": value, "reason": "..."}
                if "answer" not in answer_data:
                    continue  # Skip if no answer field present
                answer_value = answer_data["answer"]
            else:
                # Old format: direct value
                answer_value = answer_data

            # Skip validation if answer_value is None
            if answer_value is None:
                continue

            # Validate the answer value
            if answer_value not in valid_options:
                raise ValueError(
                    f"Invalid answer value {answer_value} for requirement '{req_name}'. "
                    f"Valid options are: {valid_options}"
                )

    async def evaluate_adaptive(
        self, scenario: Scenario, max_depth: int = 10, **kwargs
    ) -> EvaluationResult:
        """
        Adaptive evaluation that stops gracefully when no valid path forward exists.
        Returns detailed results including terminal condition and completion status.
        """
        state: Dict[int, Dict[str, Any]] = defaultdict(dict)
        completed_requirements = set()
        i = 0
        level = self.levels[0] if self.levels else []

        while level and i < max_depth:
            print(f"Evaluating level {i}: {level}")
            nodes = [self.name_to_node[name] for name in level]

            # Evaluate all nodes in this level
            level_results = {}

            for name, node in zip(level, nodes):
                try:
                    result = await node(scenario, **kwargs)
                    level_results[name] = result
                    completed_requirements.add(name)
                except Exception as e:
                    print(f"Error evaluating {name}: {e}")
                    level_results[name] = 0.0

            state[i] = level_results

            # Determine next level - only proceed if we have valid paths
            next_level = []

            for name, result in level_results.items():
                node = self.name_to_node[name]
                if not node.requirement.terminal():
                    # Check if we have a valid result that maps to dependencies
                    if (
                        isinstance(result, (int, float))
                        and result in node.requirement.dependencies
                    ):
                        next_level.extend(node.requirement.dependencies[result])

            # Stop if no valid path forward
            if not next_level:
                terminal_condition = (
                    TerminalCondition.NO_VALID_PATH
                    if i > 0
                    else TerminalCondition.COMPLETED
                )
                return EvaluationResult(
                    {str(k): v for k, v in state.items()},  # Convert int keys to string
                    terminal_condition,
                    completed_requirements,
                    len(self.requirements),
                )

            level = list(set(next_level))
            i += 1

        # Determine terminal condition
        if i >= max_depth:
            terminal_condition = TerminalCondition.MAX_DEPTH_REACHED
        else:
            terminal_condition = TerminalCondition.COMPLETED

        return EvaluationResult(
            {str(k): v for k, v in state.items()},  # Convert int keys to string
            terminal_condition,
            completed_requirements,
            len(self.requirements),
        )

    async def evaluate_model_guided(
        self, scenario: Scenario, start_level_idx: int = 0, **kwargs
    ) -> Dict[str, Any]:
        """
        Follow the model's answers through the dependency graph.
        Simulates the actual workflow path the model would take.
        """
        state: Dict[int, Dict[str, Any]] = defaultdict(dict)
        i = start_level_idx
        level = (
            self.levels[start_level_idx] if start_level_idx < len(self.levels) else []
        )

        while level:
            print(f"Evaluating level {i}: {level}")
            nodes = [self.name_to_node[name] for name in level]

            # Evaluate all nodes in this level
            coros = [node(scenario, **kwargs) for node in nodes]
            level_answers = dict(zip(level, await asyncio.gather(*coros)))
            state[i] = level_answers

            # Determine next level based on model's answers
            next_level = []
            for name, model_answer in level_answers.items():
                node = self.name_to_node[name]
                if (
                    not node.requirement.terminal()
                    and model_answer in node.requirement.dependencies
                ):
                    next_level.extend(node.requirement.dependencies[model_answer])

            level = list(set(next_level))
            i += 1

        return {str(k): v for k, v in state.items()}  # Convert int keys to string

    async def evaluate_reference_guided(
        self, scenario: Scenario, ground_truth_answers: Dict[str, float], **kwargs
    ) -> Dict[str, Any]:
        """
        Follow the ground truth answers through the dependency graph.
        Evaluates model performance on the "correct" workflow path.
        """
        state: Dict[int, Dict[str, Any]] = defaultdict(dict)
        i = 0
        level = self.levels[0] if self.levels else []

        while level:
            print(f"Evaluating reference level {i}: {level}")

            # Only evaluate requirements that have ground truth answers
            level_with_answers = [
                name for name in level if name in ground_truth_answers
            ]

            if not level_with_answers:
                break  # No requirements to evaluate at this level

            nodes = [self.name_to_node[name] for name in level_with_answers]

            # Evaluate model on this level
            coros = [node(scenario, **kwargs) for node in nodes]
            level_scores = dict(zip(level_with_answers, await asyncio.gather(*coros)))
            state[i] = level_scores

            # Determine next level based on ground truth answers
            next_level = []
            for name in level_with_answers:
                node = self.name_to_node[name]
                gt_answer = ground_truth_answers[name]
                if (
                    not node.requirement.terminal()
                    and gt_answer in node.requirement.dependencies
                ):
                    next_level.extend(node.requirement.dependencies[gt_answer])

            level = list(set(next_level))
            i += 1

            print(f"level {i} scores: {level_scores}")

        return {str(k): v for k, v in state.items()}  # Convert int keys to string

    async def evaluate_exhaustive(
        self, scenario: Scenario, **kwargs
    ) -> Dict[str, float]:
        """
        Evaluate all requirements regardless of dependencies.
        Provides comprehensive capability assessment.
        """
        all_nodes = list(self.name_to_node.values())

        # Evaluate all nodes in parallel
        coros = [node(scenario, **kwargs) for node in all_nodes]
        all_scores = await asyncio.gather(*coros)

        return {node.name: score for node, score in zip(all_nodes, all_scores)}

    async def evaluate(
        self,
        scenario: Scenario,
        mode: EvaluationMode = EvaluationMode.MODEL_GUIDED,
        **kwargs,
    ) -> Union[Dict[str, Any], EvaluationResult]:
        """Dispatch evaluation to appropriate mode based on evaluation mode."""
        self.validate(scenario, mode, **kwargs)  # Validate scenario before evaluation
        if mode == EvaluationMode.MODEL_GUIDED:
            return await self.evaluate_model_guided(scenario, **kwargs)
        elif mode == EvaluationMode.REFERENCE_GUIDED:
            if "ground_truth_answers" not in kwargs:
                # Convert scenario.answers to ground_truth_answers format
                ground_truth_answers: Dict[str, float] = {}
                if scenario.answers:
                    for req_name, answer_data in scenario.answers.items():
                        # Skip None answers
                        if answer_data is None:
                            continue
                        if isinstance(answer_data, dict) and "answer" in answer_data:
                            answer_value = answer_data["answer"]
                            # Only include non-None answer values that are numeric
                            if answer_value is not None and isinstance(
                                answer_value, (int, float)
                            ):
                                ground_truth_answers[req_name] = float(answer_value)
                        elif answer_data is not None and isinstance(
                            answer_data, (int, float)
                        ):
                            # Old format: direct value, only if not None and numeric
                            ground_truth_answers[req_name] = float(answer_data)
            else:
                ground_truth_answers = kwargs.pop("ground_truth_answers")
            return await self.evaluate_reference_guided(
                scenario, ground_truth_answers, **kwargs
            )
        elif mode == EvaluationMode.EXHAUSTIVE:
            return await self.evaluate_exhaustive(scenario, **kwargs)
        elif mode == EvaluationMode.ADAPTIVE:
            return await self.evaluate_adaptive(scenario, **kwargs)
        else:
            raise ValueError(f"Unknown evaluation mode: {mode}")

    async def score_rollout(
        self,
        prompt: Union[str, List[Dict[str, Any]]],
        completion: Union[str, List[Dict[str, Any]]],
        answer: Any,
        state: Dict[str, Any],
        task: str = "default",
        info: Optional[dict] = None,
        mode: EvaluationMode = EvaluationMode.REFERENCE_GUIDED,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Enhanced score_rollout that can handle different evaluation modes and terminal conditions.
        Uses configurable reward strategy for flexible reward calculation.
        """
        if info is None:
            info = {}

        # Convert prompt and completion to string format for Scenario constructor
        prompt_str = prompt if isinstance(prompt, str) else str(prompt)
        completion_str = completion if isinstance(completion, str) else str(completion)

        # Create a Scenario object from the individual parameters
        scenario = Scenario(
            prompt=prompt_str, completion=completion_str, answers=answer
        )
        result = await self.evaluate(scenario, mode=mode, **kwargs)

        # Calculate reward using the configured strategy
        reward_kwargs = {"total_requirements": len(self.requirements), **kwargs}
        reward = self.reward_strategy.calculate_reward(result, mode, **reward_kwargs)

        if isinstance(result, EvaluationResult):
            # Adaptive evaluation
            return {
                **result.to_dict(),
                "reward": reward,
                "reward_strategy": self.reward_strategy.name,
                "mode": mode.value,
            }
        else:
            # Traditional evaluation modes
            return {
                "state": result,
                "reward": reward,
                "reward_strategy": self.reward_strategy.name,
                "mode": mode.value,
                "terminal_condition": TerminalCondition.COMPLETED.value,
            }

    def get_next_conversation_step(
        self,
        messages: List[Dict[str, Any]],
        state: Dict[str, Any],
        **kwargs
    ) -> Tuple[Optional[str], Dict[str, Any], bool]:
        """
        Determine the next step in the conversation workflow.

        Args:
            messages: List of conversation messages so far
            state: Current conversation state containing workflow progress
            **kwargs: Additional arguments

        Returns:
            Tuple of (next_message_content, updated_state, is_finished)
        """
        if not messages:
            raise ValueError("messages should contain at least the initial user prompt")

        # Extract the conversation parts
        initial_user_prompt = messages[0]["content"]
        last_assistant_msg = ""
        for m in reversed(messages):
            if m["role"] == "assistant":
                last_assistant_msg = m["content"]
                break

        # Get workflow tracking data from state
        level_idx = state["level_idx"]
        active_reqs = state["active_reqs"]
        raw_answers_gt = state["answers_gt"]
        revealed_info_set = state.get("revealed_info", set())
        revealed_info_data = state.get("revealed_info_data", {})

        # Flatten scenario answer dicts so each value is a scalar (e.g., 1.0)
        answers_gt = {k: (v["answer"] if isinstance(v, dict) else v) for k, v in raw_answers_gt.items()}

        # Build scenario for evaluation
        tmp_scenario = Scenario(prompt=initial_user_prompt, completion=last_assistant_msg, answers=answers_gt)

        # Use synchronous wrapper to handle nested event loops
        try:
            # Try to get the current event loop
            asyncio.get_running_loop()
            # We're in an async context, so we need to handle this differently
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    self.evaluate_reference_guided(tmp_scenario, ground_truth_answers=answers_gt)
                )
                eval_state = future.result()
        except RuntimeError:
            # No event loop running, safe to use asyncio.run
            eval_state = asyncio.run(
                self.evaluate_reference_guided(tmp_scenario, ground_truth_answers=answers_gt)
            )

        # Extract model scores for this level
        level_scores: Dict[str, float] = eval_state.get(level_idx, {}) if isinstance(eval_state, dict) else {}

        # Determine next requirements based on dependency map and the ground truth answers
        next_reqs: List[str] = []
        for req_name, score in level_scores.items():
            req = self.name_to_req[req_name]
            if not req.terminal() and req.dependencies is not None and score in req.dependencies:
                next_reqs.extend(req.dependencies[score])

        next_reqs = list(set(next_reqs))

        # Collect revealed information from just-satisfied requirements
        revealed_info_lines = []

        # Process revealed information based on current level scores
        if revealed_info_data:
            for req_name, score in level_scores.items():
                if req_name in revealed_info_data:
                    score_key = str(float(score))
                    if score_key in revealed_info_data[req_name]:
                        info_key = f"{req_name}_{score_key}"
                        if info_key not in revealed_info_set:
                            revealed_info_lines.append(f"📋 New Information: {revealed_info_data[req_name][score_key]}")
                            revealed_info_set.add(info_key)

        # Craft environment message with revealed information and follow-up questions
        content_lines = []

        # Add any revealed information first
        if revealed_info_lines:
            content_lines.extend(revealed_info_lines)
            content_lines.append("")  # Add blank line for separation

        if next_reqs:
            for r in next_reqs:
                req = self.name_to_req[r]
                # Provide any prior reasoning we have about this requirement
                reasoning = ""
                if isinstance(answers_gt.get(r), dict):
                    reasoning = answers_gt[r].get("reasoning", "")
                if reasoning:
                    content_lines.append(f"Background ({r}): {reasoning}")
                content_lines.append(f"Question ({r}): {req.question}")
            content = "\n".join(content_lines)
        else:
            if content_lines:
                content = "\n".join(content_lines + ["No further information is available. You may conclude."])
            else:
                content = "No further information is available. You may conclude."

        # Update state
        updated_state = deepcopy(state)
        if not next_reqs:
            updated_state["finished"] = True
        else:
            updated_state["level_idx"] = level_idx + 1
            updated_state["active_reqs"] = next_reqs

        # Update revealed information in state
        updated_state["revealed_info"] = revealed_info_set

        is_finished = not next_reqs
        return content, updated_state, is_finished
