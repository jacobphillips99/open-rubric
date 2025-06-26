from typing import Any, Optional
from verifiers.rewards.reward import Reward
from openai import AsyncOpenAI
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
    
binary_judge_response_format = JudgeResponseFormat([1.0, 0.0], meanings={1.0: "yes", 0.0: "no"})


class JudgeRewarder(Reward):
    def __init__(self, judge_prompt: str, judge_response_format: JudgeResponseFormat, judge_client: AsyncOpenAI | None = None, judge_model: str = "gpt-4.1-nano", parser: Parser = Parser(), **kwargs):
        super().__init__(**kwargs)
        self.judge_response_format = judge_response_format
        self.judge_prompt = judge_prompt
        self.judge_client = judge_client if judge_client is not None else AsyncOpenAI()
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
        judge_response = await self.judge_client.chat.completions.create(
            model=self.judge_model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=10,
        )
        judge_answer = judge_response.choices[0].message.content
        return self.judge_response_format.convert(judge_answer)

class BinaryJudgeRewarder(JudgeRewarder):
    def __init__(self, judge_prompt: str, judge_client: AsyncOpenAI | None = None, judge_model: str = "gpt-4.1-nano", parser: Parser = Parser(), **kwargs):
        super().__init__(judge_prompt, binary_judge_response_format, judge_client, judge_model, parser, **kwargs)
