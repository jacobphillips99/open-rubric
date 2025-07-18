import asyncio
import json
import string
from dataclasses import dataclass
from typing import Any, Optional
from verifiers.rewards.reward import Reward
from openai import OpenAI
from verifiers.parsers.parser import Parser
from verifiers.rewards.judge_utils import DiscreteJudgeResponseFormat, JudgeResponseFormat, JudgeResponse
from verifiers.rewards.judge_utils import binary_judge_response_format, unit_vector_judge_response_format

JUDGE_PROMPT = """
Given a question and the ground truth answer, determine if the response is correct. Respond according to the judge response format.

question={question}
response={response}
ground truth answer={answer}
judge response format={judge_response_format}
"""

class JudgeRewarder(Reward):
    def __init__(self, judge_prompt: str, judge_response_format: JudgeResponseFormat, judge_client: OpenAI | None = None, judge_model: str = "gpt-4.1-nano", parser: Parser = Parser(), **kwargs):
        super().__init__(**kwargs)
        self.judge_response_format = judge_response_format
        self.judge_prompt = judge_prompt

        # Assert that judge_prompt template contains exactly the expected fields
        formatter = string.Formatter()
        field_names = {field_name for literal_text, field_name, format_spec, conversion in formatter.parse(judge_prompt) if field_name is not None}
        expected_fields = {"question", "answer", "response", "judge_response_format"}
        assert field_names == expected_fields, f"Judge prompt template must contain exactly these fields: {expected_fields}; got {field_names}"

        self.judge_client = judge_client if judge_client is not None else OpenAI()
        self.judge_model = judge_model
        self.parser = parser

    async def __call__(self, prompt, completion, answer, **kwargs) -> JudgeResponse:
        response = self.parser.parse_answer(completion)
        # check which fields are present in judge prompt template
        # get question from answer:
        if isinstance(prompt, list):
            question = prompt[-1]['content']
        else:
            question = prompt
        if isinstance(completion, list):
            response = completion[-1]['content']
        else:
            response = completion
        prompt = self.judge_prompt.format(question=question, answer=answer, response=response, judge_response_format=self.judge_response_format)

        def _create_completion():
            return self.judge_client.chat.completions.create(
                    model=self.judge_model,
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=200,  # Increased for JSON response with reasoning
                )
        try:
            judge_response = await asyncio.to_thread(_create_completion)
            judge_answer = judge_response.choices[0].message.content
            judge_result = self.judge_response_format.convert(judge_answer)
        except Exception as e:
            print(f"Error in judge_rewarder: {e}; {e.__traceback__}")
            raise e

        return judge_result


class DiscreteJudgeRewarder(JudgeRewarder):
    pass

class ContinuousJudgeRewarder(JudgeRewarder):
    pass

class BinaryJudgeRewarder(DiscreteJudgeRewarder):
    def __init__(self, judge_prompt: str, judge_client: OpenAI | None = None, judge_model: str = "gpt-4.1-nano", parser: Parser = Parser(), **kwargs):
        super().__init__(judge_prompt, binary_judge_response_format, judge_client, judge_model, parser, **kwargs)

class UnitVectorJudgeRewarder(JudgeRewarder):
    def __init__(self, judge_prompt: str, judge_client: OpenAI | None = None, judge_model: str = "gpt-4.1-nano", parser: Parser = Parser(), **kwargs):
        super().__init__(judge_prompt, unit_vector_judge_response_format, judge_client, judge_model, parser, **kwargs)
