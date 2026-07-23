import streamlit as st
import json
from utils.pdf_parser import extract_text_from_pdf, parse_pdf_sections
from utils.prompt_manager import (
    load_prompt_library,
    analyze_gaps_with_groq,
    populate_prompt_template
)

# Page configuration
st.set_page_config(
    page_title="LinkedIn Profile AI Optimizer",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom Premium Styling
st.markdown("""
<style>
    .main {
        background-color: #f8f9fa;
    }
    .stProgress > div > div > div > div {
        background-color: #0077b5;
    }
    .step-title {
        color: #0077b5;
        font-family: 'Outfit', sans-serif;
        font-weight: 700;
        margin-bottom: 20px;
    }
    .card {
        background-color: white;
        padding: 24px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 20px;
        border-left: 5px solid #0077b5;
    }
    .gap-card {
        background-color: #fff3cd;
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #ffc107;
        margin-bottom: 10px;
        color: #856404;
    }
    .pro-tip {
        font-size: 0.9rem;
        color: #555;
        background-color: #e8f4fd;
        padding: 10px;
        border-radius: 6px;
        border-left: 3px solid #0077b5;
        margin-top: 10px;
    }
    .copy-box {
        font-family: monospace;
        background-color: #f1f3f4;
        padding: 15px;
        border-radius: 6px;
        border: 1px solid #dadce0;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.title("💼 LinkedIn Profile AI Optimizer")
st.markdown("Optimize your LinkedIn presence using advanced Groq AI Gap Analysis.")

# Initialize session state
if "step" not in st.session_state:
    st.session_state.step = 1
if "pdf_text" not in st.session_state:
    st.session_state.pdf_text = ""
if "profile_sections" not in st.session_state:
    st.session_state.profile_sections = None
if "strategy_inputs" not in st.session_state:
    st.session_state.strategy_inputs = {}
if "gap_analysis_results" not in st.session_state:
    st.session_state.gap_analysis_results = None

# Progress Bar
progress_labels = ["Upload PDF Profile", "Define Positioning Strategy", "AI Gap Analysis & Prompts"]
cols = st.columns(3)
for idx, label in enumerate(progress_labels):
    with cols[idx]:
        if st.session_state.step == idx + 1:
            st.markdown(f"**Step {idx+1}: {label}** 🔵")
        elif st.session_state.step > idx + 1:
            st.markdown(f"Step {idx+1}: {label} ✅")
        else:
            st.markdown(f"Step {idx+1}: {label} ⚪")

st.progress(st.session_state.step / 3.0)
st.markdown("---")

# Wizard Steps
if st.session_state.step == 1:
    st.markdown("<h2 class='step-title'>Step 1: Upload LinkedIn Exported PDF</h2>", unsafe_allow_html=True)
    st.info("Export your LinkedIn profile to PDF (More -> Save to PDF on your LinkedIn profile page) and upload it below.")
    
    uploaded_file = st.file_uploader("Choose LinkedIn PDF Profile", type=["pdf"])
    
    if uploaded_file is not None:
        try:
            with st.spinner("Extracting text and parsing profile sections..."):
                pdf_bytes = uploaded_file.read()
                raw_text = extract_text_from_pdf(pdf_bytes)
                sections = parse_pdf_sections(raw_text)
                
                # Store in session state
                st.session_state.pdf_text = raw_text
                st.session_state.profile_sections = sections
                
            st.success("Successfully parsed your LinkedIn profile PDF!")
            
            # Show preview of parsed sections
            with st.expander("Preview Extracted Profile Sections"):
                for key, val in sections.items():
                    st.subheader(key)
                    if val:
                        st.text(val[:300] + ("..." if len(val) > 300 else ""))
                    else:
                        st.caption("No data extracted for this section")
            
            if st.button("Proceed to Strategy Form ➡️"):
                st.session_state.step = 2
                st.rerun()
                
        except Exception as e:
            st.error(f"Error parsing PDF file: {str(e)}")

elif st.session_state.step == 2:
    st.markdown("<h2 class='step-title'>Step 2: Target Positioning Strategy Form</h2>", unsafe_allow_html=True)
    st.markdown("Provide context about your career target and potential positioning gaps to run the gap analysis.")
    
    # Industry curated presets
    industry_presets = ["Software & Tech", "Fintech", "Healthcare & Biotech", "E-commerce & Retail", "Cybersecurity", "Artificial Intelligence", "Other (Specify custom...)"]
    # Role curated presets
    role_presets = ["Software Engineer", "Senior / Staff Software Engineer", "Engineering Manager / Director", "Product Manager", "Data Scientist / AI Engineer", "Other (Specify custom...)"]
    # Targets / Decision Makers presets
    target_presets = ["Technical Recruiters", "Engineering Managers", "Engineering Directors / VPs", "Executive Recruiters", "C-Level Executives", "Other (Specify custom...)"]
    
    # Read previous inputs to set default indexes
    prev_industry = st.session_state.strategy_inputs.get("target_industry", "")
    prev_role = st.session_state.strategy_inputs.get("target_role", "")
    prev_target = st.session_state.strategy_inputs.get("decision_maker", "")
    
    # Find matching preset index or default to Other/first
    def get_preset_index(val, presets):
        if val in presets:
            return presets.index(val)
        elif val:
            return presets.index("Other (Specify custom...)")
        return 0
        
    with st.form("strategy_form"):
        # Target Industry Selection
        industry_sel = st.selectbox(
            "Target Industry",
            industry_presets,
            index=get_preset_index(prev_industry, industry_presets)
        )
        custom_industry = ""
        if industry_sel == "Other (Specify custom...)":
            custom_industry = st.text_input("Enter Custom Target Industry", value=prev_industry if prev_industry not in industry_presets else "", placeholder="e.g. Clean Energy, Robotics")
            
        # Target Role Selection
        role_sel = st.selectbox(
            "Target Role",
            role_presets,
            index=get_preset_index(prev_role, role_presets)
        )
        custom_role = ""
        if role_sel == "Other (Specify custom...)":
            custom_role = st.text_input("Enter Custom Target Role", value=prev_role if prev_role not in role_presets else "", placeholder="e.g. Principal Distributed Systems Engineer")

        # Seniority selection
        seniority = st.selectbox(
            "Target Seniority Level",
            ["Junior", "Mid-Level", "Senior", "Lead", "Director", "Executive"],
            index=["Junior", "Mid-Level", "Senior", "Lead", "Director", "Executive"].index(st.session_state.strategy_inputs.get("seniority", "Senior"))
        )

        # Target Decision Maker Selection
        target_sel = st.multiselect(
            "Target Decision Maker / Reader",
            target_presets,
            default=[prev_target] if prev_target in target_presets else (["Technical Recruiters"] if not prev_target else ["Other (Specify custom...)"])
        )
        custom_target = ""
        if "Other (Specify custom...)" in target_sel:
            custom_target = st.text_input("Enter Custom Target Decision Maker", value=prev_target if prev_target not in target_presets else "", placeholder="e.g. Startup Founders, Venture Capitalists")
            
        weakness = st.text_area("Key Profile Weakness / Main Gap to Solve", value=st.session_state.strategy_inputs.get("weakness", ""), placeholder="e.g. Profile lacks quantifiable business metrics, or transitioning from QA to Dev")
        
        submitted = st.form_submit_button("Run AI Gap Analysis 🚀")
        
        if submitted:
            final_industry = custom_industry if industry_sel == "Other (Specify custom...)" else industry_sel
            final_role = custom_role if role_sel == "Other (Specify custom...)" else role_sel
            
            # Combine multiselect options
            targets_list = []
            for t in target_sel:
                if t == "Other (Specify custom...)":
                    if custom_target:
                        targets_list.append(custom_target)
                else:
                    targets_list.append(t)
            final_target = ", ".join(targets_list) if targets_list else "General Readers"
            
            if not final_role or not final_industry:
                st.error("Please provide both Target Role and Target Industry to proceed.")
            else:
                st.session_state.strategy_inputs = {
                    "target_role": final_role,
                    "target_industry": final_industry,
                    "seniority": seniority,
                    "decision_maker": final_target,
                    "weakness": weakness
                }
                
                with st.spinner("Analyzing profile gaps and selecting optimizer prompts..."):
                    results = analyze_gaps_with_groq(st.session_state.profile_sections, st.session_state.strategy_inputs)
                    st.session_state.gap_analysis_results = results
                
                st.session_state.step = 3
                st.rerun()
                
    if st.button("⬅️ Back to Upload"):
        st.session_state.step = 1
        st.rerun()

elif st.session_state.step == 3:
    st.markdown("<h2 class='step-title'>Step 3: AI Gap Analysis & Tailored Prompts</h2>", unsafe_allow_html=True)
    
    # Load prompt library and construct mapping
    library = load_prompt_library()
    prompt_map = {p.get("id"): p for p in library}
    
    # Render identified gaps as clean expanders using title and explanation
    st.subheader("🔍 Identified Profile Gaps")
    gaps = st.session_state.gap_analysis_results.get("gaps", [])
    if gaps:
        for gap in gaps:
            gap_title = gap.get("title", "Identified Gap")
            recommended_id = gap.get("recommended_prompt_id")
            prompt_obj = prompt_map.get(recommended_id)
            prompt_title = prompt_obj.get("title", "Unknown Prompt") if prompt_obj else "Unknown Prompt"
            
            with st.expander(label=gap_title, icon="⚠️"):
                st.markdown(f"**What This Means:** {gap.get('explanation', 'N/A')}")
                st.markdown(f"**How We Fix It:** Run the **{prompt_title}** prompt below.")
    else:
        st.info("No major gaps identified. Proceeding to recommended prompt templates.")
        
    st.divider()
    
    # Recommended Prompts inside collapsible expanders
    st.subheader("💡 Recommended AI Optimizer Prompts")
    st.markdown("Expand the recommended prompts below to view, copy, and run them in ChatGPT or Claude to optimize your profile sections.")
    
    selected_ids = st.session_state.gap_analysis_results.get("selected_prompt_ids", [])
    
    # Filter and find recommended prompts
    recommended_prompts = [p for p in library if p.get("id") in selected_ids]
    
    if not recommended_prompts:
        st.warning("No specific prompts matches found. Showing default general templates.")
        recommended_prompts = [p for p in library if p.get("id") in [1, 2]]
        
    for p in recommended_prompts:
        with st.expander(label=f"{p.get('section', 'General')} / {p.get('title')}", icon="💡", expanded=False):
            st.markdown(f"**Description:** {p.get('description')}")
            
            # Populate prompt template
            populated = populate_prompt_template(
                p.get("prompt", ""),
                st.session_state.profile_sections,
                st.session_state.strategy_inputs
            )
            
            # Display Copyable Box using st.code
            st.code(populated, language="markdown")
            
            # Display Pro Tips
            tips = p.get("pro_tips", [])
            if tips:
                st.markdown("**Pro Tips:**")
                for tip in tips:
                    st.markdown(f"- {tip}")
            st.markdown("<br>", unsafe_allow_html=True)
                
    st.markdown("<br>", unsafe_allow_html=True)
            
    # Reset/Restart Option
    if st.button("🔄 Start New Optimization"):
        st.session_state.step = 1
        st.session_state.pdf_text = ""
        st.session_state.profile_sections = None
        st.session_state.strategy_inputs = {}
        st.session_state.gap_analysis_results = None
        st.rerun()
