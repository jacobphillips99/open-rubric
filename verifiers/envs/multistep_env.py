import asyncio
from copy import deepcopy
from typing import Any, Dict, List, Tuple, Union

from openai import OpenAI

from verifiers.envs.multiturn_env import MultiTurnEnv
from verifiers.envs.singleturn_env import SingleTurnEnv
from verifiers.rubrics.multistep.enums import EvaluationMode
from verifiers.rubrics.multistep.multistep_rubric import MultiStepRubric
from verifiers.rubrics.multistep.scenario import Scenario

class MultiStepSingleTurnEnv(SingleTurnEnv):
    pass

class MultiStepMultiTurnEnv(MultiTurnEnv):
    """Turn-based environment that follows the multistep workflow layer by layer."""

    def __init__(self,
                 multistep_rubric: MultiStepRubric,
                 max_turns: int = 10,
                 rubric_mode: EvaluationMode = EvaluationMode.REFERENCE_GUIDED,
                 **kwargs):
        # Prepare adapter before calling parent constructor.
        super().__init__(max_turns=max_turns, rubric=multistep_rubric, **kwargs)
        self.ms_rubric = multistep_rubric
        self.rubric_mode = rubric_mode

    def is_completed(self, messages: List[Dict[str, Any]], state: Dict[str, Any], **kwargs) -> bool:
        # TODO: Implement this
        return False

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
        # Build a scenario using the entire conversation so far.
        if not messages:
            raise ValueError("messages should contain at least the initial user prompt")
        initial_user_prompt = messages[0]["content"]
        # Assume last assistant message is the model reply we want to grade.
        last_assistant_msg = ""
        for m in reversed(messages):
            if m["role"] == "assistant":
                last_assistant_msg = m["content"]
                break

        # Evaluate current level using reference-guided mode.
        level_idx = state["level_idx"]
        active_reqs = state["active_reqs"]
        # Flatten scenario answer dicts so each value is a scalar (e.g., 1.0).
        raw_answers_gt = state["answers_gt"]
        answers_gt = {k: (v["answer"] if isinstance(v, dict) else v) for k, v in raw_answers_gt.items()}


        tmp_scenario = Scenario(prompt=initial_user_prompt, completion=last_assistant_msg, answers=answers_gt)

        # Evaluate current level using reference-guided mode.
        level_idx = state["level_idx"]
        active_reqs = state["active_reqs"]
        answers_gt = state["answers_gt"]
        revealed_info_set = state.get("revealed_info", set())

        # Use synchronous wrapper (handle nested event loops)
        try:
            # Try to get the current event loop
            asyncio.get_running_loop()
            # We're in an async context, so we need to handle this differently
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    self.ms_rubric.evaluate_reference_guided(tmp_scenario, ground_truth_answers=answers_gt)
                )
                eval_state = future.result()
        except RuntimeError:
            # No event loop running, safe to use asyncio.run
            eval_state = asyncio.run(
                self.ms_rubric.evaluate_reference_guided(tmp_scenario, ground_truth_answers=answers_gt)
            )

        # Extract model scores for this level.  If evaluate_reference_guided did not
        # compute the current level (e.g. no gt answers), fallback to empty dict.
        level_scores: Dict[str, float] = eval_state.get(level_idx, {}) if isinstance(eval_state, dict) else {}

        # Determine next requirements based on dependency map and the *ground truth* answers.
        next_reqs: List[str] = []
        for req_name, score in level_scores.items():
            req = self.ms_rubric.name_to_req[req_name]
            if not req.terminal() and req.dependencies is not None and score in req.dependencies:
                next_reqs.extend(req.dependencies[score])

        next_reqs = list(set(next_reqs))

        # Collect revealed information from just-satisfied requirements
        revealed_info_lines = []
        revealed_info_data = state.get("revealed_info_data", {})

        # Process revealed information based on current level scores
        if revealed_info_data:
            for req_name, score in level_scores.items():
                if req_name in revealed_info_data:
                    score_key = str(float(score))
                    if score_key in revealed_info_data[req_name]:
                        info_key = f"{req_name}_{score_key}"
                        if info_key not in revealed_info_set:
                            revealed_info_lines.append(f"📋 New Information: {revealed_info_data[req_name][score_key]}")
                            revealed_info_set.add(info_key)

        # Craft environment message with revealed information and follow-up questions
        content_lines = []

        # Add any revealed information first
        if revealed_info_lines:
            content_lines.extend(revealed_info_lines)
            content_lines.append("")  # Add blank line for separation

        if next_reqs:
            for r in next_reqs:
                req = self.ms_rubric.name_to_req[r]
                # Provide any prior reasoning we have about this requirement
                reasoning = ""
                if isinstance(answers_gt.get(r), dict):
                    reasoning = answers_gt[r].get("reasoning", "")
                if reasoning:
                    content_lines.append(f"Background ({r}): {reasoning}")
                content_lines.append(f"Question ({r}): {req.question}")
            content = "\n".join(content_lines)
        else:
            if content_lines:
                content = "\n".join(content_lines + ["No further information is available.  You may conclude."])
            else:
                content = "No further information is available.  You may conclude."

        # Update state
        if not next_reqs:
            state["finished"] = True
        else:
            state["level_idx"] = level_idx + 1
            state["active_reqs"] = next_reqs

        # Update revealed information in state
        state["revealed_info"] = revealed_info_set

        return {"role": "user", "content": content}, state

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
        # our custom is_completed/env_response hooks.

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
            messages.append(env_msg)
            completion.append(env_msg)
        return completion, state
