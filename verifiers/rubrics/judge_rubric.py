import os
from openai import OpenAI

from verifiers.parsers import Parser
from verifiers.rubrics.rubric import Rubric
from verifiers.rewards.judge_reward import JUDGE_PROMPT, BinaryJudgeRewarder


class JudgeRubric(Rubric):
    def __init__(self,
                 judge_client: OpenAI | None = None,
                 judge_model: str = "gpt-4.1-nano",
                 judge_prompt: str = JUDGE_PROMPT,
                 parser: Parser = Parser(),
                 **kwargs):
        super().__init__(**kwargs)
        self.judge_rewarder = BinaryJudgeRewarder(judge_prompt, judge_client=judge_client, judge_model=judge_model, parser=parser)
        self.add_reward_func(self.judge_rewarder)
