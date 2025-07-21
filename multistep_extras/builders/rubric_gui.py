"""
Streamlit GUI for building MultiStep rubrics using the RubricBuilder.

Run with:
    streamlit run multistep_extras/rubric_gui.py

This GUI allows you to build a MultiStepRubric by adding judge rewarders, requirements, and a reward strategy.
"""

import streamlit as st
import json
from typing import Dict, Any, List, Optional

from multistep_extras.builders.builder import RubricBuilder
from verifiers.rubrics.multistep.requirement import NAME_TO_REQUIREMENT_CLASS, make_requirement
from verifiers.rewards.judge_reward import JUDGE_PROMPT, JUDGE_PROMPT_VARIABLES, NAME_TO_JUDGE_REWARDER_CLASS, JudgeRewarder, make_judge_rewarder
from verifiers.rubrics.multistep.reward_strategies import NAME_TO_REWARD_STRATEGY_CLASS, make_reward_strategy

# Configure Streamlit page
st.set_page_config(
    page_title="Rubric Builder GUI",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🏗️ MultiStep Rubric Builder")
st.markdown("Build complex multi-step rubrics with dependencies, judges, and reward strategies.")

# Initialize session state
if 'judge_rewarders' not in st.session_state:
    st.session_state.judge_rewarders = []
if 'requirements' not in st.session_state:
    st.session_state.requirements = []
if 'reward_strategy' not in st.session_state:
    st.session_state.reward_strategy = None

# Sidebar for configuration overview
with st.sidebar:
    st.header("📋 Configuration Overview")
    
    # Judge Rewarders section
    st.subheader("🔨 Judge Rewarders")
    if st.session_state.judge_rewarders:
        for i, judge in enumerate(st.session_state.judge_rewarders):
            with st.container():
                st.markdown(f"**{i+1}.** `{judge['type']}`")
                st.caption(f"Model: {judge['judge_model']}")
                if len(judge['judge_prompt']) > 50:
                    st.caption(f"Prompt: {judge['judge_prompt'][:47]}...")
                else:
                    st.caption(f"Prompt: {judge['judge_prompt']}")
        st.markdown(f"*Total: {len(st.session_state.judge_rewarders)} judges*")
    else:
        st.info("No judges configured yet")
    
    st.divider()
    
    # Requirements section
    st.subheader("📋 Requirements")
    if st.session_state.requirements:
        for i, req in enumerate(st.session_state.requirements):
            with st.container():
                st.markdown(f"**{i+1}.** `{req['name']}`")
                st.caption(f"Type: {req['type']}")
                deps_count = len(req.get('dependencies', {})) if req.get('dependencies') else 0
                if deps_count > 0:
                    st.caption(f"Has {deps_count} dependency rule(s)")
                else:
                    st.caption("Terminal requirement")
        st.markdown(f"*Total: {len(st.session_state.requirements)} requirements*")
    else:
        st.info("No requirements configured yet")
    
    st.divider()
    
    # Reward Strategy section
    st.subheader("🎯 Reward Strategy")
    if st.session_state.reward_strategy:
        strategy = st.session_state.reward_strategy
        st.markdown(f"**Type:** `{strategy['type']}`")
        
        # Show key parameters based on strategy type
        params = {k: v for k, v in strategy.items() if k != 'type'}
        if params:
            for param, value in params.items():
                st.caption(f"{param}: {value}")
        else:
            st.caption("No additional parameters")
    else:
        st.info("No strategy configured yet")
    
    st.divider()
    
    # Clear all button at bottom
    if st.button("🗑️ Clear All Configuration", type="secondary"):
        st.session_state.judge_rewarders = []
        st.session_state.requirements = []
        st.session_state.reward_strategy = None
        st.rerun()

# Main content area with tabs
tab1, tab2, tab3 = st.tabs(["🔨 Judge Rewarders", "📋 Requirements", "🎯 Reward Strategy"])

# Tab 1: Judge Rewarders
with tab1:
    st.header("Judge Rewarders")
    st.markdown("Configure how responses will be evaluated by judges.")
    
    # Add new judge rewarder
    col1, col2 = st.columns([1, 1])
    
    with col1:
        judge_type = st.selectbox(
            "Judge Type",
            options=list(NAME_TO_JUDGE_REWARDER_CLASS.keys()),
            key="new_judge_type"
        )
        
        judge_model = st.text_input(
            "Judge Model",
            value="gpt-4.1-nano",
            key="new_judge_model"
        )
    
    with col2:
        judge_prompt = st.text_area(
            f"Judge Prompt Template -- Must contain the following variables: {JUDGE_PROMPT_VARIABLES}",
            value=JUDGE_PROMPT.strip(),
            height=120,
            key="new_judge_prompt"
        )
    
    if st.button("Add Judge Rewarder"):
        new_judge = {
            "type": judge_type,
            "judge_prompt": judge_prompt,
            "judge_model": judge_model
        }
        if not all(var in judge_prompt for var in JUDGE_PROMPT_VARIABLES):
            st.error(f"Judge prompt must contain the following variables: {JUDGE_PROMPT_VARIABLES}")
        else:
            st.session_state.judge_rewarders.append(new_judge)
            st.success("Judge rewarder added successfully!")
            st.rerun()
        
    # Display existing judge rewarders
    for i, judge in enumerate(st.session_state.judge_rewarders):
        with st.expander(f"Judge {i+1}: {judge['type']}", expanded=False):
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                st.text_input(f"Type", value=judge['type'], disabled=True, key=f"judge_type_{i}")
                st.text_input(f"Model", value=judge['judge_model'], disabled=True, key=f"judge_model_{i}")
            
            with col2:
                st.text_area(f"Prompt", value=judge['judge_prompt'], height=100, disabled=True, key=f"judge_prompt_{i}")
            
            with col3:
                if st.button(f"🗑️ Remove", key=f"remove_judge_{i}"):
                    st.session_state.judge_rewarders.pop(i)
                    st.rerun()

# Tab 2: Requirements
with tab2:
    st.header("Requirements")
    st.markdown("Define the questions and dependency structure for your rubric.")
    
    # Add new requirement
    col1, col2 = st.columns([1, 1])
    
    with col1:
        req_type = st.selectbox(
            "Requirement Type",
            options=list(NAME_TO_REQUIREMENT_CLASS.keys()),
            key="new_req_type"
        )
        
        req_name = st.text_input(
            "Name (unique identifier)",
            placeholder="e.g., check_scene_safety",
            key="new_req_name"
        )
    
    with col2:
        req_question = st.text_area(
            "Question",
            placeholder="e.g., Is the scene safe to approach?",
            height=80,
            key="new_req_question"
        )
    
    st.markdown("**Dependencies** (JSON format - maps answers to dependent requirements)")
    st.markdown("*Example:* `{\"1.0\": [\"assess_breathing\", \"check_pulse\"], \"0.0\": []}`")
    
    req_dependencies = st.text_area(
        "Dependencies (JSON)",
        placeholder='{"1.0": ["dependent_req_1", "dependent_req_2"], "0.0": []}',
        height=60,
        key="new_req_dependencies"
    )
    
    if st.button("Add Requirement"):
        if req_name and req_question:
            # Parse dependencies
            dependencies = None
            if req_dependencies.strip():
                try:
                    dependencies = json.loads(req_dependencies)
                    # Convert string keys to float
                    dependencies = {float(k): v for k, v in dependencies.items()}
                except json.JSONDecodeError:
                    st.error("Invalid JSON format for dependencies!")
                    st.stop()
            
            new_req = {
                "type": req_type,
                "name": req_name,
                "question": req_question,
                "dependencies": dependencies
            }
            st.session_state.requirements.append(new_req)
            st.rerun()
        else:
            st.error("Name and question are required!")
    
    # Display existing requirements
    for i, req in enumerate(st.session_state.requirements):
        with st.expander(f"Requirement {i+1}: {req['name']}", expanded=False):
            col1, col2, col3 = st.columns([2, 3, 1])
            
            with col1:
                st.text_input(f"Type", value=req['type'], disabled=True, key=f"req_type_{i}")
                st.text_input(f"Name", value=req['name'], disabled=True, key=f"req_name_{i}")
            
            with col2:
                st.text_area(f"Question", value=req['question'], height=80, disabled=True, key=f"req_question_{i}")
                if req.get('dependencies'):
                    st.json(req['dependencies'])
                else:
                    st.text("No dependencies (terminal requirement)")
            
            with col3:
                if st.button(f"🗑️ Remove", key=f"remove_req_{i}"):
                    st.session_state.requirements.pop(i)
                    st.rerun()

# Tab 3: Reward Strategy
with tab3:
    st.header("Reward Strategy")
    st.markdown("Configure how rewards are calculated from evaluation results.")
    
    strategy_type = st.selectbox(
        "Strategy Type",
        options=list(NAME_TO_REWARD_STRATEGY_CLASS.keys()),
        index=0 if not st.session_state.reward_strategy else list(NAME_TO_REWARD_STRATEGY_CLASS.keys()).index(st.session_state.reward_strategy.get('type', 'level_weighted'))
    )
    
    # Dynamic parameters based on strategy type
    strategy_params = {}
    
    if strategy_type == "level_weighted":
        col1, col2 = st.columns(2)
        with col1:
            strategy_params['base_weight'] = st.number_input("Base Weight", value=1.0, step=0.1)
        with col2:
            strategy_params['level_multiplier'] = st.number_input("Level Multiplier", value=1.0, step=0.1)
    
    elif strategy_type == "level_based":
        col1, col2 = st.columns(2)
        with col1:
            strategy_params['max_level_bonus'] = st.number_input("Max Level Bonus", value=1.0, step=0.1)
        with col2:
            strategy_params['completion_bonus'] = st.number_input("Completion Bonus", value=0.5, step=0.1)
    
    elif strategy_type == "completion_ratio":
        col1, col2 = st.columns(2)
        with col1:
            strategy_params['ratio_weight'] = st.number_input("Ratio Weight", value=1.0, step=0.1)
        with col2:
            strategy_params['quality_weight'] = st.number_input("Quality Weight", value=0.5, step=0.1)
    
    elif strategy_type == "progressive":
        col1, col2 = st.columns(2)
        with col1:
            strategy_params['base_reward'] = st.number_input("Base Reward", value=1.0, step=0.1)
        with col2:
            strategy_params['growth_factor'] = st.number_input("Growth Factor", value=1.5, step=0.1)
    
    # For sum and mean strategies, no parameters needed
    elif strategy_type in ["sum", "mean"]:
        st.info(f"The {strategy_type} strategy requires no additional parameters.")
    
    if st.button("Set Reward Strategy"):
        st.session_state.reward_strategy = {
            "type": strategy_type,
            **strategy_params
        }
        st.success(f"Reward strategy set to: {strategy_type}")

# Always-visible Configuration Preview (moved from tab4)
st.divider()
st.header("🔍 Configuration Preview")

if st.session_state.judge_rewarders or st.session_state.requirements or st.session_state.reward_strategy:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Judge Rewarders")
        if st.session_state.judge_rewarders:
            for i, judge in enumerate(st.session_state.judge_rewarders):
                st.markdown(f"**{i+1}.** {judge['type']} ({judge['judge_model']})")
        else:
            st.warning("No judge rewarders configured")
        
        st.subheader("Requirements")
        if st.session_state.requirements:
            for i, req in enumerate(st.session_state.requirements):
                deps_info = f" → {list(req['dependencies'].keys()) if req.get('dependencies') else 'terminal'}"
                st.markdown(f"**{i+1}.** {req['name']} ({req['type']}){deps_info}")
        else:
            st.warning("No requirements configured")
    
    with col2:
        st.subheader("Reward Strategy")
        if st.session_state.reward_strategy:
            st.json(st.session_state.reward_strategy)
        else:
            st.warning("No reward strategy configured")
        
        # Build button and result
        if st.button("🏗️ Build Rubric", type="primary", key="build_main"):
            if st.session_state.judge_rewarders and st.session_state.requirements:
                try:
                    # Create the builder and build the rubric
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
                            **{k: v for k, v in st.session_state.reward_strategy.items() if k != "type"}
                        )
                        builder.set_reward_strategy(strategy)
                    
                    # Build the rubric
                    rubric = builder.make_rubric()
                    
                    st.success("✅ Rubric built successfully!")
                    st.info(f"**Rubric Details:**\n- {len(rubric.requirements)} requirements\n- {len(rubric.judge_options)} judge options\n- Reward strategy: {rubric.reward_strategy.name}")
                    
                    # Store in session state for potential future use
                    st.session_state.built_rubric = rubric
                    
                except Exception as e:
                    st.error(f"Error building rubric: {str(e)}")
                    st.exception(e)
            else:
                st.error("Need at least one judge rewarder and one requirement!")
else:
    st.info("Configure your judge rewarders, requirements, and reward strategy to see a preview.")

# Footer
st.divider()
st.markdown("*Built with ❤️ using Streamlit*") 