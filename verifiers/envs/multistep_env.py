import asyncio
from copy import deepcopy
from typing import Any, Dict, List, Tuple, Union

from openai import OpenAI

from verifiers.envs.multiturn_env import MultiTurnEnv
from verifiers.envs.singleturn_env import SingleTurnEnv

from verifiers.rubrics.multistep.multistep_rubric import MultiStepRubric
from verifiers.rubrics.multistep.scenario import Scenario

class MultiStepSingleTurnEnv(SingleTurnEnv):
    """
    Single-turn environment for use with MultiStepRubric.

    This is functionally identical to SingleTurnEnv, but provides semantic clarity
    when using MultiStepRubric in single-turn scenarios. In single-turn mode,
    the MultiStepRubric evaluates requirements against the final model response,
    following dependency paths based on ground truth answers.
    """
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
            "progression": [],  # Track chronological progression of the workflow
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

    def _add_progression_step(self, state: Dict[str, Any], turn: int, step_type: str, **data) -> None:
        """Add a step to the progression tracking."""
        state["progression"].append({
            "turn": turn,
            "step_type": step_type,
            **data
        })

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

        # Record initial prompt
        turn = 0
        self._add_progression_step(state, turn, "initial_prompt",
                                  content=prompt if isinstance(prompt, str) else str(prompt),
                                  state=self._capture_state_snapshot(state))

        # Main conversation loop
        is_completed = False
        completion: List[Dict[str, Any]] = []

        while not is_completed:
            if self.is_completed(messages, state):
                break

            # Get model response
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

            self._add_progression_step(state, turn, "assistant_response", content=model_reply)

            if self.is_completed(messages, state) or turn >= self.max_turns:
                break

            # Get environment response with state tracking
            state_before = self._capture_state_snapshot(state)
            env_msg, state = self.env_response(messages, state)
            state_after = self._capture_state_snapshot(state)

            self._add_progression_step(state, turn, "rubric_evaluation",
                                     state_before=state_before,
                                     state_after=state_after)

            # Add environment message if it has content
            if env_msg.get("content") is not None:
                messages.append(env_msg)
                completion.append(env_msg)
                self._add_progression_step(state, turn, "env_response", content=env_msg["content"])

        return completion, state

    def _capture_state_snapshot(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Capture a clean snapshot of state without progression data."""
        return {k: v for k, v in state.items() if k != "progression"}
# TODO clean up messy state tracking
