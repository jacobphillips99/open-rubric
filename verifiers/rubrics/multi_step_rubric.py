import asyncio
from typing import Any, List, Dict, Union
from collections import defaultdict, deque
from verifiers.rubrics.rubric import Rubric



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


class MultiStepRubric(Rubric):
    def __init__(self, dependencies: Dict[str, List[str]] = {}, **kwargs):
        super().__init__(**kwargs)
        self.reward_funcs_dict = {func.__name__: func for func in self.reward_funcs}
        self.reward_weights_dict = {func.__name__: weight for func, weight in zip(self.reward_funcs, self.reward_weights)}
        self.dependencies = dependencies

        for func_name in self.reward_funcs_dict.keys():
            if func_name not in dependencies:
                dependencies[func_name] = []

        self.level_names: list[list[str]] = topological_levels(dependencies)

    async def _score_dependency_level(self, 
                                    level: List[str], 
                                    prompt: Union[str, List[Dict[str, Any]]],
                                    completion: Union[str, List[Dict[str, Any]]],
                                    answer: Any,
                                    state: Dict[str, Any],
                                    task: str = "default",
                                    info: dict = {},
                                    **kwargs) -> Dict[str, float]:
        """
        Score a topological level of reward functions in parallel.
        """
        futures = [
            asyncio.to_thread(
                self._call_reward_func,
                func,
                prompt,
                completion,
                answer,
                state,
                task=task,
                info=info,
                **kwargs
            )
            for func in [self.reward_funcs_dict[name] for name in level]
        ]
        reward_scores = await asyncio.gather(*futures)
        rewards = {func_name: reward for func_name, reward in zip(level, reward_scores)}
        return rewards

    async def score_rollout(self,
                            prompt: Union[str, List[Dict[str, Any]]],
                            completion: Union[str, List[Dict[str, Any]]],
                            answer: Any,
                            state: Dict[str, Any],
                            task: str = "default",
                            info: dict = {},
                            **kwargs) -> Dict[str, float]:
        """
        Evaluate reward functions in order of a topological level-sort of dependencies.
        """
        rewards = dict()
        for level in self.level_names:
            intermediate_rewards = await self._score_dependency_level(level, prompt, completion, answer, state, task, info, **kwargs)
            # do some logic on selecting the next level?
            breakpoint()
            rewards.update(intermediate_rewards)
        rewards['reward'] = sum([rewards[func_name] * self.reward_weights_dict[func_name] for func_name in all_rewards])
        return rewards

def fn1(*args, **kwargs):
    return 1

def fn2(*args, **kwargs):
    return 2

def fn3(*args, **kwargs):
    return 3

def fn4(*args, **kwargs):
    return 4

fns = [fn1, fn2, fn3, fn4]
dependencies_fns = {fn2: [fn1], fn3: [fn1], fn4: [fn2, fn3]}
dependencies_names = {k.__name__: [v.__name__ for v in v] for k, v in dependencies_fns.items()}
rubric = MultiStepRubric(dependencies=dependencies_names, funcs=fns, weights=[0,0,0,1])

print(f"found {len(rubric.level_names)} levels")
for i, level in enumerate(rubric.level_names):
    print(f"level {i} has {len(level)} functions: {level}")

prompt = "a"
completion = "b"
answer = "c"
state = {}
task = "default"
info = {}
kwargs = {}

result = asyncio.run(rubric.score_rollout(prompt, completion, answer, state, task, info, **kwargs))
breakpoint()





