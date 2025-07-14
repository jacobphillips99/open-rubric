import asyncio
import json
import string
from dataclasses import dataclass
from typing import Any, Optional
from verifiers.rewards.reward import Reward
from openai import OpenAI
from verifiers.parsers.parser import Parser

@dataclass
class JudgeResponse:
    answer: Any
    reasoning: str

class JudgeResponseFormat:
    def __init__(self, options: list[Any], meanings: Optional[dict[Any, str]] = None):
        self.options = options
        self.option_type = type(options[0])
        self.meanings = meanings
        assert all(isinstance(item, self.option_type) for item in options), f"Answer format must be a list of {self.option_type}; got {options} with types {[type(item) for item in options]}"
        if meanings is not None:
            assert all(k in options for k in meanings.keys()), f"All keys in meanings must be in options; got {meanings.keys()} not in {options}"

    def __str__(self):
        base_str = f"Respond with just a JSON object containing two fields: 'answer' and 'reasoning'. The 'answer' field must be EXACTLY one of these options: {self.options} (type {self.option_type.__name__}). The 'reasoning' field should contain your explanation for the answer."
        if self.meanings is not None:
            base_str += f"\nThe meaning of each answer option is: {', '.join([f'{option} (meaning {self.meanings[option]})' for option in self.options])}"
        base_str += f"\n\nExample format: {{\"answer\": {self.options[0]}, \"reasoning\": \"Your explanation here\"}}"
        return base_str

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
            breakpoint()
        # except json.JSONDecodeError as e:
        #     raise ValueError(f"Invalid JSON response: {response}. Error: {e}")
        # except (KeyError, TypeError, ValueError) as e:
        #     raise ValueError(f"Error parsing response: {response}. Error: {e}")

binary_responses = {1.0: "yes", 0.0: "no"}
binary_judge_response_format = JudgeResponseFormat(list(binary_responses.keys()), meanings=binary_responses)


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
            breakpoint()
            judge_answer = judge_response.choices[0].message.content
            judge_result = self.judge_response_format.convert(judge_answer)
        except Exception as e:
            print(f"Error in judge_rewarder: {e}")
            breakpoint()
        
        return judge_result

        

class BinaryJudgeRewarder(JudgeRewarder):
    def __init__(self, judge_prompt: str, judge_client: OpenAI | None = None, judge_model: str = "gpt-4.1-nano", parser: Parser = Parser(), **kwargs):
        super().__init__(judge_prompt, binary_judge_response_format, judge_client, judge_model, parser, **kwargs)
