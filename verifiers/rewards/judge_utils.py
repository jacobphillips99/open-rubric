
import json
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class JudgeResponse:
    answer: Any
    reasoning: str

    def to_dict(self):
        return {"answer": self.answer, "reasoning": self.reasoning}

    def __str__(self):
        return f"JudgeResponse(answer={self.answer}, reasoning={self.reasoning})"

JUDGE_RESPONSE_BASE_STR = "Respond with just a JSON object containing two fields: 'answer' and 'reasoning'."
JUDGE_RESPONSE_REASONING_STR = "The 'reasoning' field should contain your explanation for the answer."

class JudgeResponseFormat:
    def __init__(self, options: list[Any], meanings: Optional[dict[Any, str]] = None, base_str: str = JUDGE_RESPONSE_BASE_STR, reasoning_str: str = JUDGE_RESPONSE_REASONING_STR):
        self.options = options
        self.option_type = type(options[0])
        self.meanings = meanings
        self.base_str = base_str
        self.reasoning_str = reasoning_str

        assert all(isinstance(item, self.option_type) for item in options), f"Answer format must be a list of {self.option_type}; got {options} with types {[type(item) for item in options]}"
        if meanings is not None:
            assert all(k in options for k in meanings.keys()), f"All keys in meanings must be in options; got {meanings.keys()} not in {options}"

    def make_base_str(self):
        return f"{self.base_str} The 'answer' field must be in: {self.options} (type {self.option_type.__name__}). {self.reasoning_str}"

    def make_meanings_str(self):
        raise NotImplementedError("make_meanings_str not implemented for base class")

    def make_example_format(self):
        return f"\n\nExample format: {{\"answer\": {self.options[0]}, \"reasoning\": \"Your explanation here\"}}"

    def __str__(self) -> str:
        str_rep = self.make_base_str()
        str_rep += self.make_meanings_str()
        str_rep += self.make_example_format()
        return str_rep

    def convert(self, response: str) -> JudgeResponse:
        try:
            # Parse JSON response
            parsed = json.loads(response.strip())

            # Extract answer and reasoning
            if not isinstance(parsed, dict):
                raise ValueError(f"Expected JSON object, got {type(parsed)}")

            if "answer" not in parsed:
                raise ValueError("Missing 'answer' field in response")

            if "reasoning" not in parsed:
                raise ValueError("Missing 'reasoning' field in response")

            # Convert and validate answer
            converted_answer = self.option_type(parsed["answer"])
            if converted_answer not in self.options:
                raise ValueError(f"Invalid answer: {parsed['answer']}; expected one of {self.options}")

            reasoning = str(parsed["reasoning"])
            return JudgeResponse(answer=converted_answer, reasoning=reasoning)

        except Exception as e:
            raise ValueError(f"Error parsing response: {response}. Error: {e}")

    def to_dict(self):
        return {"options": self.options, "meanings": self.meanings, "base_str": self.base_str, "reasoning_str": self.reasoning_str}

    @classmethod
    def from_dict(cls, data: dict):
        return cls(data["options"], data["meanings"], data["base_str"], data["reasoning_str"])


class DiscreteJudgeResponseFormat(JudgeResponseFormat):
    def make_base_str(self):
        return f"{self.base_str} The 'answer' field must EXACTLY ONE of the following options: {self.options} (type {self.option_type.__name__}). {self.reasoning_str}"

    def make_meanings_str(self):
        if self.meanings is not None:
            return f"\nThe meaning of each answer option is: {', '.join([f'{option} (meaning {self.meanings[option]})' for option in self.options])}"
        return ""

class ContinuousJudgeResponseFormat(JudgeResponseFormat):
    def __post_init__(self):
        assert len(self.options) == 2, "Continuous judge response format must have exactly 2 options -- lower and upper bounds"

    def make_base_str(self):
        return f"{self.base_str} The 'answer' field must be between {self.options[0]} and {self.options[1]} (type {self.option_type.__name__}). {self.reasoning_str}"

    def make_meanings_str(self):
        if self.meanings is not None:
            return f"\nThe meaning of the lower bound {self.options[0]} is: {self.meanings[self.options[0]]}. The meaning of the upper bound {self.options[1]} is: {self.meanings[self.options[1]]}."
        return ""

binary_responses = {1.0: "yes", 0.0: "no"}
binary_judge_response_format = DiscreteJudgeResponseFormat(list(binary_responses.keys()), meanings=binary_responses)

unit_vector_responses = {0.0: "lower", 1.0: "higher"}
unit_vector_judge_response_format = ContinuousJudgeResponseFormat(list(unit_vector_responses.keys()), meanings=unit_vector_responses)
