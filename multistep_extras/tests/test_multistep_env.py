"""
Enhanced test for the refactored MultiStepMultiTurnEnv with improved diagnostics.

This test demonstrates the new architecture and provides detailed diagnostics
for workflow progression, state management, and rubric evaluation.
"""

import os
from typing import Any, Dict, List

from datasets import Dataset
from openai import OpenAI

from multistep_extras.example_rubrics import get_workflow
from multistep_extras.utils.print_utils import (Colors, print_assistant,
                                                print_debug, print_environment,
                                                print_error, print_header,
                                                print_info, print_process,
                                                print_rubric, print_score,
                                                print_section, print_state,
                                                print_success)
from verifiers.envs.multistep_env import MultiStepMultiTurnEnv
from verifiers.rewards.judge_reward import JUDGE_PROMPT, BinaryJudgeRewarder
from verifiers.rubrics.multistep.multistep_rubric import MultiStepRubric
from verifiers.rubrics.multistep.requirement import Requirement
from verifiers.rubrics.multistep.reward_strategies import \
    LevelWeightedRewardStrategy
from verifiers.rubrics.multistep.scenario import Scenario


def _truncate_content(content: str, max_length: int) -> str:
    """Helper to truncate content with ellipsis if needed."""
    if len(content) > max_length:
        return content[:max_length] + "..."
    return content


def _print_state_transitions(state_before: dict, state_after: dict) -> None:
    """Analyze and print state transitions between before/after states."""
    level_change = state_after["level_idx"] - state_before["level_idx"]
    req_changes = set(state_after["active_reqs"]) - set(state_before["active_reqs"])
    completed_reqs = set(state_before["active_reqs"]) - set(state_after["active_reqs"])
    new_revealed = state_after.get("revealed_info", set()) - state_before.get(
        "revealed_info", set()
    )

    if level_change > 0:
        print_score(
            f"LEVEL PROGRESSION: {state_before['level_idx']} → {state_after['level_idx']} (+{level_change})"
        )

    if completed_reqs:
        print_success(f"COMPLETED REQUIREMENTS: {list(completed_reqs)}")

    if req_changes:
        print_process(f"NEW ACTIVE REQUIREMENTS: {list(req_changes)}")

    if new_revealed:
        print_info(f"NEW INFORMATION REVEALED: {list(new_revealed)}")

    # Show judge evaluation results from last_evaluation_results if available
    last_results = state_after.get("last_evaluation_results", {})
    if last_results:
        print_rubric("JUDGE EVALUATIONS:")
        for req_name, result_data in last_results.items():
            if isinstance(result_data, dict):
                answer = result_data.get("answer", "N/A")
                reasoning = result_data.get("reasoning", "")
                answer_color = Colors.SUCCESS if answer == 1.0 else Colors.ERROR
                print(
                    f"   {Colors.DEBUG}• {req_name}: {answer_color}Answer={answer}{Colors.END}"
                )
                if reasoning:
                    # Truncate reasoning for display
                    reasoning_preview = _truncate_content(reasoning, 100)
                    print(
                        f"     {Colors.DEBUG}Reasoning: {reasoning_preview}{Colors.END}"
                    )
            else:
                # Handle old format or direct values
                answer_color = Colors.SUCCESS if result_data == 1.0 else Colors.ERROR
                print(
                    f"   {Colors.DEBUG}• {req_name}: {answer_color}Answer={result_data}{Colors.END}"
                )

    if state_after.get("finished", False) and not state_before.get("finished", False):
        print_success("WORKFLOW COMPLETED!")


def print_workflow_state(state: dict, rubric) -> None:
    """Print detailed workflow state information."""
    print_rubric("Current Workflow State:")
    print_state(f"Level: {state['level_idx']}")
    print_state(f"Active Requirements: {state['active_reqs']}")
    print_state(f"Finished: {state.get('finished', False)}")
    print_state(f"Revealed Info Count: {len(state.get('revealed_info', set()))}")

    # Show dependency information for active requirements
    if state["active_reqs"] and rubric is not None:
        print_debug("Dependency Information:")
        for req_name in state["active_reqs"]:
            if req_name in rubric.name_to_req:
                req = rubric.name_to_req[req_name]
                deps = req.dependencies
                terminal = req.terminal()
                print(
                    f"   {Colors.DEBUG}• {req_name}: terminal={terminal}, deps={deps}{Colors.END}"
                )


def print_conversation_analysis(
    completion: List[Dict[str, Any]],
    final_state: Dict[str, Any],
    rubric=None,
    max_content_length: int = 500,
) -> None:
    """Analyze and print the conversation flow."""
    print_header("CONVERSATION ANALYSIS")

    assistant_turns = [msg for msg in completion if msg["role"] == "assistant"]
    env_turns = [msg for msg in completion if msg["role"] == "user"]

    print_info(f"Total Messages: {len(completion)}")
    print_info(f"Assistant Turns: {len(assistant_turns)}")
    print_info(f"Environment Turns: {len(env_turns)}")
    print_workflow_state(final_state, rubric)

    print_header("MESSAGE FLOW")
    for i, msg in enumerate(completion):
        role_color = (
            Colors.ASSISTANT if msg["role"] == "assistant" else Colors.ENVIRONMENT
        )
        content_preview = _truncate_content(msg["content"], max_content_length)
        print(
            f"{role_color}{i + 1}. {msg['role'].upper()}: {content_preview}{Colors.END}"
        )


