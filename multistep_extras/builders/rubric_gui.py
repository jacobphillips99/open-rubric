"""
Streamlit GUI for building MultiStep rubrics using the RubricBuilder.

Run with:
    streamlit run multistep_extras/builders/rubric_gui.py

This GUI allows you to build a MultiStepRubric by adding judge rewarders, requirements, and a reward strategy.
"""

import json
from pathlib import Path
from typing import Any

import streamlit as st
import yaml

from multistep_extras.builders.builder import RubricBuilder
from verifiers.rewards.judge_reward import (JUDGE_PROMPT,
                                            JUDGE_PROMPT_VARIABLES,
                                            NAME_TO_JUDGE_REWARDER_CLASS)
from verifiers.rubrics.multistep.multistep_rubric import MultiStepRubric
from verifiers.rubrics.multistep.requirement import NAME_TO_REQUIREMENT_CLASS
from verifiers.rubrics.multistep.reward_strategies import (
    NAME_TO_REWARD_STRATEGY_CLASS, make_reward_strategy)

# Default save directory
DEFAULT_SAVE_DIR = Path("outputs/workflows")


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
        st.divider()
        _render_requirements_overview()
        st.divider()
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

        # Populate judge rewarders
        for judge in rubric.judge_options:
            judge_data = {
                "type": judge.__class__.__name__.replace("JudgeRewarder", "").lower(),
                "judge_prompt": judge.judge_prompt,
                "judge_model": judge.judge_model,
            }
            st.session_state.judge_rewarders.append(judge_data)

        # Populate requirements
        for req in rubric.requirements:
            req_data = {
                "type": req.__class__.__name__.replace("Requirement", "").lower(),
                "name": req.name,
                "question": req.question,
                "dependencies": req.dependencies,
            }
            st.session_state.requirements.append(req_data)

        # Populate reward strategy
        strategy = rubric.reward_strategy
        strategy_data = {
            "type": strategy.__class__.__name__.replace("RewardStrategy", "").lower(),
        }

        # Add strategy parameters
        for attr_name in dir(strategy):
            if (
                not attr_name.startswith("_")
                and not callable(getattr(strategy, attr_name))
                and attr_name not in ["name"]
            ):
                strategy_data[attr_name] = getattr(strategy, attr_name)

        st.session_state.reward_strategy = strategy_data

        st.success(f"✅ Loaded rubric '{rubric_name}' from {directory}!")
        st.rerun()

    except Exception as e:
        st.error(f"Error loading rubric: {str(e)}")


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
    st.subheader("🔨 Judge Rewarders")
    if st.session_state.judge_rewarders:
        for i, judge in enumerate(st.session_state.judge_rewarders):
            with st.container():
                st.markdown(f"**{i + 1}.** `{judge['type']}`")
                st.caption(f"Model: {judge['judge_model']}")
                prompt_preview = (
                    f"{judge['judge_prompt'][:47]}..."
                    if len(judge["judge_prompt"]) > 50
                    else judge["judge_prompt"]
                )
                st.caption(f"Prompt: {prompt_preview}")
        st.markdown(f"*Total: {len(st.session_state.judge_rewarders)} judges*")
    else:
        st.info("No judges configured yet")


def _render_requirements_overview() -> None:
    """Render the requirements overview section."""
    st.subheader("📋 Requirements")
    if st.session_state.requirements:
        for i, req in enumerate(st.session_state.requirements):
            with st.container():
                st.markdown(f"**{i + 1}.** `{req['name']}`")
                st.caption(f"Type: {req['type']}")
                deps_count = (
                    len(req.get("dependencies", {})) if req.get("dependencies") else 0
                )
                if deps_count > 0:
                    st.caption(f"Has {deps_count} dependency rule(s)")
                else:
                    st.caption("Terminal requirement")
        st.markdown(f"*Total: {len(st.session_state.requirements)} requirements*")
    else:
        st.info("No requirements configured yet")


