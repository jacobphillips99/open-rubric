import asyncio
from typing import Any, List, Dict, Union
from collections import defaultdict, deque
from verifiers.parsers.parser import Parser
from verifiers.rewards.judge_reward import JudgeRewarder, BinaryJudgeRewarder, binary_judge_response_format
from verifiers.rewards.reward import Reward
from verifiers.rubrics.rubric import Rubric
from openai import AsyncOpenAI
from verifiers.rubrics.example_rubrics import first_responder_reqs, Requirement


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


# class MultiStepRubric(Rubric):
#     def __init__(self, dependencies: Dict[str, List[str]] = {}, **kwargs):
#         super().__init__(**kwargs)
#         self.reward_funcs_dict = {func.name: func for func in self.reward_funcs}
#         self.reward_weights_dict = {func.name: weight for func, weight in zip(self.reward_funcs, self.reward_weights)}
#         self.dependencies = dependencies

#         for func_name in self.reward_funcs_dict.keys():
#             if func_name not in dependencies:
#                 dependencies[func_name] = []

#         self.level_names: list[list[str]] = topological_levels(dependencies)

#     async def _score_dependency_level(self, 
#                                     level: List[str], 
#                                     prompt: Union[str, List[Dict[str, Any]]],
#                                     completion: Union[str, List[Dict[str, Any]]],
#                                     answer: Any,
#                                     state: Dict[str, Any],
#                                     task: str = "default",
#                                     info: dict = {},
#                                     **kwargs) -> Dict[str, float]:
#         """
#         Score a topological level of reward functions in parallel.
#         """
#         futures = [
#             asyncio.to_thread(
#                 self._call_reward_func,
#                 func,
#                 prompt,
#                 completion,
#                 answer,
#                 state,
#                 task=task,
#                 info=info,
#                 **kwargs
#             )
#             for func in [self.reward_funcs_dict[name] for name in level]
#         ]
#         reward_scores = await asyncio.gather(*futures)
#         rewards = {func_name: reward for func_name, reward in zip(level, reward_scores)}
#         return rewards

#     async def score_rollout(self,
#                             prompt: Union[str, List[Dict[str, Any]]],
#                             completion: Union[str, List[Dict[str, Any]]],
#                             answer: Any,
#                             state: Dict[str, Any],
#                             task: str = "default",
#                             info: dict = {},
#                             **kwargs) -> Dict[str, float]:
#         """
#         Evaluate reward functions in order of a topological level-sort of dependencies.
#         """
#         rewards = dict()
#         for level in self.level_names:
#             intermediate_rewards = await self._score_dependency_level(level, prompt, completion, answer, state, task, info, **kwargs)
#             # do some logic on selecting the next level?
#             breakpoint()
#             rewards.update(intermediate_rewards)
#         rewards['reward'] = sum([rewards[func_name] * self.reward_weights_dict[func_name] for func_name in all_rewards])
#         return rewards
    
    

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
    judge_client = AsyncOpenAI(api_key=api_key)
   
    judge_prompt = "Does the following response satisfy this question? Question: {question}\nResponse: {response}\nRespond with the following answer format: {judge_response_format}"
    judge_rewarder = BinaryJudgeRewarder(judge_prompt, judge_client=judge_client)
    
    name_to_req = {req.name: req for req in first_responder_reqs}
    name_to_node = {name: BinaryRequirementRewardNode(name_to_req[name], judge_rewarder) for name in name_to_req.keys()}
    name_to_dependencies = {name: name_to_node[name].get_dependencies() for name in name_to_req.keys()}
    name_to_dependency_options = {name: sum(deps.values(), []) if deps else [] for name, deps in name_to_dependencies.items()}

    # need to reverse the levels to find starting point
    levels = topological_levels(name_to_dependency_options) 
    levels.reverse()
    

    prompt = "you come across a patient who is unconcious and not breathing. "
    completion = "I will check the patient's airway and breathing."
    answer = "The patient is not breathing."
    kwargs = {}

    i = 0
    level = levels[3]
    state = dict()

    while level:
        print(f"solving level {i}: {level}")
        nodes = [name_to_node[name] for name in level], []
        
        # Create coroutines and await them all together
        coros = [node(prompt, completion, answer, **kwargs) for node in nodes]
        level_answers = {k: v for k, v in zip(level, await asyncio.gather(*coros))}
        state.update(level_answers)

        # select next level
        new_level = []
        for name, answer in level_answers.items():
            node = name_to_node[name]
            if node.requirement.terminal():
                continue
            new_level.append(node.requirement.dependencies[answer])

        # increment and move to next level
        level = list(set(sum(new_level, [])))
        i += 1
        print(f"state: {state}")
        breakpoint()

if __name__ == "__main__":
    asyncio.run(main())





