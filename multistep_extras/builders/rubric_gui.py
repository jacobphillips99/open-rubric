"""
Streamlit GUI for building MultiStep rubrics using the RubricBuilder.

Run with:
    streamlit run multistep_extras/builders/rubric_gui.py

This GUI allows you to build a MultiStepRubric by adding judge rewarders, requirements, and a reward strategy.
"""

import json
import traceback
from pathlib import Path
from typing import Any

import streamlit as st
import yaml

from multistep_extras.builders.builder import RubricBuilder
from verifiers.rewards.judge_reward import (JUDGE_PROMPT,
                                            JUDGE_PROMPT_VARIABLES,
                                            NAME_TO_JUDGE_REWARDER_CLASS,
                                            make_judge_rewarder)
from verifiers.rubrics.multistep.multistep_rubric import MultiStepRubric
from verifiers.rubrics.multistep.requirement import (NAME_TO_REQUIREMENT_CLASS,
                                                     make_requirement)
from verifiers.rubrics.multistep.reward_strategies import (
    NAME_TO_REWARD_STRATEGY_CLASS, make_reward_strategy)

# Default save directory
DEFAULT_SAVE_DIR = Path("example_rubrics/workflows")


def configure_page() -> None:
    """Configure the Streamlit page settings."""
    st.set_page_config(
        page_title="Rubric Builder GUI",
        page_icon="🏗️",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def initialize_session_state() -> None:
    """Initialize session state variables if they don't exist."""
    if "judge_rewarders" not in st.session_state:
        st.session_state.judge_rewarders = []
    if "requirements" not in st.session_state:
        st.session_state.requirements = []
    if "reward_strategy" not in st.session_state:
        st.session_state.reward_strategy = None

    # Create default save directory
    DEFAULT_SAVE_DIR.mkdir(parents=True, exist_ok=True)


def render_sidebar_overview() -> None:
    """Render the configuration overview in the sidebar."""
    with st.sidebar:
        st.header("📋 Rubric Preview")
        _render_judge_rewarders_overview()
        _render_requirements_overview()
        _render_reward_strategy_overview()
        st.divider()
        _render_save_load_section()
        st.divider()
        _render_clear_all_button()


def _render_save_load_section() -> None:
    """Render the enhanced save/load section with directory browsing."""
    st.subheader("💾 Save/Load")

    # Directory selection
    st.markdown("**Browse Directory:**")

    # Initialize session state for current directory
    if "current_directory" not in st.session_state:
        st.session_state.current_directory = str(DEFAULT_SAVE_DIR)

    col1, col2 = st.columns([3, 1])
    with col1:
        browse_dir = st.text_input(
            "Directory path:",
            value=st.session_state.current_directory,
            key="browse_directory_input",
            help="Enter path to browse for rubrics and scenarios",
        )

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔍 Browse"):
            st.session_state.current_directory = browse_dir
            st.rerun()

    # Scan current directory
    try:
        browse_path = Path(browse_dir)
        if browse_path.exists() and browse_path.is_dir():
            _render_directory_contents(browse_path)
        else:
            st.warning(f"Directory '{browse_dir}' does not exist or is not accessible")
    except Exception as e:
        st.error(f"Error accessing directory: {str(e)}")

    st.divider()

    # Save section (only show if there's something to save)
    if (
        st.session_state.judge_rewarders
        or st.session_state.requirements
        or st.session_state.reward_strategy
    ):
        st.markdown("**Save Current Configuration:**")

        col1, col2 = st.columns(2)
        with col1:
            save_name = st.text_input(
                "Rubric name:", placeholder="my_rubric", key="save_name_input"
            )

        with col2:
            save_dir = st.text_input(
                "Save to directory:",
                value=st.session_state.current_directory,
                key="save_directory_input",
            )

        if st.button("💾 Save Config", disabled=not save_name):
            if save_name and save_dir:
                _save_current_config_to_dir(save_name, save_dir)


def _render_directory_contents(directory: Path) -> None:
    """Render the contents of a directory with rubrics and scenarios."""
    # Scan for rubrics
    rubrics = _get_rubrics_in_directory(directory)

    # Scan for scenarios
    scenarios = _get_scenarios_in_directory(directory)

    if rubrics or scenarios:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**📋 Rubrics:**")
            if rubrics:
                for rubric_name in rubrics:
                    with st.expander(f"🏗️ {rubric_name}", expanded=False):
                        st.text(f"Path: {directory / f'{rubric_name}_config.yaml'}")
                        col_load, col_del = st.columns(2)

                        with col_load:
                            if st.button("📂 Load", key=f"load_rubric_{rubric_name}"):
                                _load_rubric_from_directory(rubric_name, directory)

                        with col_del:
                            if st.button(
                                "🗑️ Delete", key=f"delete_rubric_{rubric_name}"
                            ):
                                _delete_rubric_from_directory(rubric_name, directory)
            else:
                st.info("No rubrics found")

        with col2:
            st.markdown("**🎭 Scenarios:**")
            if scenarios:
                for scenario_file in scenarios:
                    with st.expander(f"🎯 {scenario_file['name']}", expanded=False):
                        st.text(f"Type: {scenario_file['type']}")
                        st.text(f"Count: {scenario_file['count']} scenario(s)")
                        st.text(f"Path: {scenario_file['path']}")

                        if st.button(
                            "👁️ Preview",
                            key=f"preview_scenario_{scenario_file['name']}",
                        ):
                            _preview_scenarios(scenario_file)

                        if st.button(
                            "📂 Load as Example",
                            key=f"load_scenario_{scenario_file['name']}",
                        ):
                            _load_scenarios_as_example(scenario_file)
            else:
                st.info("No scenarios found")
    else:
        st.info("No rubrics or scenarios found in this directory")


def _get_rubrics_in_directory(directory: Path) -> list[str]:
    """Get list of rubric names in a directory."""
    if not directory.exists():
        return []

    config_files = list(directory.glob("*_config.yaml"))
    rubric_names = []

    for config_file in config_files:
        name = config_file.stem.replace("_config", "")
        req_file = directory / f"{name}_requirements.yaml"
        if req_file.exists():
            rubric_names.append(name)

    return sorted(rubric_names)


def _get_scenarios_in_directory(directory: Path) -> list[dict]:
    """Get list of scenario files in a directory."""
    if not directory.exists():
        return []

    scenario_files = []

    # Look for YAML files that might contain scenarios
    yaml_files = list(directory.glob("*.yaml")) + list(directory.glob("*.yml"))

    for yaml_file in yaml_files:
        # Skip rubric files
        if "_config.yaml" in str(yaml_file) or "_requirements.yaml" in str(yaml_file):
            continue

        try:
            with open(yaml_file, "r") as f:
                data = yaml.safe_load(f)

            if isinstance(data, dict):
                if "scenarios" in data:
                    # Multiple scenarios file
                    scenario_files.append(
                        {
                            "name": yaml_file.stem,
                            "type": "Multiple scenarios",
                            "count": len(data["scenarios"]),
                            "path": yaml_file,
                            "data": data,
                        }
                    )
                elif "scenario" in data:
                    # Single scenario file
                    scenario_files.append(
                        {
                            "name": yaml_file.stem,
                            "type": "Single scenario",
                            "count": 1,
                            "path": yaml_file,
                            "data": data,
                        }
                    )
        except Exception:
            # Not a valid scenario file, skip
            continue

    return sorted(scenario_files, key=lambda x: x["name"])


def _load_rubric_from_directory(rubric_name: str, directory: Path) -> None:
    """Load a rubric from a specific directory."""
    try:
        rubric = MultiStepRubric.load(directory, rubric_name)

        # Clear current session state
        st.session_state.judge_rewarders = []
        st.session_state.requirements = []
        st.session_state.reward_strategy = None

        # Store the loaded objects directly (already instantiated and validated)
        st.session_state.judge_rewarders = list(rubric.judge_options)
        st.session_state.requirements = list(rubric.requirements)
        st.session_state.reward_strategy = rubric.reward_strategy

        st.success(f"✅ Loaded rubric '{rubric_name}' from {directory}!")
        st.rerun()

    except Exception as e:
        st.error(f"Error loading rubric: {str(e)}\n{traceback.format_exc()}")


def _delete_rubric_from_directory(rubric_name: str, directory: Path) -> None:
    """Delete a rubric from a specific directory."""
    try:
        config_file = directory / f"{rubric_name}_config.yaml"
        req_file = directory / f"{rubric_name}_requirements.yaml"

        if config_file.exists():
            config_file.unlink()
        if req_file.exists():
            req_file.unlink()

        st.success(f"✅ Deleted rubric '{rubric_name}' from {directory}!")
        st.rerun()

    except Exception as e:
        st.error(f"Error deleting rubric: {str(e)}")


def _save_current_config_to_dir(save_name: str, save_dir: str) -> None:
    """Save the current configuration to a specific directory."""
    try:
        save_path = Path(save_dir)
        save_path.mkdir(parents=True, exist_ok=True)

        # Build the rubric first
        rubric = _build_rubric()

        # Save the rubric
        rubric.save(save_path, save_name)

        st.success(f"✅ Saved configuration as '{save_name}' to {save_path}!")
        st.rerun()

    except Exception as e:
        st.error(f"Error saving configuration: {str(e)}")


def _preview_scenarios(scenario_file: dict) -> None:
    """Preview scenarios in a popup."""
    from verifiers.rubrics.multistep.scenario import Scenario

    try:
        if scenario_file["type"] == "Multiple scenarios":
            scenarios = Scenario.load_multiple(scenario_file["path"])

            st.markdown("**Scenarios Preview:**")
            for i, scenario in enumerate(scenarios[:3]):  # Show first 3
                with st.expander(
                    f"Scenario {i + 1}: {scenario.name or 'Unnamed'}", expanded=False
                ):
                    st.markdown(
                        f"**Description:** {scenario.description or 'No description'}"
                    )
                    st.markdown(f"**Prompt:** {scenario.prompt[:200]}...")
                    if scenario.answers:
                        st.markdown(f"**Answer keys:** {list(scenario.answers.keys())}")

            if len(scenarios) > 3:
                st.info(f"... and {len(scenarios) - 3} more scenarios")

        else:  # Single scenario
            scenario = Scenario.load(scenario_file["path"])
            st.markdown("**Scenario Preview:**")
            st.markdown(f"**Name:** {scenario.name or 'Unnamed'}")
            st.markdown(f"**Description:** {scenario.description or 'No description'}")
            st.markdown(f"**Prompt:** {scenario.prompt}")
            if scenario.answers:
                st.markdown(f"**Answer keys:** {list(scenario.answers.keys())}")

    except Exception as e:
        st.error(f"Error previewing scenarios: {str(e)}")


def _load_scenarios_as_example(scenario_file: dict) -> None:
    """Load scenarios as examples (for demonstration/testing)."""
    from verifiers.rubrics.multistep.scenario import Scenario

    try:
        if scenario_file["type"] == "Multiple scenarios":
            scenarios = Scenario.load_multiple(scenario_file["path"])
        else:
            scenarios = [Scenario.load(scenario_file["path"])]

        # Store in session state for potential use
        st.session_state.loaded_scenarios = scenarios

        st.success(f"✅ Loaded {len(scenarios)} scenario(s) as examples!")
        st.info(
            "Scenarios are now available in session state for testing with your rubric."
        )

    except Exception as e:
        st.error(f"Error loading scenarios: {str(e)}")


# Legacy functions for backward compatibility
def _get_saved_rubrics() -> list[str]:
    """Get list of saved rubric names in default directory."""
    return _get_rubrics_in_directory(DEFAULT_SAVE_DIR)


def _load_rubric_to_session(rubric_name: str) -> None:
    """Load a saved rubric from default directory into the session state."""
    _load_rubric_from_directory(rubric_name, DEFAULT_SAVE_DIR)


def _save_current_config(save_name: str) -> None:
    """Save the current configuration to default directory."""
    _save_current_config_to_dir(save_name, str(DEFAULT_SAVE_DIR))


def _delete_saved_rubric(rubric_name: str) -> None:
    """Delete a saved rubric from default directory."""
    _delete_rubric_from_directory(rubric_name, DEFAULT_SAVE_DIR)


def _render_judge_rewarders_overview() -> None:
    """Render the judge rewarders overview section."""
    if st.session_state.judge_rewarders:
        with st.expander(
            f"🔨 Judge Rewarders ({len(st.session_state.judge_rewarders)})",
            expanded=False,
        ):
            for i, judge in enumerate(st.session_state.judge_rewarders):
                judge_name = getattr(judge, "name", "") or ""
                type_info = (
                    f"`{judge.__class__.__name__.replace('JudgeRewarder', '').lower()}`"
                )
                if judge_name:
                    st.markdown(f"**{i + 1}.** `{judge_name}` ({type_info})")
                else:
                    st.markdown(f"**{i + 1}.** {type_info}")

                # Combine all info into a single text block to avoid blank lines
                info_lines = []
                info_lines.append(f"Model: {judge.judge_model}")

                # Show response format if configured
                if hasattr(judge, "judge_response_format"):
                    rf = judge.judge_response_format
                    if "Discrete" in rf.__class__.__name__:
                        options_str = ", ".join(map(str, rf.options))
                        info_lines.append(f"Format: Discrete [{options_str}]")
                        if rf.meanings:
                            # Show first 2 meanings with better formatting
                            meanings_items = list(rf.meanings.items())[:2]
                            meanings_preview = ", ".join(
                                [f"{k}: {v}" for k, v in meanings_items]
                            )
                            if len(rf.meanings) > 2:
                                meanings_preview += f", +{len(rf.meanings) - 2} more"
                            info_lines.append(f"Meanings: {meanings_preview}")
                    elif "Continuous" in rf.__class__.__name__:
                        bounds = rf.options
                        info_lines.append(
                            f"Format: Continuous [{bounds[0]} to {bounds[1]}]"
                        )

                st.text("\n".join(info_lines))
    else:
        st.subheader("🔨 Judge Rewarders")
        st.info("No judges configured yet")


def _render_requirements_overview() -> None:
    """Render the requirements overview section."""
    if st.session_state.requirements:
        with st.expander(
            f"📋 Requirements ({len(st.session_state.requirements)})", expanded=False
        ):
            for i, req in enumerate(st.session_state.requirements):
                st.markdown(f"**{i + 1}.** `{req.name}`")

                # Combine all info into a single caption to avoid blank lines
                info_lines = []
                info_lines.append(
                    f"Type: {req.__class__.__name__.replace('Requirement', '').lower()}"
                )

                # Show judge assignment
                judge_name = getattr(req, "judge_name", "") or ""
                if judge_name:
                    info_lines.append(f"Judge: {judge_name}")

                # Show dependency info
                if req.dependencies:
                    # Show actual dependency mappings with better formatting
                    dep_info = []
                    for answer, deps in req.dependencies.items():
                        if deps:
                            # Truncate long dependency lists
                            if len(deps) > 2:
                                deps_preview = (
                                    f"{', '.join(deps[:2])}, +{len(deps) - 2} more"
                                )
                            else:
                                deps_preview = ", ".join(deps)
                            dep_info.append(f"{answer} → {deps_preview}")
                        else:
                            dep_info.append(f"{answer} → terminal")

                    # Show up to 2 dependency mappings to keep it readable
                    if len(dep_info) > 2:
                        displayed_deps = dep_info[:2] + [
                            f"+{len(dep_info) - 2} more answers"
                        ]
                    else:
                        displayed_deps = dep_info

                    info_lines.append(f"Dependencies: {', '.join(displayed_deps)}")
                else:
                    info_lines.append("Terminal requirement")

                st.text("\n".join(info_lines))
    else:
        st.subheader("📋 Requirements")
        st.info("No requirements configured yet")


def _render_reward_strategy_overview() -> None:
    """Render the reward strategy overview section."""
    if st.session_state.reward_strategy:
        strategy = st.session_state.reward_strategy
        with st.expander("🎯 Reward Strategy (1)", expanded=False):
            st.markdown(f"**Type:** `{strategy.name}`")

            # Show strategy parameters
            params = {}
            for attr_name in dir(strategy):
                if (
                    not attr_name.startswith("_")
                    and not callable(getattr(strategy, attr_name))
                    and attr_name not in ["name", "calculate_reward"]
                ):
                    params[attr_name] = getattr(strategy, attr_name)

            if params:
                info_lines = []
                for param, value in params.items():
                    info_lines.append(f"{param}: {value}")
                st.text("\n".join(info_lines))
            else:
                st.text("No additional parameters")
    else:
        st.subheader("🎯 Reward Strategy")
        st.info("No strategy configured yet")


def _render_clear_all_button() -> None:
    """Render the clear all configuration button."""
    if st.button("🗑️ Clear All Configuration", type="secondary"):
        st.session_state.judge_rewarders = []
        st.session_state.requirements = []
        st.session_state.reward_strategy = None
        st.rerun()


def render_judge_rewarders_tab() -> None:
    """Render the judge rewarders configuration tab."""
    st.header("Judge Rewarders")
    st.markdown("Configure how responses will be evaluated by judges.")

    _render_judge_rewarder_form()
    _render_existing_judge_rewarders()


def _render_judge_rewarder_form() -> None:
    """Render the form for adding new judge rewarders."""
    col1, col2 = st.columns([1, 1])

    with col1:
        judge_type = st.selectbox(
            "Judge Type",
            options=list(NAME_TO_JUDGE_REWARDER_CLASS.keys()),
            key="new_judge_type",
        )
        judge_model = st.text_input(
            "Judge Model", value="gpt-4.1-nano", key="new_judge_model"
        )
        judge_name = st.text_input(
            "Judge Name (optional)",
            placeholder="e.g., accuracy_judge, style_judge",
            key="new_judge_name",
            help="Optional name to identify this judge for specific requirements",
        )

    with col2:
        judge_prompt = st.text_area(
            f"Judge Prompt Template -- Must contain the following variables: {JUDGE_PROMPT_VARIABLES}",
            value=JUDGE_PROMPT.strip(),
            height=120,
            key="new_judge_prompt",
        )

    # Response format configuration for discrete/continuous judges
    response_format_config = None
    if judge_type in ["discrete", "continuous"]:
        response_format_config = _render_response_format_config(judge_type)

    if st.button("Add Judge Rewarder"):
        _add_judge_rewarder(
            judge_type, judge_model, judge_prompt, response_format_config, judge_name
        )


def _render_response_format_config(judge_type: str) -> dict:
    """Render the response format configuration for discrete/continuous judges."""
    st.markdown("**Response Format Configuration:**")

    if judge_type == "discrete":
        st.markdown(
            "*Configure the discrete options and their meanings (e.g., Likert scale)*"
        )

        col1, col2 = st.columns([1, 1])

        with col1:
            # Options input
            options_input = st.text_input(
                "Options (comma-separated)",
                placeholder="1, 2, 3, 4, 5",
                key="discrete_options",
                help="Enter the discrete values separated by commas. Numbers will be converted to float.",
            )

        with col2:
            # Meanings input
            meanings_input = st.text_area(
                "Meanings (JSON format)",
                placeholder='{"1": "terrible", "2": "bad", "3": "fine", "4": "good", "5": "great"}',
                key="discrete_meanings",
                height=80,
                help="Optional: Map each option to its meaning using JSON format.",
            )

    elif judge_type == "continuous":
        st.markdown("*Configure the continuous range bounds and their meanings*")

        col1, col2 = st.columns([1, 1])

        with col1:
            lower_bound = st.number_input(
                "Lower Bound", value=0.0, step=0.1, key="continuous_lower"
            )
            upper_bound = st.number_input(
                "Upper Bound", value=1.0, step=0.1, key="continuous_upper"
            )

        with col2:
            meanings_input = st.text_area(
                "Meanings (JSON format)",
                placeholder='{"0.0": "poor", "1.0": "excellent"}',
                key="continuous_meanings",
                height=80,
                help="Optional: Map the bounds to their meanings using JSON format.",
            )

    # Parse and return the config
    config = {"type": judge_type}

    if judge_type == "discrete":
        if options_input.strip():
            try:
                # Parse options
                options_str = options_input.strip().split(",")
                options = [float(opt.strip()) for opt in options_str]
                config["options"] = options

                # Parse meanings if provided
                if meanings_input.strip():
                    meanings_dict = json.loads(meanings_input.strip())
                    # Convert keys to float to match options
                    meanings = {float(k): v for k, v in meanings_dict.items()}
                    config["meanings"] = meanings

            except (ValueError, json.JSONDecodeError) as e:
                st.error(f"Error parsing discrete format: {str(e)}")
                return None

    elif judge_type == "continuous":
        config["options"] = [lower_bound, upper_bound]

        if meanings_input.strip():
            try:
                meanings_dict = json.loads(meanings_input.strip())
                # Convert keys to float to match bounds
                meanings = {float(k): v for k, v in meanings_dict.items()}
                config["meanings"] = meanings
            except json.JSONDecodeError as e:
                st.error(f"Error parsing continuous meanings: {str(e)}")
                return None

    return config


def _add_judge_rewarder(
    judge_type: str,
    judge_model: str,
    judge_prompt: str,
    response_format_config: dict = None,
    judge_name: str = None,
) -> None:
    """Add a new judge rewarder to the session state."""
    if not all(var in judge_prompt for var in JUDGE_PROMPT_VARIABLES):
        st.error(
            f"Judge prompt must contain the following variables: {JUDGE_PROMPT_VARIABLES}"
        )
        return

    try:
        # Prepare kwargs for make_judge_rewarder
        judge_kwargs = {
            "judge_model": judge_model,
            "judge_prompt": judge_prompt,
        }

        # Add response format config if provided
        if response_format_config:
            judge_kwargs["response_format"] = response_format_config

        # Add judge name if provided
        if judge_name:
            judge_kwargs["name"] = judge_name

        # Instantiate the judge rewarder - this will validate the configuration
        new_judge = make_judge_rewarder(judge_type, **judge_kwargs)

    except Exception as e:
        st.error(f"Error creating judge rewarder: {str(e)}")
        return

    st.session_state.judge_rewarders.append(new_judge)
    st.success("Judge rewarder added successfully!")
    st.rerun()


def _update_judge_rewarder(
    index: int,
    new_model: str,
    new_prompt: str,
    new_name: str = None,
) -> None:
    """Update an existing judge rewarder."""
    if not new_model or not new_prompt:
        st.error("Model and prompt are required!")
        return

    if not all(var in new_prompt for var in JUDGE_PROMPT_VARIABLES):
        st.error(
            f"Judge prompt must contain the following variables: {JUDGE_PROMPT_VARIABLES}"
        )
        return

    try:
        # Get the current judge to preserve its type and response format
        current_judge = st.session_state.judge_rewarders[index]
        judge_type = current_judge.__class__.__name__.replace(
            "JudgeRewarder", ""
        ).lower()

        # Prepare kwargs for make_judge_rewarder
        judge_kwargs = {
            "judge_model": new_model,
            "judge_prompt": new_prompt,
        }

        # Preserve existing response format if it exists
        if hasattr(current_judge, "judge_response_format"):
            rf = current_judge.judge_response_format

            # Reconstruct response format config
            response_format_config = {"type": judge_type}
            response_format_config["options"] = rf.options
            if rf.meanings:
                response_format_config["meanings"] = rf.meanings

            judge_kwargs["response_format"] = response_format_config

        # Add judge name if provided
        if new_name:
            judge_kwargs["name"] = new_name

        # Create the updated judge rewarder
        updated_judge = make_judge_rewarder(judge_type, **judge_kwargs)

        # Replace the judge rewarder
        st.session_state.judge_rewarders[index] = updated_judge
        st.success("Judge rewarder updated successfully!")
        st.rerun()

    except Exception as e:
        st.error(f"Error updating judge rewarder: {str(e)}")
        return


def _update_judge_response_format(
    index: int,
    judge_type: str,
    options_input: str,
    meanings_input: str,
) -> None:
    """Update the response format of an existing judge rewarder."""
    try:
        # Get the current judge
        current_judge = st.session_state.judge_rewarders[index]

        # Parse the new response format configuration
        config = {"type": judge_type}

        if judge_type == "discrete":
            if options_input.strip():
                options_str = options_input.strip().split(",")
                options = [float(opt.strip()) for opt in options_str]
                config["options"] = options

                # Parse meanings if provided
                if meanings_input.strip():
                    meanings_dict = json.loads(meanings_input.strip())
                    # Convert keys to float to match options
                    meanings = {float(k): v for k, v in meanings_dict.items()}
                    config["meanings"] = meanings
            else:
                st.error("Options are required for discrete format!")
                return

        elif judge_type == "continuous":
            bounds = [float(x.strip()) for x in options_input.split(",")]
            if len(bounds) != 2:
                st.error("Continuous format requires exactly two bounds!")
                return
            config["options"] = bounds

            if meanings_input.strip():
                meanings_dict = json.loads(meanings_input.strip())
                # Convert keys to float to match bounds
                meanings = {float(k): v for k, v in meanings_dict.items()}
                config["meanings"] = meanings

        # Reconstruct the judge with new response format
        judge_type_name = current_judge.__class__.__name__.replace(
            "JudgeRewarder", ""
        ).lower()

        judge_kwargs = {
            "judge_model": current_judge.judge_model,
            "judge_prompt": current_judge.judge_prompt,
            "response_format": config,
        }

        # Preserve judge name if it exists
        if hasattr(current_judge, "name") and current_judge.name:
            judge_kwargs["name"] = current_judge.name

        # Create the updated judge rewarder
        updated_judge = make_judge_rewarder(judge_type_name, **judge_kwargs)

        # Replace the judge rewarder
        st.session_state.judge_rewarders[index] = updated_judge
        st.success("Judge response format updated successfully!")
        st.rerun()

    except (ValueError, json.JSONDecodeError) as e:
        st.error(f"Error parsing response format: {str(e)}")
        return
    except Exception as e:
        st.error(f"Error updating judge response format: {str(e)}")
        return


def _render_existing_judge_rewarders() -> None:
    """Render the list of existing judge rewarders."""
    for i, judge in enumerate(st.session_state.judge_rewarders):
        judge_display_name = getattr(judge, "name", None) or judge.__class__.__name__
        with st.expander(f"Judge {i + 1}: {judge_display_name}", expanded=False):
            col1, col2, col3 = st.columns([2, 2, 1])

            with col1:
                st.text_input(
                    "Type",
                    value=judge.__class__.__name__,
                    disabled=True,
                    key=f"judge_type_{i}",
                )
                updated_model = st.text_input(
                    "Model",
                    value=judge.judge_model,
                    key=f"judge_model_{i}",
                )
                updated_name = st.text_input(
                    "Name",
                    value=getattr(judge, "name", "") or "",
                    key=f"judge_name_{i}",
                    help="Optional judge name for specific matching",
                )

            with col2:
                updated_prompt = st.text_area(
                    "Prompt",
                    value=judge.judge_prompt,
                    height=100,
                    key=f"judge_prompt_{i}",
                )

            with col3:
                st.markdown("<br>", unsafe_allow_html=True)  # Add some spacing

                if st.button("💾 Update", key=f"update_judge_{i}"):
                    _update_judge_rewarder(
                        i, updated_model, updated_prompt, updated_name
                    )

                if st.button("🗑️ Remove", key=f"remove_judge_{i}"):
                    st.session_state.judge_rewarders.pop(i)
                    st.rerun()

            # Show and allow editing response format details if configured
            if hasattr(judge, "judge_response_format"):
                st.markdown("**Response Format:**")
                rf = judge.judge_response_format
                judge_type = rf.__class__.__name__.replace(
                    "JudgeResponseFormat", ""
                ).lower()

                col_rf1, col_rf2 = st.columns(2)
                with col_rf1:
                    st.text_input(
                        "Format Type",
                        value=judge_type,
                        disabled=True,
                        key=f"judge_format_type_{i}",
                    )

                    if judge_type == "discrete":
                        options_str = ", ".join(map(str, rf.options))
                        updated_options = st.text_input(
                            "Options (comma-separated)",
                            value=options_str,
                            key=f"judge_options_{i}",
                            help="Enter discrete values separated by commas",
                        )
                    elif judge_type == "continuous":
                        col_lower, col_upper = st.columns(2)
                        with col_lower:
                            updated_lower = st.number_input(
                                "Lower Bound",
                                value=float(rf.options[0]),
                                step=0.1,
                                key=f"judge_lower_{i}",
                            )
                        with col_upper:
                            updated_upper = st.number_input(
                                "Upper Bound",
                                value=float(rf.options[1]),
                                step=0.1,
                                key=f"judge_upper_{i}",
                            )

                with col_rf2:
                    if rf.meanings:
                        meanings_json = json.dumps(rf.meanings, indent=2)
                    else:
                        meanings_json = ""

                    updated_meanings = st.text_area(
                        "Meanings (JSON format)",
                        value=meanings_json,
                        height=100,
                        key=f"judge_meanings_{i}",
                        help="Optional: Map options to meanings using JSON format",
                    )

                # Update button for response format
                if st.button("💾 Update Format", key=f"update_format_{i}"):
                    if judge_type == "discrete":
                        _update_judge_response_format(
                            i, judge_type, updated_options, updated_meanings
                        )
                    elif judge_type == "continuous":
                        _update_judge_response_format(
                            i,
                            judge_type,
                            f"{updated_lower}, {updated_upper}",
                            updated_meanings,
                        )


def render_requirements_tab() -> None:
    """Render the requirements configuration tab."""
    st.header("Requirements")
    st.markdown("Define the questions and dependency structure for your rubric.")

    _render_requirement_form()
    _render_existing_requirements()


def _render_requirement_form() -> None:
    """Render the form for adding new requirements."""
    col1, col2 = st.columns([1, 1])

    with col1:
        req_type = st.selectbox(
            "Requirement Type",
            options=list(NAME_TO_REQUIREMENT_CLASS.keys()),
            key="new_req_type",
        )
        req_name = st.text_input(
            "Name (unique identifier)",
            placeholder="e.g., check_scene_safety",
            key="new_req_name",
        )

        # Judge name selector
        judge_options = ["(auto-select by type)"] + [
            getattr(judge, "name", None) or f"Unnamed {judge.__class__.__name__}"
            for judge in st.session_state.judge_rewarders
            if getattr(judge, "name", None)  # Only show named judges
        ]
        judge_name_selection = st.selectbox(
            "Judge Name (optional)",
            options=judge_options,
            key="new_req_judge_name",
            help="Select a specific judge by name, or leave as auto-select to use type-based matching",
        )
        req_judge_name = (
            None
            if judge_name_selection == "(auto-select by type)"
            else judge_name_selection
        )

    with col2:
        req_question = st.text_area(
            "Question",
            placeholder="e.g., Is the scene safe to approach?",
            height=80,
            key="new_req_question",
        )

    st.markdown(
        "**Dependencies** (JSON format - maps answers to dependent requirements)"
    )
    st.markdown('*Example:* `{"1.0": ["assess_breathing", "check_pulse"], "0.0": []}`')

    req_dependencies = st.text_area(
        "Dependencies (JSON)",
        placeholder='{"1.0": ["dependent_req_1", "dependent_req_2"], "0.0": []}',
        height=60,
        key="new_req_dependencies",
    )

    if st.button("Add Requirement"):
        _add_requirement(
            req_type, req_name, req_question, req_dependencies, req_judge_name
        )


def _add_requirement(
    req_type: str,
    req_name: str,
    req_question: str,
    req_dependencies: str,
    req_judge_name: str = None,
) -> None:
    """Add a new requirement to the session state."""
    if not req_name or not req_question:
        st.error("Name and question are required!")
        return

    dependencies = None
    if req_dependencies.strip():
        try:
            dependencies = json.loads(req_dependencies)
            dependencies = {float(k): v for k, v in dependencies.items()}
        except json.JSONDecodeError:
            st.error("Invalid JSON format for dependencies!")
            return

    try:
        # Prepare kwargs for make_requirement
        req_kwargs = {
            "name": req_name,
            "question": req_question,
            "dependencies": dependencies,
        }

        # Add judge name if provided
        if req_judge_name:
            req_kwargs["judge_name"] = req_judge_name

        # Instantiate the requirement - this will validate the configuration
        new_req = make_requirement(req_type, **req_kwargs)

    except Exception as e:
        st.error(f"Error creating requirement: {str(e)}")
        return

    st.session_state.requirements.append(new_req)
    st.rerun()


def _render_existing_requirements() -> None:
    """Render the list of existing requirements."""
    for i, req in enumerate(st.session_state.requirements):
        req_display_name = req.name
        # Remove the judge_info from the title to clean it up
        with st.expander(f"Requirement {i + 1}: {req_display_name}", expanded=False):
            col1, col2, col3 = st.columns([2, 3, 1])

            with col1:
                st.text_input(
                    "Type",
                    value=req.__class__.__name__,
                    disabled=True,
                    key=f"req_type_{i}",
                )
                updated_name = st.text_input(
                    "Name", value=req.name, key=f"req_name_{i}"
                )

                # Judge name selector for editing
                judge_options = ["(auto-select by type)"] + [
                    getattr(judge, "name", None)
                    or f"Unnamed {judge.__class__.__name__}"
                    for judge in st.session_state.judge_rewarders
                    if getattr(judge, "name", None)  # Only show named judges
                ]
                current_judge = getattr(req, "judge_name", "") or ""
                current_judge_display = (
                    current_judge if current_judge else "(auto-select by type)"
                )

                try:
                    judge_index = judge_options.index(current_judge_display)
                except ValueError:
                    judge_index = 0

                updated_judge_selection = st.selectbox(
                    "Judge Name",
                    options=judge_options,
                    index=judge_index,
                    key=f"req_judge_name_{i}",
                    help="Select a specific judge by name, or leave as auto-select to use type-based matching",
                )
                updated_judge_name = (
                    None
                    if updated_judge_selection == "(auto-select by type)"
                    else updated_judge_selection
                )

            with col2:
                updated_question = st.text_area(
                    "Question",
                    value=req.question,
                    height=80,
                    key=f"req_question_{i}",
                )

                # Add a proper title for the dependencies section
                st.markdown("**Dependencies:**")
                if req.dependencies:
                    deps_json = json.dumps(req.dependencies, indent=2)
                else:
                    deps_json = ""

                updated_dependencies = st.text_area(
                    "Dependencies (JSON)",
                    value=deps_json,
                    height=100,
                    key=f"req_dependencies_{i}",
                    help="JSON format mapping answers to dependent requirements",
                )

            with col3:
                st.markdown("<br>", unsafe_allow_html=True)  # Add some spacing

                if st.button("💾 Update", key=f"update_req_{i}"):
                    _update_requirement(
                        i,
                        updated_name,
                        updated_question,
                        updated_dependencies,
                        updated_judge_name,
                    )

                if st.button("🗑️ Remove", key=f"remove_req_{i}"):
                    st.session_state.requirements.pop(i)
                    st.rerun()


def _update_requirement(
    index: int,
    new_name: str,
    new_question: str,
    new_dependencies: str,
    new_judge_name: str = None,
) -> None:
    """Update an existing requirement."""
    if not new_name or not new_question:
        st.error("Name and question are required!")
        return

    # Parse dependencies
    dependencies = None
    if new_dependencies.strip():
        try:
            dependencies = json.loads(new_dependencies)
            dependencies = {float(k): v for k, v in dependencies.items()}
        except json.JSONDecodeError:
            st.error("Invalid JSON format for dependencies!")
            return

    try:
        # Get the current requirement to preserve its type
        current_req = st.session_state.requirements[index]
        req_type = current_req.__class__.__name__.replace("Requirement", "").lower()

        # Prepare kwargs for make_requirement
        req_kwargs = {
            "name": new_name,
            "question": new_question,
            "dependencies": dependencies,
        }

        # Add judge name if provided
        if new_judge_name:
            req_kwargs["judge_name"] = new_judge_name

        # Create the updated requirement
        updated_req = make_requirement(req_type, **req_kwargs)

        # Replace the requirement
        st.session_state.requirements[index] = updated_req
        st.success("Requirement updated successfully!")
        st.rerun()

    except Exception as e:
        st.error(f"Error updating requirement: {str(e)}")
        return


def render_reward_strategy_tab() -> None:
    """Render the reward strategy configuration tab."""
    st.header("Reward Strategy")
    st.markdown("Configure how rewards are calculated from evaluation results.")

    current_strategy_type = (
        st.session_state.reward_strategy.name
        if st.session_state.reward_strategy
        else "levelweighted"
    )

    strategy_type = st.selectbox(
        "Strategy Type",
        options=list(NAME_TO_REWARD_STRATEGY_CLASS.keys()),
        index=list(NAME_TO_REWARD_STRATEGY_CLASS.keys()).index(current_strategy_type),
    )

    strategy_params = _render_strategy_parameters(strategy_type)

    if st.button("Set Reward Strategy"):
        try:
            # Instantiate the reward strategy - this will validate the configuration
            strategy = make_reward_strategy(strategy_type, **strategy_params)
            st.session_state.reward_strategy = strategy
            st.success(f"Reward strategy set to: {strategy_type}")
        except Exception as e:
            st.error(f"Error creating reward strategy: {str(e)}")


def _render_strategy_parameters(strategy_type: str) -> dict[str, Any]:
    """Render parameter inputs for the selected strategy type and return the values."""
    strategy_params = {}

    if strategy_type == "levelweighted":
        col1, col2 = st.columns(2)
        with col1:
            strategy_params["base_weight"] = st.number_input(
                "Base Weight", value=1.0, step=0.1
            )
        with col2:
            strategy_params["level_multiplier"] = st.number_input(
                "Level Multiplier", value=1.0, step=0.1
            )

    elif strategy_type == "level_based":
        col1, col2 = st.columns(2)
        with col1:
            strategy_params["max_level_bonus"] = st.number_input(
                "Max Level Bonus", value=1.0, step=0.1
            )
        with col2:
            strategy_params["completion_bonus"] = st.number_input(
                "Completion Bonus", value=0.5, step=0.1
            )

    elif strategy_type == "completion_ratio":
        col1, col2 = st.columns(2)
        with col1:
            strategy_params["ratio_weight"] = st.number_input(
                "Ratio Weight", value=1.0, step=0.1
            )
        with col2:
            strategy_params["quality_weight"] = st.number_input(
                "Quality Weight", value=0.5, step=0.1
            )

    elif strategy_type == "progressive":
        col1, col2 = st.columns(2)
        with col1:
            strategy_params["base_reward"] = st.number_input(
                "Base Reward", value=1.0, step=0.1
            )
        with col2:
            strategy_params["growth_factor"] = st.number_input(
                "Growth Factor", value=1.5, step=0.1
            )

    elif strategy_type in ["sum", "mean"]:
        st.info(f"The {strategy_type} strategy requires no additional parameters.")

    return strategy_params


def render_configuration_preview() -> None:
    """Render the configuration preview and build button."""
    st.divider()

    # Header with build button
    col_header, col_button = st.columns([3, 1])
    with col_header:
        st.header("🔍 Rubric Preview")
    with col_button:
        _render_build_button()

    if (
        st.session_state.judge_rewarders
        or st.session_state.requirements
        or st.session_state.reward_strategy
    ):

        # Enhanced preview layout
        _render_enhanced_preview()
    else:
        st.info(
            "Configure your judge rewarders, requirements, and reward strategy to see a preview."
        )


def _render_build_button() -> None:
    """Render the build rubric button and handle building."""
    # Compact header version
    rubric_name = st.text_input(
        "Name:",
        placeholder="my_rubric",
        key="build_rubric_name",
        label_visibility="collapsed",
        help="Enter name for the rubric",
    )

    # Check if we can build
    can_build = (
        st.session_state.judge_rewarders
        and st.session_state.requirements
        and rubric_name.strip()
    )

    if st.button(
        "🏗️ Build & Save", type="primary", key="build_main", disabled=not can_build
    ):
        try:
            rubric = _build_rubric()

            # Save the rubric
            DEFAULT_SAVE_DIR.mkdir(parents=True, exist_ok=True)
            rubric.save(DEFAULT_SAVE_DIR, rubric_name.strip())

            st.success("✅ Rubric built and saved successfully!")
            st.info(
                f"**Rubric Details:**\n"
                f"- Name: {rubric_name.strip()}\n"
                f"- {len(rubric.requirements)} requirements\n"
                f"- {len(rubric.judge_options)} judge options\n"
                f"- Reward strategy: {rubric.reward_strategy.name}\n"
                f"- Saved to: {DEFAULT_SAVE_DIR / rubric_name.strip()}"
            )
            st.session_state.built_rubric = rubric

        except Exception as e:
            st.error(f"Error building/saving rubric: {str(e)}")
            st.exception(e)


def _render_enhanced_preview() -> None:
    """Render an enhanced preview of the current rubric configuration."""
    # Configuration summary cards
    col1, col2, col3 = st.columns(3)

    with col1:
        with st.container():
            st.markdown("### 🔨 Judge Rewarders")
            if st.session_state.judge_rewarders:
                st.metric("Count", len(st.session_state.judge_rewarders))

                with st.expander("View Details", expanded=False):
                    for i, judge in enumerate(st.session_state.judge_rewarders):
                        judge_name = getattr(judge, "name", None) or f"Judge {i + 1}"
                        judge_type = judge.__class__.__name__.replace(
                            "JudgeRewarder", ""
                        ).lower()

                        st.markdown(f"**{judge_name}**")
                        st.caption(f"Type: {judge_type} • Model: {judge.judge_model}")

                        # Show response format if configured
                        if hasattr(judge, "judge_response_format"):
                            rf = judge.judge_response_format
                            if "Discrete" in rf.__class__.__name__:
                                options_str = ", ".join(map(str, rf.options))
                                st.caption(f"Options: [{options_str}]")
                            elif "Continuous" in rf.__class__.__name__:
                                bounds = rf.options
                                st.caption(f"Range: [{bounds[0]} to {bounds[1]}]")

                        if i < len(st.session_state.judge_rewarders) - 1:
                            st.divider()
            else:
                st.warning("No judges configured")

    with col2:
        with st.container():
            st.markdown("### 📋 Requirements")
            if st.session_state.requirements:
                st.metric("Count", len(st.session_state.requirements))

                with st.expander("View Details", expanded=False):
                    for i, req in enumerate(st.session_state.requirements):
                        st.markdown(f"**{req.name}**")
                        st.caption(
                            f"Type: {req.__class__.__name__.replace('Requirement', '').lower()}"
                        )

                        # Show judge assignment
                        judge_name = getattr(req, "judge_name", None)
                        if judge_name:
                            st.caption(f"Judge: {judge_name}")
                        else:
                            st.caption("Judge: auto-select")

                        # Show dependency info
                        if req.dependencies:
                            dep_count = sum(
                                len(deps) for deps in req.dependencies.values()
                            )
                            st.caption(f"Dependencies: {dep_count} total")
                        else:
                            st.caption("Terminal requirement")

                        if i < len(st.session_state.requirements) - 1:
                            st.divider()
            else:
                st.warning("No requirements configured")

    with col3:
        with st.container():
            st.markdown("### 🎯 Reward Strategy")
            if st.session_state.reward_strategy:
                strategy = st.session_state.reward_strategy
                st.metric("Type", strategy.name)

                with st.expander("View Details", expanded=False):
                    st.markdown(f"**Strategy:** `{strategy.name}`")

                    # Show strategy parameters
                    params = {}
                    for attr_name in dir(strategy):
                        if (
                            not attr_name.startswith("_")
                            and not callable(getattr(strategy, attr_name))
                            and attr_name not in ["name", "calculate_reward"]
                        ):
                            params[attr_name] = getattr(strategy, attr_name)

                    if params:
                        st.markdown("**Parameters:**")
                        for param, value in params.items():
                            st.caption(f"{param}: {value}")
                    else:
                        st.caption("No additional parameters")
            else:
                st.warning("No strategy configured")

    # Requirement dependencies visualization
    if st.session_state.requirements:
        st.markdown("---")
        st.markdown("### 🔗 Dependency Structure")

        with st.expander("View Dependency Flow", expanded=False):
            # Create a simple dependency visualization
            terminal_reqs = []
            dependent_reqs = []

            for req in st.session_state.requirements:
                if req.dependencies:
                    dependent_reqs.append(req)
                else:
                    terminal_reqs.append(req)

            if terminal_reqs:
                st.markdown("**Terminal Requirements:**")
                for req in terminal_reqs:
                    st.markdown(f"• `{req.name}`")

            if dependent_reqs:
                st.markdown("**Requirements with Dependencies:**")
                for req in dependent_reqs:
                    st.markdown(f"• `{req.name}`")
                    for answer, deps in req.dependencies.items():
                        if deps:
                            deps_str = ", ".join([f"`{dep}`" for dep in deps])
                            st.markdown(f"  - If {answer} → {deps_str}")
                        else:
                            st.markdown(f"  - If {answer} → terminal")


def _build_rubric():
    """Build the rubric using the current configuration."""
    builder = RubricBuilder()

    # Add judge rewarders (already instantiated and validated)
    for judge in st.session_state.judge_rewarders:
        builder.add_judge_option(judge)

    # Add requirements (already instantiated and validated)
    for req in st.session_state.requirements:
        builder.add_requirement(req)

    # Set reward strategy (already instantiated and validated)
    if st.session_state.reward_strategy:
        builder.set_reward_strategy(st.session_state.reward_strategy)

    return builder.make_rubric()


def main() -> None:
    """Entry point for the rubric builder GUI."""
    configure_page()
    initialize_session_state()

    st.title("🏗️ MultiStep Rubric Builder")
    st.markdown(
        "Build complex multi-step rubrics for RL environments with dependencies, judges, and reward strategies."
    )

    render_sidebar_overview()

    # Main content area with tabs
    tab1, tab2, tab3, tab4 = st.tabs(
        ["🔨 Judge Rewarders", "📋 Requirements", "🎯 Reward Strategy", "🎭 Scenarios"]
    )

    with tab1:
        render_judge_rewarders_tab()

    with tab2:
        render_requirements_tab()

    with tab3:
        render_reward_strategy_tab()

    with tab4:
        render_scenarios_tab()

    render_configuration_preview()

    # Visualization section at the bottom
    st.divider()
    render_visualization()

    # Footer
    st.divider()
    st.markdown(
        "View source code on [GitHub](https://github.com/jacobphillips99/open-rubric)",
        unsafe_allow_html=True,
    )


def render_scenarios_tab() -> None:
    """Render the scenarios management tab."""
    st.header("Scenarios")
    st.markdown("Manage and preview loaded scenarios for testing your rubrics.")

    # Show loaded scenarios if any
    if "loaded_scenarios" in st.session_state and st.session_state.loaded_scenarios:
        scenarios = st.session_state.loaded_scenarios

        st.success(f"📊 **{len(scenarios)} scenario(s) currently loaded**")

        # Scenario selector
        scenario_names = [
            f"{i + 1}. {s.name or 'Unnamed'}" for i, s in enumerate(scenarios)
        ]
        selected_idx = st.selectbox(
            "Select scenario to view:",
            range(len(scenarios)),
            format_func=lambda x: scenario_names[x],
            key="selected_scenario",
        )

        if selected_idx is not None:
            scenario = scenarios[selected_idx]
            _render_scenario_details(scenario, selected_idx)

        # Actions for loaded scenarios
        st.divider()
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("🗑️ Clear All Scenarios"):
                st.session_state.loaded_scenarios = []
                st.rerun()

        with col2:
            if st.button("💾 Save Scenarios"):
                _save_loaded_scenarios()

        with col3:
            if st.button("🧪 Test with Current Rubric"):
                _test_scenarios_with_rubric()

    else:
        st.info("No scenarios loaded yet.")
        st.markdown(
            "Use the **Save/Load** section in the sidebar to load scenarios from directories."
        )

        # Option to load example scenarios
        st.divider()
        st.markdown("**Load Example Scenarios:**")

        example_options = {
            "First Responder": "first_responder",
            "Debugging": "debugging",
        }

        col1, col2 = st.columns(2)
        with col1:
            selected_example = st.selectbox(
                "Choose example:",
                options=list(example_options.keys()),
                key="example_scenarios_select",
            )

        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("📂 Load Example"):
                _load_example_scenarios(example_options[selected_example])


def _render_scenario_details(scenario, index: int) -> None:
    """Render detailed view of a scenario."""
    st.subheader(f"Scenario {index + 1}: {scenario.name or 'Unnamed'}")

    # Basic info
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Name:** {scenario.name or 'N/A'}")
        st.markdown(f"**Description:** {scenario.description or 'N/A'}")

    with col2:
        if scenario.answers:
            st.markdown(f"**Answer Keys:** {len(scenario.answers)}")
            st.markdown(f"**Requirements:** {', '.join(scenario.answers.keys())}")
        else:
            st.markdown("**No answer keys defined**")

    # Content
    with st.expander("📝 Prompt", expanded=True):
        st.text_area(
            "Scenario prompt:", value=scenario.prompt, height=150, disabled=True
        )

    if scenario.completion:
        with st.expander("💬 Completion", expanded=False):
            st.text_area(
                "Scenario completion:",
                value=scenario.completion,
                height=100,
                disabled=True,
            )

    if scenario.answers:
        with st.expander("🎯 Answers", expanded=False):
            st.json(scenario.answers)

    if scenario.revealed_info:
        with st.expander("🔍 Revealed Info", expanded=False):
            st.json(scenario.revealed_info)


def _save_loaded_scenarios() -> None:
    """Save the currently loaded scenarios to a file."""
    if (
        "loaded_scenarios" not in st.session_state
        or not st.session_state.loaded_scenarios
    ):
        st.error("No scenarios to save!")
        return

    from verifiers.rubrics.multistep.scenario import Scenario

    # Get save parameters
    with st.form("save_scenarios_form"):
        st.markdown("**Save Scenarios:**")

        col1, col2 = st.columns(2)
        with col1:
            filename = st.text_input(
                "Filename:",
                placeholder="my_scenarios",
                help="File will be saved as .yaml",
            )

        with col2:
            save_dir = st.text_input(
                "Directory:",
                value=st.session_state.get("current_directory", str(DEFAULT_SAVE_DIR)),
            )

        submitted = st.form_submit_button("💾 Save")

        if submitted and filename:
            try:
                save_path = Path(save_dir)
                save_path.mkdir(parents=True, exist_ok=True)

                file_path = save_path / f"{filename}.yaml"
                Scenario.save_multiple(st.session_state.loaded_scenarios, file_path)

                st.success(
                    f"✅ Saved {len(st.session_state.loaded_scenarios)} scenarios to {file_path}!"
                )

            except Exception as e:
                st.error(f"Error saving scenarios: {str(e)}")


def _test_scenarios_with_rubric() -> None:
    """Test loaded scenarios with the current rubric configuration."""
    if not st.session_state.judge_rewarders or not st.session_state.requirements:
        st.error("Please configure judges and requirements first!")
        return

    if (
        "loaded_scenarios" not in st.session_state
        or not st.session_state.loaded_scenarios
    ):
        st.error("No scenarios loaded!")
        return

    try:
        # Build the rubric
        rubric = _build_rubric()
        scenarios = st.session_state.loaded_scenarios

        st.info("🧪 Testing scenarios with current rubric...")

        # Quick compatibility check
        compatible_scenarios = []
        for scenario in scenarios:
            if scenario.answers:
                # Check if scenario has answers for rubric requirements
                rubric_req_names = {req.name for req in rubric.requirements}
                scenario_req_names = set(scenario.answers.keys())

                if rubric_req_names.intersection(scenario_req_names):
                    compatible_scenarios.append(scenario)

        if compatible_scenarios:
            st.success(
                f"✅ Found {len(compatible_scenarios)} compatible scenarios out of {len(scenarios)}"
            )

            # Show compatibility details
            with st.expander("Compatibility Details", expanded=False):
                for i, scenario in enumerate(compatible_scenarios):
                    rubric_reqs = {req.name for req in rubric.requirements}
                    scenario_reqs = set(scenario.answers.keys())
                    matching = rubric_reqs.intersection(scenario_reqs)

                    st.markdown(f"**{scenario.name or f'Scenario {i + 1}'}:**")
                    st.markdown(f"- Matching requirements: {', '.join(matching)}")
                    st.markdown(
                        f"- Coverage: {len(matching)}/{len(rubric_reqs)} requirements"
                    )
        else:
            st.warning(
                "⚠️ No scenarios are compatible with the current rubric requirements."
            )
            st.info(
                "Scenarios need answer keys that match your rubric's requirement names."
            )

    except Exception as e:
        st.error(f"Error testing scenarios: {str(e)}")


def _load_example_scenarios(example_name: str) -> None:
    """Load example scenarios from the multistep_extras package."""
    try:
        from example_rubrics import get_workflow

        _, scenarios = get_workflow(example_name)
        st.session_state.loaded_scenarios = scenarios

        st.success(
            f"✅ Loaded {len(scenarios)} example scenarios from '{example_name}'!"
        )
        st.rerun()

    except Exception as e:
        st.error(f"Error loading example scenarios: {str(e)}")


def render_visualization() -> None:
    """Render the visualization tab with dependency graphs and metrics."""
    st.header("Dependency Visualization")
    st.markdown("Visualize the structure and flow of your rubric requirements.")

    if not st.session_state.requirements:
        st.info("Configure some requirements first to see visualizations.")
        return

    # Enhanced visualization options
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        _ = st.selectbox(
            "Layout Algorithm",
            options=["hierarchical", "force", "circular"],
            index=0,
            help="Choose how to arrange the nodes in the graph",
        )

    with col2:
        show_answer_labels = st.checkbox(
            "Show Answer Labels", value=True, help="Display answer values on the edges"
        )

    with col3:
        show_terminal_states = st.checkbox(
            "Highlight Terminal States",
            value=True,
            help="Emphasize terminal states with diamond shapes",
        )

    with col4:
        graph_height = st.slider(
            "Graph Height",
            min_value=400,
            max_value=1000,
            value=600,
            step=50,
            help="Adjust the height of the graph",
        )

    # Create the main dependency graph with enhanced features
    try:
        from multistep_extras.visualization.visualizer import \
            create_dependency_graph

        st.subheader("🔗 Dependency Graph")

        fig = create_dependency_graph(
            st.session_state.requirements,
            width=1000,
            height=graph_height,
            show_answer_labels=show_answer_labels,
            show_terminal_states=show_terminal_states,
            show_requirement_types=True,
        )

        # # Add enhanced annotations like in the demo
        # fig.add_annotation(
        #     text="💎 Diamond shapes = Terminal states<br>🔵 Circles = Non-terminal states<br>🟢 Green edges = Positive answers<br>🔴 Red edges = Negative answers",
        #     xref="paper",
        #     yref="paper",
        #     x=0.02,
        #     y=0.98,
        #     showarrow=False,
        #     font=dict(size=12, color="#2c3e50"),
        #     align="left",
        #     bgcolor="rgba(255,255,255,0.8)",
        #     bordercolor="lightgray",
        #     borderwidth=1,
        # )

        st.plotly_chart(fig, use_container_width=True)

        # Add explanation
        with st.expander("📚 How to Read This Graph", expanded=False):
            st.markdown(
                """
            **Understanding the Dependency Graph:**

            - **Nodes (shapes)** represent requirements:
              - 💎 **Diamond shapes** = Terminal states (no dependencies)
              - 🔵 **Circle shapes** = Non-terminal states (have dependencies)
            - **Colors** indicate requirement types:
              - 🔵 Blue: Binary requirements
              - 🟠 Orange: Discrete requirements
              - 🟢 Green: Continuous requirements
              - 🔴 Red: Unit vector requirements
            - **Edges (arrows)** show dependencies between requirements
            - **Numbers on edges** show which answer triggers that dependency
            - **Size** indicates if a requirement is terminal (larger) or has dependencies
            - **Hover** over nodes to see detailed information

            **Layout Algorithms:**
            - **Hierarchical**: Organizes by dependency levels (top-down flow)
            - **Force**: Uses physics simulation for natural clustering
            - **Circular**: Arranges nodes in a circle for overview
            """
            )
        return
    except Exception as e:
        st.error(f"Error creating dependency graph: {str(e)}")
        return

    # Enhanced metrics dashboard section
    st.divider()
    st.subheader("📊 Metrics")

    try:
        from multistep_extras.visualization.visualizer import (
            RequirementsVisualizer, create_metrics_dashboard)

        metrics_fig = create_metrics_dashboard(st.session_state.requirements)

        # Add terminal state analysis like in the demo
        viz = RequirementsVisualizer(st.session_state.requirements)
        terminal_analysis = viz.create_terminal_analysis()

        # Add terminal state summary as annotation
        non_terminal_count = (
            len(st.session_state.requirements) - terminal_analysis["terminal_nodes"]
        )
        terminal_summary = (
            f"💎 Terminal Analysis:<br>"
            f"• {terminal_analysis['terminal_nodes']} terminal nodes<br>"
            f"• {non_terminal_count} non-terminal nodes<br>"
            f"• {terminal_analysis['terminal_percentage']:.1f}% terminal rate"
        )

        metrics_fig.add_annotation(
            text=terminal_summary,
            xref="paper",
            yref="paper",
            x=0.02,
            y=0.98,
            showarrow=False,
            font=dict(size=12, color="#2c3e50"),
            align="left",
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="lightgray",
            borderwidth=1,
        )

        st.plotly_chart(metrics_fig, use_container_width=True)

        # Show text metrics alongside
        metrics = viz.analyze_metrics()

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Requirements", metrics["total_requirements"])

        with col2:
            st.metric(
                "Terminal Nodes",
                metrics["terminal_nodes"],
                delta=f"{terminal_analysis['terminal_percentage']:.1f}%",
            )

        with col3:
            st.metric("Max Depth", metrics["max_depth"])

        with col4:
            st.metric("Avg Branching", f"{metrics['avg_branching_factor']:.1f}")

        # Enhanced metrics details
        with st.expander("📊 Detailed Metrics", expanded=False):
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Structure Analysis:**")
                st.markdown(f"• Branching Nodes: {metrics['branching_nodes']}")
                st.markdown(f"• Multi-branch Nodes: {metrics['multi_branch_nodes']}")
                st.markdown(f"• Root Nodes: {', '.join(metrics['root_nodes'])}")
                st.markdown(f"• Total Edges: {metrics['total_edges']}")

            with col2:
                st.markdown("**Terminal Analysis:**")
                for req_type, count in terminal_analysis["terminal_by_type"].items():
                    st.markdown(f"• {req_type}: {count} terminal")
                st.markdown(
                    f"• Terminal Rate: {terminal_analysis['terminal_percentage']:.1f}%"
                )
                st.markdown(f"• Non-Terminal: {non_terminal_count}")

    except Exception as e:
        st.error(
            f"Error creating metrics dashboard: {str(e)}; {traceback.format_exc()}"
        )
        breakpoint()

    # Save visualization section
    st.divider()
    st.subheader("💾 Save Visualizations")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("📁 Save Dependency Graph"):
            try:
                from pathlib import Path

                outputs_dir = Path("outputs") / "visualizations"
                outputs_dir.mkdir(parents=True, exist_ok=True)

                output_file = outputs_dir / "dependency_graph.html"
                fig.write_html(str(output_file))
                st.success(f"✅ Saved dependency graph to: {output_file}")

            except Exception as e:
                st.error(f"Error saving dependency graph: {str(e)}")

    with col2:
        if st.button("📊 Save Metrics Dashboard"):
            try:
                from pathlib import Path

                outputs_dir = Path("outputs") / "visualizations"
                outputs_dir.mkdir(parents=True, exist_ok=True)

                output_file = outputs_dir / "metrics_dashboard.html"
                metrics_fig.write_html(str(output_file))
                st.success(f"✅ Saved metrics dashboard to: {output_file}")

            except Exception as e:
                st.error(f"Error saving metrics dashboard: {str(e)}")

    # Comparison section if multiple rubrics are loaded
    if "loaded_scenarios" in st.session_state and st.session_state.loaded_scenarios:
        st.divider()
        st.subheader("🔄 Scenario Compatibility")

        try:
            rubric = _build_rubric()
            scenarios = st.session_state.loaded_scenarios

            compatible_count = 0
            total_count = len(scenarios)

            for scenario in scenarios:
                if scenario.answers:
                    rubric_req_names = {req.name for req in rubric.requirements}
                    scenario_req_names = set(scenario.answers.keys())
                    if rubric_req_names.intersection(scenario_req_names):
                        compatible_count += 1

            st.metric(
                "Compatible Scenarios",
                f"{compatible_count}/{total_count}",
                delta=(
                    f"{compatible_count / total_count * 100:.0f}%"
                    if total_count > 0
                    else "0%"
                ),
            )

        except Exception as e:
            st.warning(f"Could not analyze scenario compatibility: {str(e)}")


if __name__ == "__main__":
    main()
