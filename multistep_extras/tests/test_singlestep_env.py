from copy import deepcopy
import os
import asyncio
from openai import OpenAI, AsyncOpenAI
from multistep_extras.example_rubrics import (
    first_responder_requirements as REQUIREMENTS,
    first_responder_scenarios as ALL_SCENARIOS,
)
from datasets import Dataset

from verifiers.envs.singleturn_env import SingleTurnEnv
from verifiers.rubrics.multistep.multistep_rubric import MultiStepRubric
from verifiers.rewards.judge_reward import JUDGE_PROMPT, BinaryJudgeRewarder


def setup_inputs(ds: Dataset | dict) -> dict:
    """
    Setup the inputs for the environment.
    Copied from verifiers.envs.environment.py generate()

    """
    if isinstance(ds, Dataset):
        results = {col: deepcopy(ds[col]) for col in ds.column_names}
    else:
        results = deepcopy(ds)
    if "task" not in results:
        results["task"] = ["default"] * len(results["prompt"])
    if "info" not in results:
        results["info"] = [{}] * len(results["prompt"])
    return results


async def run_test():
    """ Setup objects for environment -- client, model, requirements, judges, rubric, dataset, and env. """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    async_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    model = "gpt-4.1-nano"
    scenario = ALL_SCENARIOS[0]

    max_concurrent = 10
    binary_judge_rewarder = BinaryJudgeRewarder(judge_prompt=JUDGE_PROMPT)
    rubric = MultiStepRubric(
        REQUIREMENTS,
        [binary_judge_rewarder],
    )

    ds = Dataset.from_dict(
        {
            "prompt": [scenario.prompt],
            "answer": [scenario.answers],
        }
    )

    env = SingleTurnEnv(
        rubric=rubric,
        dataset=ds,
        message_type="chat",
    )

    results = setup_inputs(ds)
    results["answer"] = scenario.answers
    if isinstance(results["prompt"][0], str):
        results["prompt"] = [{"role": "user", "content": results["prompt"][0]}]

    """ Run policy model rollouts (done with API model for testing)"""
    # Use async client and await the result
    rollout = await env.rollout(
        client=async_client,
        model=model,
        prompt=results["prompt"],
        answer=results["answer"],
        task=results["task"],
        info=results["info"],
    )
    results["completion"] = rollout[0]
    results["state"] = rollout[1]
    if "task" not in results:
        results["task"] = "default"

    """ Score rollouts with multistep rubric """
    results_rewards = await env.rubric.score_rollouts(
        prompts=[results["prompt"]],
        completions=[results["completion"]],
        answers=[results["answer"]],
        states=[results["state"]],
        tasks=[results["task"]],
        infos=[results["info"]],
        max_concurrent=max_concurrent,
        apply_weights=True,
    )
    results.update(results_rewards)


if __name__ == "__main__":
    asyncio.run(run_test())