def _render_reward_strategy_overview() -> None:
    """Render the reward strategy overview section."""
    st.subheader("🎯 Reward Strategy")
    if st.session_state.reward_strategy:
        strategy = st.session_state.reward_strategy
        st.markdown(f"**Type:** `{strategy['type']}`")
        params = {k: v for k, v in strategy.items() if k != "type"}
        if params:
            for param, value in params.items():
                st.caption(f"{param}: {value}")
        else:
            st.caption("No additional parameters")
    else:
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

    with col2:
        judge_prompt = st.text_area(
            f"Judge Prompt Template -- Must contain the following variables: {JUDGE_PROMPT_VARIABLES}",
            value=JUDGE_PROMPT.strip(),
            height=120,
            key="new_judge_prompt",
        )

    if st.button("Add Judge Rewarder"):
        _add_judge_rewarder(judge_type, judge_model, judge_prompt)


def _add_judge_rewarder(judge_type: str, judge_model: str, judge_prompt: str) -> None:
    """Add a new judge rewarder to the session state."""
    if not all(var in judge_prompt for var in JUDGE_PROMPT_VARIABLES):
        st.error(
            f"Judge prompt must contain the following variables: {JUDGE_PROMPT_VARIABLES}"
        )
        return

    new_judge = {
        "type": judge_type,
        "judge_prompt": judge_prompt,
        "judge_model": judge_model,
    }
    st.session_state.judge_rewarders.append(new_judge)
    st.success("Judge rewarder added successfully!")
    st.rerun()


def _render_existing_judge_rewarders() -> None:
    """Render the list of existing judge rewarders."""
    for i, judge in enumerate(st.session_state.judge_rewarders):
        with st.expander(f"Judge {i + 1}: {judge['type']}", expanded=False):
            col1, col2, col3 = st.columns([2, 2, 1])

            with col1:
                st.text_input(
                    "Type", value=judge["type"], disabled=True, key=f"judge_type_{i}"
                )
                st.text_input(
                    "Model",
                    value=judge["judge_model"],
                    disabled=True,
                    key=f"judge_model_{i}",
                )

            with col2:
                st.text_area(
                    "Prompt",
                    value=judge["judge_prompt"],
                    height=100,
                    disabled=True,
                    key=f"judge_prompt_{i}",
                )

            with col3:
                if st.button("🗑️ Remove", key=f"remove_judge_{i}"):
                    st.session_state.judge_rewarders.pop(i)
                    st.rerun()


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
        _add_requirement(req_type, req_name, req_question, req_dependencies)


