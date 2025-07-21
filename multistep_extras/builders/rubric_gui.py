"""
Streamlit GUI for building MultiStep rubrics using the RubricBuilder.

Run with:
    streamlit run multistep_extras/rubric_gui.py

This GUI allows you to build a MultiStepRubric by adding judge rewarders, requirements, and a reward strategy.
"""

import json
import os
from pathlib import Path
from typing import Any

import streamlit as st

from multistep_extras.builders.builder import RubricBuilder
from verifiers.rewards.judge_reward import (JUDGE_PROMPT,
                                            JUDGE_PROMPT_VARIABLES,
                                            NAME_TO_JUDGE_REWARDER_CLASS)
from verifiers.rubrics.multistep.multistep_rubric import MultiStepRubric
from verifiers.rubrics.multistep.requirement import NAME_TO_REQUIREMENT_CLASS
from verifiers.rubrics.multistep.reward_strategies import (
    NAME_TO_REWARD_STRATEGY_CLASS, make_reward_strategy)

# Default save directory
DEFAULT_SAVE_DIR = Path("outputs/rubrics")


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
    """Render the save/load section in the sidebar."""
    st.subheader("💾 Save/Load")
    
    # Create save directory if it doesn't exist
    DEFAULT_SAVE_DIR.mkdir(parents=True, exist_ok=True)
    
    # Load section
    st.markdown("**Load Existing Rubric:**")
    saved_rubrics = _get_saved_rubrics()
    
    if saved_rubrics:
        selected_rubric = st.selectbox(
            "Select rubric to load:",
            options=[""] + saved_rubrics,
            key="load_rubric_select"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📂 Load", disabled=not selected_rubric):
                if selected_rubric:
                    _load_rubric_to_session(selected_rubric)
        
        with col2:
            if st.button("🗑️ Delete", disabled=not selected_rubric):
                if selected_rubric:
                    _delete_saved_rubric(selected_rubric)
    else:
        st.info("No saved rubrics found")
    
    # Save section (only show if there's something to save)
    if (st.session_state.judge_rewarders or 
        st.session_state.requirements or 
        st.session_state.reward_strategy):
        
        st.markdown("**Save Current Configuration:**")
        save_name = st.text_input(
            "Rubric name:",
            placeholder="my_rubric",
            key="save_name_input"
        )
        
        if st.button("💾 Save Config", disabled=not save_name):
            if save_name:
                _save_current_config(save_name)


def _get_saved_rubrics() -> list[str]:
    """Get list of saved rubric names."""
    if not DEFAULT_SAVE_DIR.exists():
        return []
    
    # Look for config files and extract rubric names
    config_files = list(DEFAULT_SAVE_DIR.glob("*_config.yaml"))
    rubric_names = []
    
    for config_file in config_files:
        # Extract name by removing _config.yaml suffix
        name = config_file.stem.replace("_config", "")
        # Check if corresponding requirements file exists
        req_file = DEFAULT_SAVE_DIR / f"{name}_requirements.yaml"
        if req_file.exists():
            rubric_names.append(name)
    
    return sorted(rubric_names)


def _load_rubric_to_session(rubric_name: str) -> None:
    """Load a saved rubric into the session state."""
    try:
        # Load the rubric
        rubric = MultiStepRubric.load(DEFAULT_SAVE_DIR, rubric_name)
        
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
            if (not attr_name.startswith("_") and 
                not callable(getattr(strategy, attr_name)) and 
                attr_name not in ["name"]):
                strategy_data[attr_name] = getattr(strategy, attr_name)
        
        st.session_state.reward_strategy = strategy_data
        
        st.success(f"✅ Loaded rubric '{rubric_name}' successfully!")
        st.rerun()
        
    except Exception as e:
        st.error(f"Error loading rubric: {str(e)}")


def _save_current_config(save_name: str) -> None:
    """Save the current configuration without building the full rubric."""
    try:
        # Build the rubric first
        rubric = _build_rubric()
        
        # Save the rubric
        rubric.save(DEFAULT_SAVE_DIR, save_name)
        
        st.success(f"✅ Saved configuration as '{save_name}'!")
        st.rerun()
        
    except Exception as e:
        st.error(f"Error saving configuration: {str(e)}")


def _delete_saved_rubric(rubric_name: str) -> None:
    """Delete a saved rubric."""
    try:
        config_file = DEFAULT_SAVE_DIR / f"{rubric_name}_config.yaml"
        req_file = DEFAULT_SAVE_DIR / f"{rubric_name}_requirements.yaml"
        
        if config_file.exists():
            config_file.unlink()
        if req_file.exists():
            req_file.unlink()
            
        st.success(f"✅ Deleted rubric '{rubric_name}'!")
        st.rerun()
        
    except Exception as e:
        st.error(f"Error deleting rubric: {str(e)}")


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
            help="The rubric will be automatically saved with this name"
        )
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)  # Add space to align with input
        if st.button("🏗️ Build & Save Rubric", type="primary", key="build_main"):
            if not st.session_state.judge_rewarders or not st.session_state.requirements:
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
    tab1, tab2, tab3 = st.tabs(
        ["🔨 Judge Rewarders", "📋 Requirements", "🎯 Reward Strategy"]
    )

    with tab1:
        render_judge_rewarders_tab()

    with tab2:
        render_requirements_tab()

    with tab3:
        render_reward_strategy_tab()

    render_configuration_preview()

    # Footer
    st.divider()
    st.markdown(
        "View source code on [GitHub](https://github.com/jacobphillips99/open-rubric)",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
