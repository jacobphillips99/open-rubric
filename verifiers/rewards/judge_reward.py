import asyncio
import json
import string
from dataclasses import dataclass
from typing import Any, Optional
from verifiers.rewards.reward import Reward
from openai import OpenAI
from verifiers.parsers.parser import Parser
from verifiers.rewards.judge_utils import ContinuousJudgeResponseFormat, DiscreteJudgeResponseFormat, JudgeResponseFormat, JudgeResponse
from verifiers.rewards.judge_utils import binary_judge_response_format, unit_vector_judge_response_format


JUDGE_PROMPT = """
Given a question and the ground truth answer, determine if the response is correct. Respond according to the judge response format.

question={question}
response={response}
ground truth answer={answer}
judge response format={judge_response_format}
""".strip()
JUDGE_PROMPT_VARIABLES = ["question", "answer", "response", "judge_response_format"]


# FIXME -- other client types
def create_openai_client(base_url: Optional[str] = None, api_key: Optional[str] = None, **kwargs) -> OpenAI:
    """Create an OpenAI client with optional custom configuration."""
    client_kwargs = {}
    if base_url is not None:
        client_kwargs["base_url"] = base_url
    if api_key is not None:
        client_kwargs["api_key"] = api_key
    client_kwargs.update(kwargs)
    return OpenAI(**client_kwargs)


CLIENT_TYPE_TO_FACTORY = {
    "openai": lambda: OpenAI(),
    "openai_custom": create_openai_client,
}


def make_client(client_type: str, **kwargs) -> OpenAI:
    """Create a client based on the client type and configuration."""
    if client_type not in CLIENT_TYPE_TO_FACTORY:
        raise ValueError(f"Unknown client type: {client_type}. Available types: {list(CLIENT_TYPE_TO_FACTORY.keys())}")

    factory = CLIENT_TYPE_TO_FACTORY[client_type]
    return factory(**kwargs)


def detect_client_type(client: OpenAI) -> tuple[str, dict[str, Any]]:
    """
    Detect the client type and extract serializable configuration.

    Returns:
        Tuple of (client_type, config_dict)
    """
    config = {}

    # Check if it's a custom OpenAI client (non-standard base_url)
    if client.base_url and str(client.base_url) != "https://api.openai.com/v1/":
        config["base_url"] = str(client.base_url)
        return "openai_custom", config

    # Default OpenAI client
    return "openai", config


class JudgeRewarder(Reward):
    def __init__(self, judge_prompt: str, judge_response_format: JudgeResponseFormat, judge_client: OpenAI | None = None, judge_model: str = "gpt-4.1-nano", parser: Parser = Parser(), **kwargs):
        self.judge_response_format = judge_response_format
        self.judge_prompt = judge_prompt

        # Assert that judge_prompt template contains exactly the expected fields
        formatter = string.Formatter()
        field_names = {field_name for literal_text, field_name, format_spec, conversion in formatter.parse(judge_prompt) if field_name is not None}
        assert set(field_names) == set(JUDGE_PROMPT_VARIABLES), f"Judge prompt template must contain exactly these fields: {JUDGE_PROMPT_VARIABLES}; got {field_names}"

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
    def __init__(self, judge_prompt: str, judge_response_format: JudgeResponseFormat = None, judge_client: OpenAI | None = None, judge_model: str = "gpt-4.1-nano", parser: Parser = Parser(), **kwargs):
        # If no response format provided, use binary as default for discrete
        if judge_response_format is None:
            judge_response_format = binary_judge_response_format
        super().__init__(judge_prompt, judge_response_format, judge_client, judge_model, parser, **kwargs)

class ContinuousJudgeRewarder(JudgeRewarder):
    def __init__(self, judge_prompt: str, judge_response_format: JudgeResponseFormat = None, judge_client: OpenAI | None = None, judge_model: str = "gpt-4.1-nano", parser: Parser = Parser(), **kwargs):
        # If no response format provided, use unit vector as default for continuous
        if judge_response_format is None:
            judge_response_format = unit_vector_judge_response_format
        super().__init__(judge_prompt, judge_response_format, judge_client, judge_model, parser, **kwargs)

class BinaryJudgeRewarder(DiscreteJudgeRewarder):
    def __init__(self, judge_prompt: str, judge_client: OpenAI | None = None, judge_model: str = "gpt-4.1-nano", parser: Parser = Parser(), **kwargs):
        super().__init__(judge_prompt, binary_judge_response_format, judge_client, judge_model, parser, **kwargs)

class UnitVectorJudgeRewarder(JudgeRewarder):
    def __init__(self, judge_prompt: str, judge_client: OpenAI | None = None, judge_model: str = "gpt-4.1-nano", parser: Parser = Parser(), **kwargs):
        super().__init__(judge_prompt, unit_vector_judge_response_format, judge_client, judge_model, parser, **kwargs)

NAME_TO_JUDGE_REWARDER_CLASS = {
    "binary": BinaryJudgeRewarder,
    "unit_vector": UnitVectorJudgeRewarder,
    "discrete": DiscreteJudgeRewarder,
    "continuous": ContinuousJudgeRewarder,
}

def make_judge_rewarder(judge_rewarder_type: str, **kwargs) -> JudgeRewarder:
    """Make a judge rewarder based on the judge_rewarder_type."""
    # Handle client creation if client info is provided
    if "client_type" in kwargs:
        client_type = kwargs.pop("client_type")
        client_config = kwargs.pop("client_config", {})
        kwargs["judge_client"] = make_client(client_type, **client_config)

    # Handle response format creation for discrete/continuous judges
    if "response_format" in kwargs:
        response_format_config = kwargs.pop("response_format")
        format_type = response_format_config.get("type")
        
        if format_type == "discrete":
            judge_response_format = DiscreteJudgeResponseFormat(
                options=response_format_config.get("options", [0.0, 1.0]),
                meanings=response_format_config.get("meanings")
            )
            kwargs["judge_response_format"] = judge_response_format
            
        elif format_type == "continuous":
            judge_response_format = ContinuousJudgeResponseFormat(
                options=response_format_config.get("options", [0.0, 1.0]),
                meanings=response_format_config.get("meanings")
            )
            kwargs["judge_response_format"] = judge_response_format

    return NAME_TO_JUDGE_REWARDER_CLASS[judge_rewarder_type](**kwargs)

def make_judge_rewarders(judge_rewarders: list[dict]) -> list[JudgeRewarder]:
    """Make a list of judge rewarders based on the judge_rewarders."""
    result = []
    for j in judge_rewarders:
        # Create a copy without the 'type' key to avoid conflicts
        kwargs = {k: v for k, v in j.items() if k != "type"}
        result.append(make_judge_rewarder(j["type"], **kwargs))
    return result
