import asyncio
from typing import Any, List, Dict, Union, Callable
from collections import defaultdict

from verifiers.rewards.judge_reward import JudgeRewarder
from verifiers.rubrics.multistep.core.scenario import Scenario
from verifiers.rubrics.multistep.core.enums import EvaluationMode, TerminalCondition
from verifiers.rubrics.multistep.core.results import EvaluationResult
from verifiers.rubrics.multistep.core.reward_strategies import RewardStrategy, LevelWeightedRewardStrategy
from verifiers.rubrics.multistep.core.nodes import RequirementRewardNode
from verifiers.rubrics.multistep.core.utils import topological_levels


class MultiStepRubric:
    """
    Rubric that evaluates requirements with dependencies using different traversal modes.
    
    Supports evaluation modes including adaptive evaluation that stops gracefully
    when no valid path forward exists.
    """
    
    def __init__(self, requirements: List[Any], judge_rewarder: JudgeRewarder, 
                 node_factory: Callable = RequirementRewardNode,
                 reward_strategy: RewardStrategy = None):
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
        self.name_to_node = {name: node_factory(req, judge_rewarder) 
                            for name, req in self.name_to_req.items()}
       
        
        # Build dependency structure for topological sorting
        self.name_to_dependency_options = {
            name: sum(req.dependencies.values(), []) if req.dependencies else [] 
            for name, req in self.name_to_req.items()
        }
        
        # Get topological levels (reversed to start from root nodes)
        self.levels = topological_levels(self.name_to_dependency_options)
        self.levels.reverse()
    
    def validate(self, scenario: Scenario, mode: EvaluationMode = None, **kwargs) -> None:
        """
        Validate that the scenario is compatible with this rubric's requirements.
        
        Args:
            scenario: The scenario to validate
            mode: The evaluation mode (for mode-specific validation)
            **kwargs: Additional arguments that may contain ground_truth_answers
        
        Raises:
            ValueError: If validation fails
        """
        if scenario.answers:
            # Check unknown requirements
            unknown_requirements = set(scenario.answers.keys()) - set(self.name_to_req.keys())
            if unknown_requirements:
                raise ValueError(f"Scenario contains answers for unknown requirements: {unknown_requirements}")
            
            # Check invalid answer values
            for req_name, answer_data in scenario.answers.items():
                requirement = self.name_to_req[req_name]
                valid_options = requirement.judge_response_format.options
                
                # Extract answer value from new format
                if isinstance(answer_data, dict) and "answer" in answer_data:
                    answer_value = answer_data["answer"]
                else:
                    # Fallback for old format
                    answer_value = answer_data
                    
                if answer_value not in valid_options:
                    raise ValueError(f"Invalid answer value {answer_value} for requirement '{req_name}'. "
                                   f"Valid options are: {valid_options}")
        
        # Mode-specific validation
        if mode == EvaluationMode.REFERENCE_GUIDED:
            ground_truth_answers = kwargs.get("ground_truth_answers")
            if ground_truth_answers is None:
                raise ValueError("ground_truth_answers is required for REFERENCE_GUIDED mode")
            
            # Validate ground truth answers
            for req_name, answer_value in ground_truth_answers.items():
                if req_name not in self.name_to_req:
                    raise ValueError(f"Ground truth answers contains unknown requirement: {req_name}")
                
                requirement = self.name_to_req[req_name]
                valid_options = requirement.judge_response_format.options
                if answer_value not in valid_options:
                    raise ValueError(f"Invalid answer value {answer_value} in ground truth answers for requirement '{req_name}'. "
                                   f"Valid options are: {valid_options}")
    
    async def evaluate_adaptive(self, scenario: Scenario,
                               max_depth: int = 10, **kwargs) -> EvaluationResult:
        """
        Adaptive evaluation that stops gracefully when no valid path forward exists.
        Returns detailed results including terminal condition and completion status.
        """
        state = defaultdict(dict)
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
                    if isinstance(result, (int, float)) and result in node.requirement.dependencies:
                        next_level.extend(node.requirement.dependencies[result])
            
            # Stop if no valid path forward
            if not next_level:
                terminal_condition = TerminalCondition.NO_VALID_PATH if i > 0 else TerminalCondition.COMPLETED
                return EvaluationResult(dict(state), terminal_condition, completed_requirements, len(self.requirements))
            
            level = list(set(next_level))
            i += 1
            
        # Determine terminal condition
        if i >= max_depth:
            terminal_condition = TerminalCondition.MAX_DEPTH_REACHED
        else:
            terminal_condition = TerminalCondition.COMPLETED
            
        return EvaluationResult(dict(state), terminal_condition, completed_requirements, len(self.requirements))
    
    async def evaluate_model_guided(self, 
                                  scenario: Scenario,
                                  start_level_idx: int = 0, **kwargs) -> Dict[str, Any]:
        """
        Follow the model's answers through the dependency graph.
        Simulates the actual workflow path the model would take.
        """
        state = defaultdict(dict)
        i = start_level_idx
        level = self.levels[start_level_idx] if start_level_idx < len(self.levels) else []
        
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
                if not node.requirement.terminal() and model_answer in node.requirement.dependencies:
                    next_level.extend(node.requirement.dependencies[model_answer])
            
            level = list(set(next_level))
            i += 1
            
        return dict(state)
    
    async def evaluate_reference_guided(self, 
                                      scenario: Scenario,
                                      ground_truth_answers: Dict[str, float], **kwargs) -> Dict[str, Any]:
        """
        Follow the ground truth answers through the dependency graph.
        Evaluates model performance on the "correct" workflow path.
        """
        state = defaultdict(dict)
        i = 0
        level = self.levels[0] if self.levels else []
        
        while level:
            print(f"Evaluating reference level {i}: {level}")
            
            # Only evaluate requirements that have ground truth answers
            level_with_answers = [name for name in level if name in ground_truth_answers]
            
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
                if not node.requirement.terminal() and gt_answer in node.requirement.dependencies:
                    next_level.extend(node.requirement.dependencies[gt_answer])
            
            level = list(set(next_level))
            i += 1

            print(f"level {i} scores: {level_scores}")
            
        return dict(state)
    
    async def evaluate_exhaustive(self, scenario: Scenario, **kwargs) -> Dict[str, float]:
        """
        Evaluate all requirements regardless of dependencies.
        Provides comprehensive capability assessment.
        """
        all_nodes = list(self.name_to_node.values())
        
        # Evaluate all nodes in parallel
        coros = [node(scenario, **kwargs) for node in all_nodes]
        all_scores = await asyncio.gather(*coros)
        
        return {node.name: score for node, score in zip(all_nodes, all_scores)}
    
    async def evaluate(self, 
                      scenario: Scenario,
                      mode: EvaluationMode = EvaluationMode.MODEL_GUIDED,
                      **kwargs) -> Union[Dict[str, Any], EvaluationResult]:
        """
        Main evaluation method that dispatches to appropriate evaluation mode.
        """
        self.validate(scenario, mode, **kwargs)  # Validate scenario before evaluation
        if mode == EvaluationMode.MODEL_GUIDED:
            return await self.evaluate_model_guided(scenario, **kwargs)
        elif mode == EvaluationMode.REFERENCE_GUIDED:
            if "ground_truth_answers" not in kwargs:
                # Convert scenario.answers to ground_truth_answers format
                ground_truth_answers = {}
                for req_name, answer_data in scenario.answers.items():
                    if isinstance(answer_data, dict) and "answer" in answer_data:
                        ground_truth_answers[req_name] = answer_data["answer"]
                    else:
                        ground_truth_answers[req_name] = answer_data
            else:
                ground_truth_answers = kwargs.pop("ground_truth_answers")
            return await self.evaluate_reference_guided(scenario, ground_truth_answers, **kwargs)
        elif mode == EvaluationMode.EXHAUSTIVE:
            return await self.evaluate_exhaustive(scenario, **kwargs)
        elif mode == EvaluationMode.ADAPTIVE:
            return await self.evaluate_adaptive(scenario, **kwargs)
        else:
            raise ValueError(f"Unknown evaluation mode: {mode}")
        
    async def score_rollout(self,
                            prompt: Union[str, List[Dict[str, Any]]],
                            completion: Union[str, List[Dict[str, Any]]],
                            answer: Any,
                            state: Dict[str, Any],
                            task: str = "default",
                            info: dict = {},
                            mode: EvaluationMode = EvaluationMode.MODEL_GUIDED,
                            **kwargs) -> Dict[str, Any]:
        """
        Enhanced score_rollout that can handle different evaluation modes and terminal conditions.
        Uses configurable reward strategy for flexible reward calculation.
        """
        # Create a Scenario object from the individual parameters
        scenario = Scenario(prompt=prompt, completion=completion, answers=answer)
        result = await self.evaluate(scenario, mode=mode, **kwargs)
        
        # Calculate reward using the configured strategy
        reward_kwargs = {
            'total_requirements': len(self.requirements),
            **kwargs
        }
        reward = self.reward_strategy.calculate_reward(result, mode, **reward_kwargs)
        
        if isinstance(result, EvaluationResult):
            # Adaptive evaluation
            return {
                **result.to_dict(),
                'reward': reward,
                'reward_strategy': self.reward_strategy.name,
                'mode': mode.value
            }
        else:
            # Traditional evaluation modes
            return {
                'state': result,
                'reward': reward,
                'reward_strategy': self.reward_strategy.name,
                'mode': mode.value,
                'terminal_condition': TerminalCondition.COMPLETED.value
            } 