from openai import OpenAI

from verifiers import Parser, Rubric
from verifiers.rewards.judge_reward import JUDGE_PROMPT, BinaryJudgeRewarder


class JudgeRubric(Rubric):
    def __init__(
        self,
        parser: Parser = Parser(),
        parallelize_scoring: bool = False,
        judge_client: OpenAI | None = None,
        judge_model: str = "gpt-4.1-nano",
        judge_sampling_args: dict = {},
        judge_prompt: str = JUDGE_PROMPT,
        **kwargs,
    ):
        super().__init__(
            parser=parser, parallelize_scoring=parallelize_scoring, **kwargs
        )
        self.parser = parser
        self.judge_client = judge_client if judge_client is not None else OpenAI()
        self.judge_model = judge_model
        self.judge_prompt = judge_prompt
        self.judge_sampling_args = judge_sampling_args
        self.judge_rewarder = BinaryJudgeRewarder(
            judge_prompt,
            judge_client=judge_client,
            judge_model=judge_model,
            parser=parser,
        )
        self.add_reward_func(self.judge_rewarder)

    def judge(self, prompt, completion, answer, state, **kwargs) -> str:
        if "judge_response" in state:
            return state["judge_response"]
        judge_response = self.judge_rewarder(
            prompt, completion, answer, state, **kwargs
        )
        state["judge_response"] = judge_response
        return judge_response
