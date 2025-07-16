import asyncio
from copy import deepcopy
from typing import Any, Dict, List, Tuple, Union

from openai import OpenAI

from verifiers.envs.multiturn_env import MultiTurnEnv
from verifiers.envs.singleturn_env import SingleTurnEnv

from verifiers.rubrics.multistep.multistep_rubric import MultiStepRubric
from verifiers.rubrics.multistep.scenario import Scenario

class MultiStepSingleTurnEnv(SingleTurnEnv):
    pass

class MultiStepMultiTurnEnv(MultiTurnEnv):
    """Turn-based environment that follows the multistep workflow layer by layer."""

    def __init__(self,
                 multistep_rubric: MultiStepRubric,
                 max_turns: int = 10,
                 **kwargs):
        # Prepare adapter before calling parent constructor.
        super().__init__(max_turns=max_turns, rubric=multistep_rubric, **kwargs)
        self.ms_rubric = multistep_rubric

    def is_completed(self, messages: List[Dict[str, Any]], state: Dict[str, Any], **kwargs) -> bool:
        """Check if the workflow is completed based on state."""
        return state.get("finished", False)

    def _initialise_state(self, answer: Any) -> Dict[str, Any]:
        """Helper to build the initial rollout state."""
        # Handle both dict answers and Scenario objects
        if hasattr(answer, 'answers'):
            # This is a Scenario object
            flat = {k: (v['answer'] if isinstance(v, dict) else v) for k, v in answer.answers.items()}
            revealed_info_data = getattr(answer, 'revealed_info', {})
        else:
            # This is a regular dict (from dataset)
            # Extract revealed_info if present, without modifying the original dict
            answer_copy = dict(answer)
            revealed_info_data = answer_copy.pop('_revealed_info', {})
            flat = {k: (v['answer'] if isinstance(v, dict) else v)
                   for k, v in answer_copy.items()
                   if not k.startswith('_')}

        return {
            "level_idx": 0,
            "active_reqs": deepcopy(self.ms_rubric.levels[0] if self.ms_rubric.levels else []),
            "answers_gt": flat,  # Ground-truth answer dict from dataset
            "finished": False,
            "revealed_info": set(),  # Track what information has been revealed
            "revealed_info_data": revealed_info_data,  # Store the revealed info mapping
        }

    def env_response(self,  # type: ignore[override]
                     messages: List[Dict[str, Any]],
                     state: Dict[str, Any],
                     **kwargs) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Get the next step in the conversation from the rubric."""
        # Delegate all workflow logic to the rubric!
        content, updated_state, is_finished = self.ms_rubric.get_next_conversation_step(
            messages, state, **kwargs
        )

        return {"role": "user", "content": content}, updated_state

    def rollout(self,
                client: OpenAI,
                model: str,
                prompt: Union[str, List[Dict[str, Any]]],
                answer: Any,
                task: str = "default",
                info: Dict[str, Any] | None = None,
                sampling_args: Dict[str, Any] | None = None,
                **kwargs) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        if sampling_args is None:
            sampling_args = {}
        if info is None:
            info = {}

        # Convert plain‐text prompt to chat format expected by MultiTurnEnv.
        if isinstance(prompt, str):
            messages = [{"role": "user", "content": prompt}]
        else:
            messages = deepcopy(prompt)

        # Initialise state before entering parent rollout loop.
        state = self._initialise_state(answer)

        # Use MultiTurnEnv.rollout implementation by delegating via deepcopy of self.
        # Unfortunately we cannot directly call super().rollout because that method
        # constructs its own loop; instead we replicate the core logic here with
        # our custom is_completed/efnv_response hooks.

        is_completed = False
        completion: List[Dict[str, Any]] = []
        turn = 0
        while not is_completed:
            if self.is_completed(messages, state):
                break
            model_reply = self.get_model_response(
                prompt=messages,
                client=client,
                model=model,
                sampling_args=sampling_args,
                message_type="chat",
            )
            messages.append({"role": "assistant", "content": model_reply})
            completion.append({"role": "assistant", "content": model_reply})
            turn += 1
            if self.is_completed(messages, state) or turn >= self.max_turns:
                break
            env_msg, state = self.env_response(messages, state)

            # Only append env_msg if it has actual content
            # None content means "let model continue naturally without explicit prompting"
            if env_msg.get("content") is not None:
                messages.append(env_msg)
                completion.append(env_msg)
        return completion, state
