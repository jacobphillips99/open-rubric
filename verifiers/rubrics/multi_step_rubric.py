import asyncio
from typing import Any, List, Dict, Union
from collections import defaultdict, deque
from enum import Enum
from verifiers.parsers.parser import Parser
from verifiers.rewards.judge_reward import JudgeRewarder, BinaryJudgeRewarder, binary_judge_response_format
from verifiers.rewards.reward import Reward
from verifiers.rubrics.rubric import Rubric
from openai import OpenAI
from verifiers.rubrics.example_rubrics import first_responder_reqs, Requirement


class EvaluationMode(Enum):
    """Different modes for evaluating multi-step rubrics."""
    MODEL_GUIDED = "model_guided"        # Follow model's answers through graph
    REFERENCE_GUIDED = "reference_guided"  # Follow ground truth answers through graph  
    EXHAUSTIVE = "exhaustive"            # Evaluate all nodes regardless of dependencies


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


class MultiStepRubric:
    """
    Rubric that evaluates requirements with dependencies using different traversal modes.
    
    Supports three evaluation modes:
    - MODEL_GUIDED: Follow model's answers to simulate real decision paths
    - REFERENCE_GUIDED: Follow ground truth answers for standardized evaluation
    - EXHAUSTIVE: Evaluate all requirements for comprehensive capability assessment
    """
    
    def __init__(self, requirements: List[Requirement], judge_rewarder: JudgeRewarder):
        self.requirements = requirements
        self.judge_rewarder = judge_rewarder
        
        # Build lookup structures
        self.name_to_req = {req.name: req for req in requirements}
        self.name_to_node = {name: RequirementRewardNode(req, judge_rewarder) 
                            for name, req in self.name_to_req.items()}
        
        # Build dependency structure for topological sorting
        self.name_to_dependency_options = {
            name: sum(req.dependencies.values(), []) if req.dependencies else [] 
            for name, req in self.name_to_req.items()
        }
        
        # Get topological levels (reversed to start from root nodes)
        self.levels = topological_levels(self.name_to_dependency_options)
        self.levels.reverse()
    
    async def evaluate_model_guided(self, prompt: str, completion: str, answer: str, 
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
            coros = [node(prompt, completion, answer, **kwargs) for node in nodes]
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
    
    async def evaluate_reference_guided(self, prompt: str, completion: str, answer: str,
                                      ground_truth_path: Dict[str, float], **kwargs) -> Dict[str, Any]:
        """
        Follow the ground truth answers through the dependency graph.
        Evaluates model performance on the "correct" workflow path.
        """
        state = defaultdict(dict)
        i = 0
        level = self.levels[0] if self.levels else []
        
        while level:
            print(f"Evaluating reference level {i}: {level}")
            nodes = [self.name_to_node[name] for name in level]
            
            # Evaluate model on this level
            coros = [node(prompt, completion, answer, **kwargs) for node in nodes]
            level_scores = dict(zip(level, await asyncio.gather(*coros)))
            state[i] = level_scores
            
            # Determine next level based on ground truth answers
            next_level = []
            for name in level:
                if name in ground_truth_path:
                    node = self.name_to_node[name]
                    gt_answer = ground_truth_path[name]
                    if not node.requirement.terminal() and gt_answer in node.requirement.dependencies:
                        next_level.extend(node.requirement.dependencies[gt_answer])
            
            level = list(set(next_level))
            i += 1
            
        return dict(state)
    
    async def evaluate_exhaustive(self, prompt: str, completion: str, answer: str, **kwargs) -> Dict[str, float]:
        """
        Evaluate all requirements regardless of dependencies.
        Provides comprehensive capability assessment.
        """
        all_nodes = list(self.name_to_node.values())
        
        # Evaluate all nodes in parallel
        coros = [node(prompt, completion, answer, **kwargs) for node in all_nodes]
        all_scores = await asyncio.gather(*coros)
        
        return {node.name: score for node, score in zip(all_nodes, all_scores)}
    
    async def evaluate(self, prompt: str, completion: str, answer: str,
                      mode: EvaluationMode = EvaluationMode.MODEL_GUIDED,
                      ground_truth_path: Dict[str, float] = None,
                      **kwargs) -> Dict[str, Any]:
        """
        Main evaluation method that dispatches to appropriate evaluation mode.
        """
        if mode == EvaluationMode.MODEL_GUIDED:
            return await self.evaluate_model_guided(prompt, completion, answer, **kwargs)
        elif mode == EvaluationMode.REFERENCE_GUIDED:
            if ground_truth_path is None:
                raise ValueError("ground_truth_path required for REFERENCE_GUIDED mode")
            return await self.evaluate_reference_guided(prompt, completion, answer, ground_truth_path, **kwargs)
        elif mode == EvaluationMode.EXHAUSTIVE:
            return await self.evaluate_exhaustive(prompt, completion, answer, **kwargs)
        else:
            raise ValueError(f"Unknown evaluation mode: {mode}")
        
    async def score_rollout(self,
                            prompt: Union[str, List[Dict[str, Any]]],
                            completion: Union[str, List[Dict[str, Any]]],
                            answer: Any,
                            state: Dict[str, Any],
                            task: str = "default",
                            info: dict = {},
                            **kwargs) -> Dict[str, float]:
        state = await self.evaluate(prompt, completion, answer, mode=EvaluationMode.MODEL_GUIDED)
        reward = sum([i*sum(state[i].values()) for i in state.keys()]) # weighted sum against successful level rewards
        state['reward'] = reward
        return state
        


class RequirementRewardNode:
    def __init__(self, requirement: Requirement, judge_rewarder: JudgeRewarder):
        self.requirement = requirement
        self.judge_rewarder = judge_rewarder
        self.name = requirement.name
    
    async def __call__(self, prompt, completion, answer, **kwargs):
        return await self.judge_rewarder(prompt, completion, answer, **kwargs)
    
    def get_dependencies(self):
        return self.requirement.dependencies

class BinaryRequirementRewardNode(RequirementRewardNode):
    def __init__(self, requirement: Requirement, judge_rewarder: BinaryJudgeRewarder):
        super().__init__(requirement, judge_rewarder)


async def main():
    import os
    api_key = os.getenv("OPENAI_API_KEY")
    judge_client = OpenAI(api_key=api_key)
    
    judge_prompt = "Does the following response satisfy this question? Question: {question}\nResponse: {response}\nRespond with the following answer format: {judge_response_format}"
    judge_rewarder = BinaryJudgeRewarder(judge_prompt, judge_client=judge_client)
    
    # name_to_req = {req.name: req for req in first_responder_reqs}
    # name_to_node = {name: BinaryRequirementRewardNode(name_to_req[name], judge_rewarder) for name in name_to_req.keys()}
    # name_to_dependencies = {name: name_to_node[name].get_dependencies() for name in name_to_req.keys()}
    # name_to_dependency_options = {name: sum(deps.values(), []) if deps else [] for name, deps in name_to_dependencies.items()}

    # need to reverse the levels to find starting point
    # levels = topological_levels(name_to_dependency_options) 
    # levels.reverse()
    

    prompt = "you come across a patient who is unconsious and not breathing. "
    completion = "First, I'll check if the scene is safe. Then I'll jump right into CPR."
    
    # Ground truth path for unconscious, non-breathing patient scenario
    # This represents the expected correct decisions at each step
    answer = {
        # Initial assessments - scene safety is assumed safe (allows workflow to continue)
        "scene_safety": 1.0,  # Assume scene is safe to proceed with patient care
        
        # Based on patient being unconscious and not breathing:
        "initial_assessment": 0.0,  # Patient is unconscious/unresponsive (from prompt)
        "vital_signs": 0.0,  # Not breathing indicates unstable vitals (from prompt)  
        "trauma_check": 0.0,  # No trauma mentioned in prompt, assume medical emergency
        
        # Subsequent steps based on unconscious, non-breathing patient:
        "airway_management": 1.0,  # Must assess/manage airway for unconscious patient
        "breathing_support": 0.0,  # Patient not breathing adequately (from prompt)
        "medical_history": 0.0,  # Cannot obtain from unconscious patient
        "symptom_assessment": 0.0,  # Cannot obtain from unconscious patient
        
        # Critical care steps:
        "immediate_intervention": 1.0,  # CPR/resuscitation needed immediately
        "emergency_protocols": 1.0,  # Emergency protocols must be activated
    }
    
    kwargs = {"ground_truth_path": answer}

    rubric = MultiStepRubric(first_responder_reqs, judge_rewarder)
    reference_result = await rubric.score_rollout(prompt, completion, answer, state=dict(), mode=EvaluationMode.REFERENCE_GUIDED, **kwargs)
    model_result = await rubric.score_rollout(prompt, completion, answer, state=dict(), mode=EvaluationMode.MODEL_GUIDED, **kwargs)
    exhaustive_result = await rubric.score_rollout(prompt, completion, answer, state=dict(), mode=EvaluationMode.EXHAUSTIVE, **kwargs)
    
    breakpoint()


if __name__ == "__main__":
    result = asyncio.run(main())
    breakpoint()





