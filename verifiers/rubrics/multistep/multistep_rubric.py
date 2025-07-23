"""MultiStep rubric implementation for evaluating requirements in a dependency graph in both single-turn and multi-turn environments."""

import asyncio
from collections import defaultdict
from collections.abc import Sequence
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple, Union

import yaml

from verifiers.rewards.judge_reward import (JudgeResponse, JudgeRewarder,
                                            detect_client_type,
                                            make_judge_rewarders)
from verifiers.rubrics.multistep.enums import EvaluationMode, TerminalCondition
from verifiers.rubrics.multistep.nodes import (NodeFactory,
                                               RequirementRewardNode)
from verifiers.rubrics.multistep.requirement import Requirement
from verifiers.rubrics.multistep.reward_strategies import (
    LevelWeightedRewardStrategy, RewardStrategy, make_reward_strategy)
from verifiers.rubrics.multistep.scenario import Scenario
from verifiers.rubrics.multistep.utils import topological_levels
from verifiers.rubrics.rubric import Rubric


class MultiStepRubric(Rubric):
    """
    Rubric that evaluates requirements with dependencies in both single-turn and multi-turn environments.

    The policy model provides responses which are evaluated by a judge against ground truth answers.
    The judge's determination of correctness drives workflow progression:
    - Correct answers continue down the dependency path and may reveal information
    - Incorrect answers stop that branch immediately
    - Rewards are calculated per requirement based on judge evaluation

    The MultiStepRubric organizes requirements into a dependency graph where each requirement can have
    conditional dependencies on the outcomes of other requirements. This enables complex, branching
    evaluation workflows that adapt based on judge-determined correctness.

    ## Usage Patterns

    ### Single-Turn Environment
    In the single-turn environment, the rubric evaluates requirements against the final response:
    - Judge evaluates model response against ground truth for each requirement
    - Dependencies determine evaluation path based on ground truth answers (when judge says correct)
    - Results provide assessment based on judge-determined correctness

    ### Multi-Turn Environment
    In the multi-turn environment, the rubric drives an interactive conversation workflow:
    - Requirements are evaluated incrementally as the conversation progresses
    - Judge determines if model responses align with ground truth
    - Only correct judge evaluations trigger information revelation and path continuation
    - The rubric advances through dependency levels based on judge-approved correct answers

    ## Key Features
    - Judge-driven evaluation against ground truth answers
    - Progressive information revelation only on correct judge evaluations
    - Flexible reward strategies for different evaluation objectives
    - Robust handling of missing dependencies and evaluation errors
    """

    def __init__(
        self,
        requirements: Sequence[Requirement],
        judge_options: list[JudgeRewarder],
        reward_strategy: Optional[RewardStrategy] = None,
    ):
        """
        Initialize MultiStepRubric.

        Args:
            requirements: List of requirement objects with name, dependencies, etc.
            judge_options: List of judge rewarders for evaluating requirements
            reward_strategy: Strategy for calculating rewards from evaluation results
        """
        self.requirements = requirements
        self.judge_options = judge_options
        self.reward_strategy = reward_strategy or LevelWeightedRewardStrategy()

        # Build lookup structures
        self.name_to_req = {req.name: req for req in requirements}

        # Use custom node factory if provided, otherwise use default
        self.name_to_node: Dict[str, RequirementRewardNode] = {
            name: NodeFactory.create_node(req, judge_options)
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

    async def evaluate(
        self,
        scenario: Scenario,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Evaluate the scenario using judge-driven workflow progression.

        The judge evaluates the model's response against ground truth answers.
        Only when the judge determines correctness do we follow dependency paths.

        Args:
            scenario: The scenario to evaluate
            ground_truth_answers: Optional ground truth answers (uses scenario.answers if not provided)
            **kwargs: Additional arguments for evaluation

        Returns:
            Dictionary containing evaluation results by level
        """
        if not scenario.answers:
            raise ValueError(
                "ground_truth_answers or scenario.answers required for evaluation"
            )

        # Convert scenario.answers to ground_truth_answers format
        ground_truth_answers = {}
        for req_name, answer_data in scenario.answers.items():
            # Skip None answers and metadata keys (starting with underscore)
            if answer_data is None or req_name.startswith("_"):
                continue
            maybe_answer = answer_data.get("answer", answer_data)
            if isinstance(maybe_answer, (int, float)):
                ground_truth_answers[req_name] = float(maybe_answer)
            else:
                raise ValueError(f"Invalid answer format for {req_name}: {answer_data}")

        state: Dict[int, Dict[str, Any]] = defaultdict(dict)
        i = 0
        level = self.levels[0] if self.levels else []

        while level:
            print(f"Evaluating level {i}: {level}")

            # Only evaluate requirements that have ground truth answers
            level_with_answers = [
                name for name in level if name in ground_truth_answers
            ]

            if not level_with_answers:
                break  # No requirements to evaluate at this level

            nodes = [self.name_to_node[name] for name in level_with_answers]

            # Evaluate model response with judge for each requirement
            coros = [node(scenario, **kwargs) for node in nodes]
            judge_results: Dict[str, JudgeResponse] = dict(
                zip(level_with_answers, await asyncio.gather(*coros))
            )

            # Store both answer and reasoning in state
            state[i] = {
                name: result.to_dict() for name, result in judge_results.items()
            }

            # Determine next level based on ground truth answers where judge said correct
            next_level = []
            for name in level_with_answers:
                node = self.name_to_node[name]
                gt_answer = ground_truth_answers[name]

                # Only follow dependencies if judge determined the response was correct
                # Judge answer of 1.0 means correct, anything else means incorrect
                if (
                    judge_results[name].answer == 1.0
                    and not node.terminal()
                    and node.dependencies
                    and gt_answer in node.dependencies
                ):
                    # Follow the dependency path for the ground truth answer
                    next_level.extend(
                        node.requirement.get_dependencies_from_answer(gt_answer)
                    )

            level = list(set(next_level))
            i += 1

            print(f"level {i} judge results: {judge_results}")

        return {str(k): v for k, v in state.items()}  # Convert int keys to string

    def validate(self, scenario: Scenario, **kwargs) -> None:
        """
        Validate that the scenario is compatible with this rubric's requirements.

        Args:
            scenario: The scenario to validate
            **kwargs: Additional arguments that may contain ground_truth_answers

        Raises:
            ValueError: If validation fails
        """
        # Require ground truth answers for evaluation
        if not scenario.answers:
            raise ValueError(
                "scenario.answers is required for MultiStepRubric evaluation"
            )

        # Validate answers when they exist and are not None
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

    async def score_rollout(
        self,
        prompt: Union[str, List[Dict[str, Any]]],
        completion: Union[str, List[Dict[str, Any]]],
        answer: Any,
        state: Dict[str, Any],
        task: str = "default",
        info: Optional[dict] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Score a rollout using judge-driven evaluation strategy.
        Uses configurable reward strategy for flexible reward calculation.
        """
        if info is None:
            info = {}

        # Check if we have evaluation results from conversation flow
        if "evaluation_results" in state and state["evaluation_results"]:
            # Use the evaluation results that were built during the conversation
            evaluation_results = state["evaluation_results"]
        else:
            # Fallback to direct evaluation for single-turn scenarios
            # Convert prompt and completion to string format for Scenario constructor
            prompt_str = prompt if isinstance(prompt, str) else str(prompt)
            completion_str = (
                completion if isinstance(completion, str) else str(completion)
            )

            # Create a Scenario object from the individual parameters
            scenario = Scenario(
                prompt=prompt_str, completion=completion_str, answers=answer
            )
            evaluation_results = await self.evaluate(scenario, **kwargs)

        # Calculate reward using the configured strategy
        reward_kwargs = {"total_requirements": len(self.requirements), **kwargs}
        reward = self.reward_strategy.calculate_reward(
            evaluation_results, EvaluationMode.MODEL_GUIDED, **reward_kwargs
        )

        # Return reward info with the full original state preserved
        return {
            "state": state,  # Return the full original state, don't modify it
            "reward": reward,
            "reward_strategy": self.reward_strategy.name,
            "mode": EvaluationMode.MODEL_GUIDED.value,
            "terminal_condition": TerminalCondition.COMPLETED.value,
        }

    def get_next_conversation_step(
        self, messages: List[Dict[str, Any]], state: Dict[str, Any], **kwargs
    ) -> Tuple[Optional[str], Dict[str, Any], bool]:
        """
        Determine the next step in the conversation workflow using incremental evaluation.
        Continues evaluating until new information is found or workflow is finished.

        The judge evaluates model responses against ground truth. Only correct judge
        evaluations trigger information revelation and dependency progression.

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
        answers_gt = {
            k: (v["answer"] if isinstance(v, dict) else v)
            for k, v in raw_answers_gt.items()
        }

        # Build scenario for evaluation
        tmp_scenario = Scenario(
            prompt=initial_user_prompt,
            completion=last_assistant_msg,
            answers=answers_gt,
        )

        # Initialize state tracking
        updated_state = deepcopy(state)
        revealed_info_set = state.get("revealed_info", set())

        # Process any pending requirements from previous turn
        pending_next_reqs = updated_state.get("_pending_next_reqs", [])
        if pending_next_reqs:
            # Use pending requirements and advance level
            updated_state["level_idx"] = level_idx + 1
            updated_state["active_reqs"] = pending_next_reqs
            updated_state.pop("_pending_next_reqs", None)
            # No evaluation needed this turn, just advance
            return None, updated_state, False

        # Evaluate current active requirements once
        current_level_results: Dict[str, JudgeResponse] = {}
        if active_reqs:
            try:
                # Evaluate only requirements that have ground truth answers
                for req_name in active_reqs:
                    if req_name in self.name_to_node and req_name in answers_gt:
                        node = self.name_to_node[req_name]
                        # Use synchronous wrapper to handle nested event loops
                        try:
                            asyncio.get_running_loop()
                            # We're in an async context, use thread executor
                            import concurrent.futures

                            with concurrent.futures.ThreadPoolExecutor() as executor:
                                future = executor.submit(
                                    asyncio.run, node(tmp_scenario)
                                )
                                result = future.result()
                        except RuntimeError:
                            # No event loop running, safe to use asyncio.run
                            result = asyncio.run(node(tmp_scenario))

                        current_level_results[req_name] = result
                    elif req_name not in answers_gt:
                        print(
                            f"Warning: No answer provided for requirement '{req_name}', skipping evaluation"
                        )
            except Exception as e:
                print(f"Error evaluating requirements {active_reqs}: {e}")
                # Fallback to empty results if evaluation fails
                current_level_results = {}

        # Check for revealed information from current level results
        # Only reveal info when judge determined the response was correct (answer == 1.0)
        revealed_info_content = []
        new_info_found = False

        if revealed_info_data and current_level_results:
            for req_name, judge_result in current_level_results.items():
                # Only proceed if judge determined the response was correct
                if judge_result.answer == 1.0 and req_name in revealed_info_data:
                    info_key = req_name
                    if info_key not in revealed_info_set:
                        # Add the revealed information
                        revealed_info_content.append(revealed_info_data[req_name])
                        revealed_info_set.add(info_key)
                        new_info_found = True

        # Determine next requirements based on current level results
        # Only follow dependencies where judge determined correctness (answer == 1.0)
        next_reqs: List[str] = []
        for req_name, judge_result in current_level_results.items():
            req = self.name_to_req[req_name]
            gt_answer = answers_gt.get(req_name)

            # Only follow dependencies if judge says correct AND we have valid ground truth
            if (
                judge_result.answer == 1.0  # Judge determined response was correct
                and not req.terminal()
                and req.dependencies is not None
                and gt_answer is not None
                and gt_answer in req.dependencies
            ):
                next_reqs.extend(req.get_dependencies_from_answer(gt_answer))

        next_reqs = list(set(next_reqs))

        # Update state with revealed info and evaluation results for testing/debugging
        updated_state["revealed_info"] = revealed_info_set
        updated_state["last_evaluation_results"] = {
            name: result.to_dict() for name, result in current_level_results.items()
        }

        # Accumulate evaluation results in level-based format for test compatibility
        if current_level_results:
            evaluation_results = updated_state.get("evaluation_results", {})
            level_key = str(level_idx)
            evaluation_results[level_key] = {
                name: result.to_dict() for name, result in current_level_results.items()
            }
            updated_state["evaluation_results"] = evaluation_results

        # If we found new information, return it
        if new_info_found:
            content = "\n".join(revealed_info_content)

            if next_reqs:
                # Prepare next requirements for the subsequent turn
                updated_state["_pending_next_reqs"] = next_reqs
                return content, updated_state, False
            else:
                # No next requirements - conversation is ending
                updated_state["finished"] = True
                return content, updated_state, True

        # No new information found - check if we can advance directly
        if next_reqs:
            # Advance to next level with new requirements
            updated_state["level_idx"] = level_idx + 1
            updated_state["active_reqs"] = next_reqs
            # Continue conversation without explicit environment message
            return None, updated_state, False
        else:
            # No more requirements - conversation is finished
            updated_state["finished"] = True
            return None, updated_state, True

    def save(
        self,
        directory: Union[str, Path],
        name: str = "rubric",
    ) -> None:
        """
        Save this MultiStepRubric to a directory with separate files.

        Args:
            directory: Directory to save files in
            name: Base name for the files
        """
        directory = Path(directory)
        directory.mkdir(exist_ok=True)

        # Save requirements
        Requirement.save_multiple(
            self.requirements, directory / f"{name}_requirements.yaml"
        )

        # Save rubric configuration (judges and reward strategy)
        self._save_config(directory / f"{name}_config.yaml", name)

        print(f"Saved rubric to {directory}/")
        print(f"  - {name}_requirements.yaml")
        print(f"  - {name}_config.yaml")

    def _save_config(
        self,
        file_path: Union[str, Path],
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> None:
        """Save rubric configuration to YAML file."""
        config_data: Dict[str, Any] = {}

        if name:
            config_data["name"] = name
        if description:
            config_data["description"] = description

        # Serialize judge options
        judges_data = []
        for judge in self.judge_options:
            # Detect client type and configuration
            client_type, client_config = detect_client_type(judge.judge_client)

            judge_data = {
                "type": judge.__class__.__name__.replace("JudgeRewarder", "").lower(),
                "judge_prompt": judge.judge_prompt,
                "judge_model": judge.judge_model,
                "client_type": client_type,
                "client_config": client_config,
            }
            judges_data.append(judge_data)
        config_data["judge_options"] = judges_data

        # Serialize reward strategy
        strategy_data = {
            "type": self.reward_strategy.__class__.__name__.replace(
                "RewardStrategy", ""
            ).lower(),
        }

        # Add all strategy parameters automatically
        for attr_name in dir(self.reward_strategy):
            # Skip private attributes, methods, and built-in attributes
            if (
                not attr_name.startswith("_")
                and not callable(getattr(self.reward_strategy, attr_name))
                and attr_name not in ["name"]
            ):  # Skip the 'name' property
                strategy_data[attr_name] = getattr(self.reward_strategy, attr_name)

        config_data["reward_strategy"] = strategy_data

        with open(file_path, "w") as f:
            yaml.dump(config_data, f, default_flow_style=False, indent=2)

    @classmethod
    def load(
        cls,
        directory: Union[str, Path],
        name: str = "rubric",
    ) -> "MultiStepRubric":
        """
        Load a MultiStepRubric from a directory.

        Args:
            directory: Directory containing the files
            name: Base name for the files

        Returns:
            MultiStepRubric object
        """
        directory = Path(directory)

        # Load requirements
        requirements = Requirement.load_multiple(
            directory / f"{name}_requirements.yaml"
        )

        # Load configuration
        config = cls._load_config(directory / f"{name}_config.yaml")

        return cls(
            requirements=requirements,
            judge_options=config["judge_options"],
            reward_strategy=config["reward_strategy"],
        )

    @classmethod
    def _load_config(cls, file_path: Union[str, Path]) -> Dict[str, Any]:
        """Load rubric configuration from YAML file."""
        with open(file_path, "r") as f:
            config_data = yaml.safe_load(f)

        # Load judge options
        judge_options = make_judge_rewarders(config_data["judge_options"])

        # Load reward strategy
        strategy_config = config_data["reward_strategy"].copy()
        strategy_type = strategy_config.pop("type")
        reward_strategy = make_reward_strategy(strategy_type, **strategy_config)

        return {
            "judge_options": judge_options,
            "reward_strategy": reward_strategy,
            "name": config_data.get("name"),
            "description": config_data.get("description"),
        }