def _add_requirement(
    req_type: str, req_name: str, req_question: str, req_dependencies: str
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

    new_req = {
        "type": req_type,
        "name": req_name,
        "question": req_question,
        "dependencies": dependencies,
    }
    st.session_state.requirements.append(new_req)
    st.rerun()


def _render_existing_requirements() -> None:
    """Render the list of existing requirements."""
    for i, req in enumerate(st.session_state.requirements):
        with st.expander(f"Requirement {i + 1}: {req['name']}", expanded=False):
            col1, col2, col3 = st.columns([2, 3, 1])

            with col1:
                st.text_input(
                    "Type", value=req["type"], disabled=True, key=f"req_type_{i}"
                )
                st.text_input(
                    "Name", value=req["name"], disabled=True, key=f"req_name_{i}"
                )

            with col2:
                st.text_area(
                    "Question",
                    value=req["question"],
                    height=80,
                    disabled=True,
                    key=f"req_question_{i}",
                )
                if req.get("dependencies"):
                    st.json(req["dependencies"])
                else:
                    st.text("No dependencies (terminal requirement)")

            with col3:
                if st.button("🗑️ Remove", key=f"remove_req_{i}"):
                    st.session_state.requirements.pop(i)
                    st.rerun()


def render_reward_strategy_tab() -> None:
    """Render the reward strategy configuration tab."""
    st.header("Reward Strategy")
    st.markdown("Configure how rewards are calculated from evaluation results.")

    current_strategy_type = (
        st.session_state.reward_strategy.get("type", "levelweighted")
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
        st.session_state.reward_strategy = {"type": strategy_type, **strategy_params}
        st.success(f"Reward strategy set to: {strategy_type}")


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
    st.header("🔍 Rubric Preview")

    if (
        st.session_state.judge_rewarders
        or st.session_state.requirements
        or st.session_state.reward_strategy
    ):
        col1, col2 = st.columns(2)

        with col1:
            _render_preview_judges()
            _render_preview_requirements()

        with col2:
            _render_preview_strategy()
            _render_build_button()
    else:
        st.info(
            "Configure your judge rewarders, requirements, and reward strategy to see a preview."
        )


def _render_preview_judges() -> None:
    """Render judge rewarders preview."""
    st.subheader("Judge Rewarders")
    if st.session_state.judge_rewarders:
        for i, judge in enumerate(st.session_state.judge_rewarders):
            st.markdown(f"**{i + 1}.** {judge['type']} ({judge['judge_model']})")
    else:
        st.warning("No judge rewarders configured")


def _render_preview_requirements() -> None:
    """Render requirements preview."""
    st.subheader("Requirements")
    if st.session_state.requirements:
        for i, req in enumerate(st.session_state.requirements):
            deps_info = (
                f" → {list(req['dependencies'].keys())}"
                if req.get("dependencies")
                else " → terminal"
            )
            st.markdown(f"**{i + 1}.** {req['name']} ({req['type']}){deps_info}")
    else:
        st.warning("No requirements configured")


def _render_preview_strategy() -> None:
    """Render reward strategy preview."""
    st.subheader("Reward Strategy")
    if st.session_state.reward_strategy:
        st.json(st.session_state.reward_strategy)
    else:
        st.warning("No reward strategy configured")


def _render_build_button() -> None:
    """Render the build rubric button and handle building."""
    # Add input field for rubric name
    col1, col2 = st.columns([3, 1])

    with col1:
        rubric_name = st.text_input(
            "Rubric name for saving:",
            placeholder="my_rubric",
            key="build_rubric_name",
            help="The rubric will be automatically saved with this name",
        )

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)  # Add space to align with input
        if st.button("🏗️ Build & Save Rubric", type="primary", key="build_main"):
            if (
                not st.session_state.judge_rewarders
                or not st.session_state.requirements
            ):
                st.error("Need at least one judge rewarder and one requirement!")
                return

            if not rubric_name.strip():
                st.error("Please provide a name for the rubric!")
                return

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


def _build_rubric():
    """Build the rubric using the current configuration."""
    builder = RubricBuilder()

    # Add judge rewarders
    for judge_data in st.session_state.judge_rewarders:
        builder.add_judge_option(judge_data)

    # Add requirements
    for req_data in st.session_state.requirements:
        builder.add_requirement(req_data)

    # Set reward strategy
    if st.session_state.reward_strategy:
        strategy = make_reward_strategy(
            st.session_state.reward_strategy["type"],
            **{
                k: v for k, v in st.session_state.reward_strategy.items() if k != "type"
            },
        )
        builder.set_reward_strategy(strategy)

    return builder.make_rubric()


def main() -> None:
    """Entry point for the rubric builder GUI."""
    configure_page()
    initialize_session_state()

    st.title("🏗️ MultiStep Rubric Builder")
    st.markdown(
        "Build complex multi-step rubrics with dependencies, judges, and reward strategies."
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
        from multistep_extras.example_rubrics import get_workflow

        _, scenarios = get_workflow(example_name)
        st.session_state.loaded_scenarios = scenarios

        st.success(
            f"✅ Loaded {len(scenarios)} example scenarios from '{example_name}'!"
        )
        st.rerun()

    except Exception as e:
        st.error(f"Error loading example scenarios: {str(e)}")


if __name__ == "__main__":
    main()
