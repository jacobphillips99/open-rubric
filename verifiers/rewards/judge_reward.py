import asyncio
from typing import Any, Optional
from verifiers.rewards.reward import Reward
from openai import OpenAI
from verifiers.parsers.parser import Parser

class JudgeResponseFormat:
    def __init__(self, options: list[Any], meanings: Optional[dict[Any, str]] = None):
        self.options = options
        self.option_type = type(options[0])
        self.meanings = meanings
        assert all(isinstance(item, self.option_type) for item in options), f"Answer format must be a list of {self.option_type}; got {options} with types {[type(item) for item in options]}"
        if meanings is not None:
            assert all(k in options for k in meanings.keys()), f"All keys in meanings must be in options; got {meanings.keys()} not in {options}"

    def __str__(self):
        base_str = f"Answer with ONLY your selection from the following options: {self.options}. Note that the options are of type {self.option_type}." 
        if self.meanings is not None:
            base_str += f"\nThe meaning of each option is: {', '.join([f'{option} (meaning {self.meanings[option]})' for option in self.options])}"
        return base_str

    def convert(self, response: Any) -> Any:
        converted_response = self.option_type(response)
        if converted_response not in self.options:
            raise ValueError(f"Invalid response: {response}; expected one of {self.options}")
        return converted_response

binary_responses = {1.0: "yes", 0.0: "no"}
binary_judge_response_format = JudgeResponseFormat(list(binary_responses.keys()), meanings=binary_responses)


class JudgeRewarder(Reward):
    def __init__(self, judge_prompt: str, judge_response_format: JudgeResponseFormat, judge_client: OpenAI | None = None, judge_model: str = "gpt-4.1-nano", parser: Parser = Parser(), **kwargs):
        super().__init__(**kwargs)
        self.judge_response_format = judge_response_format
        self.judge_prompt = judge_prompt
        self.judge_client = judge_client if judge_client is not None else OpenAI()
        self.judge_model = judge_model
        self.parser = parser

    async def __call__(self, prompt, completion, answer, **kwargs) -> float:
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
                    max_tokens=10,
                )
        try:
            judge_response = await asyncio.to_thread(_create_completion)
            judge_answer = judge_response.choices[0].message.content
            score = self.judge_response_format.convert(judge_answer)
        except Exception as e:
            print(f"Error in judge_rewarder: {e}")
            breakpoint()
        
        return score

        

class BinaryJudgeRewarder(JudgeRewarder):
    def __init__(self, judge_prompt: str, judge_client: OpenAI | None = None, judge_model: str = "gpt-4.1-nano", parser: Parser = Parser(), **kwargs):
        super().__init__(judge_prompt, binary_judge_response_format, judge_client, judge_model, parser, **kwargs)
