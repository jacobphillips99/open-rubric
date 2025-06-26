import os
from openai import OpenAI

from verifiers.parsers import Parser
from verifiers.rubrics.rubric import Rubric
from verifiers.rewards.judge_reward import BinaryJudgeRewarder

DEFAULT_JUDGE_PROMPT = """Given a ground truth answer \
and a response, determine if the response is correct.

Question:
```
{question}
```

Ground truth answer:
```
{answer}
```

Response:
```
{response}
```

{judge_response_format}"""

class JudgeRubric(Rubric):
    def __init__(self,
                 judge_client: OpenAI | None = None,
                 judge_model: str = "gpt-4.1-nano",
                 judge_prompt: str = DEFAULT_JUDGE_PROMPT,
                 parser: Parser = Parser(),
                 **kwargs):
        super().__init__(**kwargs)
        self.judge_rewarder = BinaryJudgeRewarder(judge_prompt, judge_client=judge_client, judge_model=judge_model, parser=parser)
        self.add_reward_func(self.judge_rewarder)



    