def print_workflow_progression_from_state(
    final_state: dict, rubric=None, max_content_length: int = 300
) -> None:
    """Print chronological workflow progression from state data."""

    progression = final_state.get("progression", [])
    if not progression:
        print_error("No progression data found in state!")
        print_debug(f"Available state keys: {list(final_state.keys())}")

        # Debug: let's see what's actually in the state
        print_debug("Full state contents:")
        for key, value in final_state.items():
            if isinstance(value, (dict, list)):
                print_debug(f"  {key}: {type(value)} with {len(value)} items")
                if isinstance(value, dict) and len(value) < 10:
                    for sub_key, sub_value in value.items():
                        print_debug(f"    {sub_key}: {type(sub_value)}")
            else:
                print_debug(f"  {key}: {type(value)} = {value}")

        # Try to reconstruct basic progression from available data
        print_info("Attempting to show available state information instead:")
        level_idx = final_state.get("level_idx", "unknown")
        active_reqs = final_state.get("active_reqs", [])
        finished = final_state.get("finished", False)
        revealed_info = final_state.get("revealed_info", set())

        print_info(f"Final level: {level_idx}")
        print_info(f"Final active requirements: {active_reqs}")
        print_info(f"Workflow finished: {finished}")
        print_info(f"Information revealed: {len(revealed_info)} items")
        return

    print_header("CHRONOLOGICAL WORKFLOW PROGRESSION")

    for step in progression:
        turn = step["turn"]
        step_type = step["step_type"]

        if step_type == "initial_prompt":
            print_header(f"TURN {turn}: INITIAL PROMPT")
            content_preview = _truncate_content(step["content"], max_content_length)
            print_environment(f"PROMPT: {content_preview}")
            if "state" in step:
                print_workflow_state(step["state"], rubric)

        elif step_type == "assistant_response":
            print_header(f"TURN {turn}: ASSISTANT RESPONSE")
            content_preview = _truncate_content(step["content"], max_content_length)
            print_assistant(f"RESPONSE: {content_preview}")

        elif step_type == "rubric_evaluation":
            print_header(f"TURN {turn}: RUBRIC EVALUATION & STATE CHANGE")

            # Analyze state transitions
            state_before = step.get("state_before")
            state_after = step.get("state_after")

            if state_before and state_after:
                _print_state_transitions(state_before, state_after)

            print_workflow_state(state_after, rubric)

        elif step_type == "env_response":
            print_header(f"TURN {turn}: ENVIRONMENT RESPONSE")
            if "content" in step and step["content"]:
                content_preview = _truncate_content(step["content"], max_content_length)
                print_environment(f"RESPONSE: {content_preview}")
            else:
                print_environment(
                    "No explicit environment response - letting model continue naturally"
                )


def print_evaluation_results(state: dict) -> None:
    """Print detailed evaluation results from the final state."""
    print_header("DETAILED EVALUATION RESULTS")

    evaluation_data = state.get("evaluation_results", {})
    if not evaluation_data:
        print_error("No evaluation data found in state!")
        # Try to find evaluation data in other formats
        for key, value in state.items():
            if key.isdigit() and isinstance(value, dict):
                print_info(f"Found level {key} results in state keys")
                evaluation_data[key] = value

        if not evaluation_data:
            print_error("No evaluation results found in any format!")
            return

    for level_str, level_results in evaluation_data.items():
        print_rubric(f"LEVEL {level_str} RESULTS:")

        if isinstance(level_results, dict):
            for req_name, result_data in level_results.items():
                print_debug(f"  Requirement: {req_name}")

                answer_color = (
                    Colors.SUCCESS if result_data["answer"] == 1.0 else Colors.ERROR
                )
                print(f"    {answer_color}Score: {result_data['answer']}{Colors.END}")

                if result_data["reasoning"]:
                    print(
                        f"    {Colors.DEBUG}Reasoning: {result_data['reasoning']}{Colors.END}"
                    )

        else:
            print_debug(f"    Result: {level_results}")


def test_multistep_rollout(
    client: OpenAI, model: str, requirements: list[Requirement], scenario: Scenario
):
    """Test the complete multistep rollout using the env's rollout method."""
    print_header("TESTING MULTISTEP ROLLOUT WITH REAL GPT 4.1 NANO")
    print_section("=" * 70)

    # Create rubric with first responder requirements
    rubric = MultiStepRubric(
        requirements,
        [BinaryJudgeRewarder(judge_prompt=JUDGE_PROMPT)],
        reward_strategy=LevelWeightedRewardStrategy(),
    )

    # Show rubric structure
    print_debug("Rubric Structure:")
    print_debug(f"Total Requirements: {len(rubric.requirements)}")
    print_debug(f"Levels: {len(rubric.levels)} total")
    for i, level in enumerate(rubric.levels):
        print_debug(f"- Level {i}: {level}")

    # Prepare dataset format
    answer_with_revealed_info = {
        **scenario.answers,
        "_revealed_info": scenario.revealed_info,
    }

    ds = Dataset.from_dict(
        {
            "prompt": [scenario.prompt],
            "answer": [answer_with_revealed_info],
        }
    )

    # Create environment
    env = MultiStepMultiTurnEnv(
        multistep_rubric=rubric,
        max_turns=6,
        dataset=ds,
        message_type="chat",
    )

    print_success("Environment Created Successfully")
    print_info(f"Max Turns: {env.max_turns}")
    print_info(f"Message Type: {env.message_type}")

    # Run the complete rollout with progression tracking
    print_process("Starting Complete Rollout with Real-Time Progression Tracking...")

    try:
        result = env.generate(
            inputs=ds,
            client=client,
            model=model,
            sampling_args={"temperature": 0.7, "max_tokens": 10000},
            score_rollouts=True,
        )

        completion = result["completion"][0]
        final_state = result["state"][0]

        print_success("Rollout Completed Successfully!")

        # Show chronological progression from state
        print_workflow_progression_from_state(final_state, rubric)

        # Show detailed evaluation results
        try:
            print_evaluation_results(final_state)
        except Exception as e:
            print_error(f"Could not print evaluation results: {e}")
            print_debug(f"Available final state keys: {list(final_state.keys())}")

        # Show final summary
        print_header("FINAL SUMMARY")
        assistant_turns = [msg for msg in completion if msg["role"] == "assistant"]
        env_turns = [msg for msg in completion if msg["role"] == "user"]
        print_info(f"Total Messages: {len(completion)}")
        print_info(f"Assistant Turns: {len(assistant_turns)}")
        print_info(f"Environment Turns: {len(env_turns)}")

        # Check if workflow completed properly
        if final_state.get("finished", False):
            print_success("Workflow completed successfully!")
        else:
            print_info("Workflow reached max turns without completion")

        # Show final revealed information
        revealed_info = final_state.get("revealed_info", set())
        if revealed_info:
            print_info(
                f"Information revealed during conversation: {len(revealed_info)} items"
            )
            for info in revealed_info:
                print_debug(f"  • {info}")

    except Exception as e:
        print_error(f"Error during rollout: {e}")
        import traceback

        traceback.print_exc()
        return

    print_success("Multistep rollout test completed!")


def test_state_tracking(
    client: OpenAI, requirements: list[Requirement], scenario: Scenario
):
    """Test state tracking and logging capabilities."""
    print_header("TESTING STATE TRACKING AND LOGGING")
    print_section("=" * 60)

    rubric = MultiStepRubric(
        requirements,
        [BinaryJudgeRewarder(judge_prompt=JUDGE_PROMPT)],
        reward_strategy=LevelWeightedRewardStrategy(),
    )

    answer_with_revealed_info = {
        **scenario.answers,
        "_revealed_info": scenario.revealed_info,
    }

    ds = Dataset.from_dict(
        {
            "prompt": [scenario.prompt],
            "answer": [answer_with_revealed_info],
        }
    )

    env = MultiStepMultiTurnEnv(
        multistep_rubric=rubric,
        max_turns=3,  # Shorter for testing
        dataset=ds,
        message_type="chat",
    )

    print_process("Testing initial state creation...")
    initial_state = env._initialise_state(answer_with_revealed_info)
    print_workflow_state(initial_state, rubric)

    print_process("Running short rollout for state tracking...")
    completion, final_state = env.rollout(
        client=client,
        model="gpt-4.1-nano",
        prompt=scenario.prompt,
        answer=answer_with_revealed_info,
        sampling_args={"temperature": 0.3, "max_tokens": 10000},
    )

    print_success("State tracking test completed!")

    # Show progression from state data
    print_workflow_progression_from_state(final_state, rubric)

    print_info("State progression analysis:")
    print_info(f"  Initial level: {initial_state['level_idx']}")
    print_info(f"  Final level: {final_state['level_idx']}")
    print_info(f"  Initial requirements: {initial_state['active_reqs']}")
    print_info(f"  Final requirements: {final_state['active_reqs']}")
    print_info(
        f"  Level progression: {final_state['level_idx'] - initial_state['level_idx']}"
    )
    print_info(
        f"  Progression steps captured: {len(final_state.get('progression', []))}"
    )


def main():
    """Run all enhanced tests."""
    print_header("TESTING REFACTORED MULTISTEP ENVIRONMENT")
    print_section("=" * 80)

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    model = "gpt-4.1-nano"

    # Get test scenario from first_responder module
    workflow_name = "first_responder"
    requirements, scenarios = get_workflow(workflow_name, advanced=True)
    scenario = scenarios[0]

    test_multistep_rollout(client, model, requirements, scenario)

    print_header("All tests completed!")
    print_success("Enhanced testing provides diagnostics for:")
    print_info("  • Complete workflow rollouts")
    print_info("  • State progression tracking")
    print_info("  • Real model interactions")
    print_info("  • Conversation flow analysis")


if __name__ == "__main__":
    main()
