import streamlit as st
import streamlit.components.v1 as components
import json
from utils.pdf_parser import extract_text_from_pdf, parse_pdf_sections
from utils.prompt_manager import (
    load_prompt_library,
    analyze_gaps_with_groq,
    populate_prompt_template,
    predict_career_next_step,
    extract_nlp_themes_from_text,
    clean_title
)

def render_copy_button(text: str, button_id: str or int):
    """
    Renders a dedicated 1-click clipboard copy button using HTML/JS.
    """
    json_text = json.dumps(text)
    html_code = f"""
    <div style="font-family: sans-serif; display: flex; align-items: center; margin-bottom: 8px;">
      <button id="copy_btn_{button_id}" onclick="doCopy_{button_id}()" style="
        background-color: #0077b5;
        color: #ffffff;
        border: none;
        padding: 8px 16px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 13px;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        transition: all 0.2s ease;
      ">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
        Copy Prompt to Clipboard
      </button>
      <span id="copy_msg_{button_id}" style="margin-left: 10px; color: #28a745; font-weight: 600; font-size: 13px; display: none;">✓ Copied to clipboard!</span>
    </div>
    <script>
    function doCopy_{button_id}() {{
      const text = {json_text};
      function showSuccess() {{
        const btn = document.getElementById("copy_btn_{button_id}");
        const msg = document.getElementById("copy_msg_{button_id}");
        if (btn) {{
          btn.style.backgroundColor = "#28a745";
          btn.innerHTML = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg> Copied!`;
        }}
        if (msg) msg.style.display = "inline";
        setTimeout(() => {{
          if (btn) {{
            btn.style.backgroundColor = "#0077b5";
            btn.innerHTML = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg> Copy Prompt to Clipboard`;
          }}
          if (msg) msg.style.display = "none";
        }}, 2500);
      }}

      if (navigator.clipboard && window.isSecureContext) {{
        navigator.clipboard.writeText(text).then(showSuccess).catch(fallbackCopy);
      }} else {{
        fallbackCopy();
      }}

      function fallbackCopy() {{
        const ta = document.createElement("textarea");
        ta.value = text;
        ta.style.position = "fixed";
        ta.style.opacity = "0";
        document.body.appendChild(ta);
        ta.focus();
        ta.select();
        try {{
          document.execCommand('copy');
          showSuccess();
        }} catch(e) {{
          console.error("Copy failed", e);
        }}
        document.body.removeChild(ta);
      }}
    }}
    </script>
    """
    components.html(html_code, height=45)

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
if "strategy_defaults" not in st.session_state:
    st.session_state.strategy_defaults = {}
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
            with st.spinner("Extracting text and running AI career prediction..."):
                pdf_bytes = uploaded_file.read()
                raw_text = extract_text_from_pdf(pdf_bytes)
                sections = parse_pdf_sections(raw_text)
                prediction = predict_career_next_step(raw_text)
                
                # Store in session state
                st.session_state.pdf_text = raw_text
                st.session_state.profile_sections = sections
                st.session_state.strategy_defaults = prediction
                
            st.success("Successfully parsed your LinkedIn profile PDF and predicted target career strategy!")
            
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
    industry_options = ["Software & Tech", "Fintech", "Healthcare & Biotech", "E-commerce & Retail", "Cybersecurity", "Artificial Intelligence", "➕ Other / Type Custom..."]
    # Role curated presets
    role_options = ["Software Engineer", "Senior / Staff Software Engineer", "Engineering Manager / Director", "Product Manager", "Data Scientist / AI Engineer", "➕ Other / Type Custom..."]
    # Targets / Decision Makers presets
    target_options = ["Technical Recruiters", "Engineering Managers", "Engineering Directors / VPs", "Executive Recruiters", "C-Level Executives", "➕ Other / Type Custom..."]
    # Weakness presets
    weakness_options = ["Profile lacks quantifiable metrics/impact", "Transitioning to a new role/industry", "Headline & Summary lack strategic positioning", "Skills section not aligned with target job keywords", "Lacks demonstrated leadership & strategic scale", "➕ Other / Type Custom..."]
    
    # Read previous inputs or default AI predictions to set default values
    defaults = st.session_state.get("strategy_defaults", {})
    prev_industry = st.session_state.strategy_inputs.get("target_industry") or defaults.get("predicted_industry", "")
    prev_role = st.session_state.strategy_inputs.get("target_role") or defaults.get("logical_next_role", "")
    prev_target = st.session_state.strategy_inputs.get("decision_maker") or defaults.get("target_decision_maker", "")
    prev_user_text = (
        st.session_state.strategy_inputs.get("user_text")
        or st.session_state.strategy_inputs.get("weakness")
        or defaults.get("key_weakness", "")
    )
    prev_seniority = st.session_state.strategy_inputs.get("seniority") or defaults.get("logical_seniority", "")
    
    # Find matching preset index or return None for placeholder display
    def get_preset_index(val, options):
        if not val:
            return None
        if val in options:
            return options.index(val)
        return options.index("➕ Other / Type Custom...")
        
    with st.form("strategy_form"):
        # Target Industry Selection
        industry_sel = st.selectbox(
            "Target Industry",
            options=industry_options,
            index=get_preset_index(prev_industry, industry_options),
            placeholder="Select or type target industry..."
        )
        custom_industry = ""
        if industry_sel == "➕ Other / Type Custom..." or industry_sel == "Other (Specify custom...)":
            custom_industry = st.text_input("Enter Custom Target Industry", value=prev_industry if prev_industry not in industry_options else "", placeholder="e.g. Clean Energy, Robotics")
            
        # Target Role Selection
        role_sel = st.selectbox(
            "Target Role",
            options=role_options,
            index=get_preset_index(prev_role, role_options),
            placeholder="Select or type target role..."
        )
        custom_role = ""
        if role_sel == "➕ Other / Type Custom..." or role_sel == "Other (Specify custom...)":
            custom_role = st.text_input("Enter Custom Target Role", value=prev_role if prev_role not in role_options else "", placeholder="e.g. Principal Distributed Systems Engineer")

        # Seniority selection
        seniority_options = ["Junior", "Mid-Level", "Senior", "Lead", "Director", "Executive"]
        seniority_idx = seniority_options.index(prev_seniority) if prev_seniority in seniority_options else None
        seniority = st.selectbox(
            "Target Seniority Level",
            options=seniority_options,
            index=seniority_idx,
            placeholder="Select target seniority level..."
        )

        # Target Decision Maker Selection
        default_targets = []
        if prev_target:
            if prev_target in target_options:
                default_targets = [prev_target]
            else:
                default_targets = ["➕ Other / Type Custom..."]
        target_sel = st.multiselect(
            "Target Decision Maker / Reader",
            options=target_options,
            default=default_targets,
            placeholder="Select target decision maker(s)..."
        )
        custom_target = ""
        if "➕ Other / Type Custom..." in target_sel or "Other (Specify custom...)" in target_sel:
            custom_target = st.text_input("Enter Custom Target Decision Maker", value=prev_target if prev_target not in target_options else "", placeholder="e.g. Startup Founders, Venture Capitalists")
            
        # Free-Text Career Goals & Profile Challenges
        user_text_input = st.text_area(
            "Describe your main career goals, target transition, or profile challenges in your own words:",
            value=prev_user_text,
            height=130,
            placeholder="e.g., I'm a Senior Backend Engineer aiming to transition into an AI/ML Lead role. My current profile highlights legacy Java work, but I want to emphasize my recent PyTorch projects and team mentoring..."
        )
        
        submitted = st.form_submit_button("Run AI Gap Analysis 🚀")
        
        if submitted:
            final_industry = custom_industry if (industry_sel in ["➕ Other / Type Custom...", "Other (Specify custom...)"]) else (industry_sel if industry_sel else "")
            final_role = custom_role if (role_sel in ["➕ Other / Type Custom...", "Other (Specify custom...)"]) else (role_sel if role_sel else "")
            final_user_text = user_text_input.strip() if user_text_input else ""
            if not final_user_text:
                final_user_text = "Optimize profile positioning for target role and industry."
            
            # Combine multiselect options
            targets_list = []
            for t in target_sel:
                if t in ["➕ Other / Type Custom...", "Other (Specify custom...)"]:
                    if custom_target:
                        targets_list.append(custom_target)
                else:
                    targets_list.append(t)
            final_target = ", ".join(targets_list) if targets_list else "General Readers"
            
            if not final_role or not final_industry:
                st.error("Please select or enter both Target Role and Target Industry to proceed.")
            else:
                with st.spinner("Extracting positioning themes and keywords from your response..."):
                    nlp_themes = extract_nlp_themes_from_text(final_user_text)

                st.session_state.strategy_inputs = {
                    "target_role": final_role,
                    "target_industry": final_industry,
                    "seniority": seniority or "Senior",
                    "decision_maker": final_target,
                    "user_text": final_user_text,
                    "weakness": nlp_themes.get("user_core_challenge", final_user_text),
                    "user_core_challenge": nlp_themes.get("user_core_challenge", final_user_text),
                    "target_skill_keywords": nlp_themes.get("target_skill_keywords", []),
                    "career_transition_narrative": nlp_themes.get("career_transition_narrative", final_user_text)
                }
                
                with st.spinner("Analyzing profile gaps and generating tailored ATS prompts..."):
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
    
    # Single Unified Section: Identified Gaps & Tailored Fixes
    st.subheader("🎯 Identified Gaps & Tailored Fixes")
    gap_data = st.session_state.gap_analysis_results or {}
    gaps = gap_data.get("gaps", [])
    
    if gaps:
        for idx, gap in enumerate(gaps):
            gap_title = gap.get("title", "Identified Gap")
            gap_location = gap.get("location", "General Profile")
            profile_excerpt = gap.get("profile_excerpt", "N/A")
            specific_issue = gap.get("specific_issue", "")
            strategic_impact = gap.get("strategic_impact", gap.get("why_it_matters", gap.get("explanation", "N/A")))
            recommended_id = gap.get("recommended_prompt_id")
            
            prompt_obj = prompt_map.get(recommended_id) if recommended_id else None
            prompt_title = gap.get("recommended_prompt_title") or (clean_title(prompt_obj.get("title", "")) if prompt_obj else "Tailored Fix")
            
            populated_prompt = gap.get("populated_prompt")
            if not populated_prompt and prompt_obj:
                populated_prompt = populate_prompt_template(
                    prompt_obj.get("prompt", ""),
                    st.session_state.profile_sections,
                    st.session_state.strategy_inputs
                )
                
            with st.expander(f"⚠️ {gap_title} — Location: {gap_location}", expanded=True):
                st.markdown(f"**Location:** `{gap_location}`")
                if profile_excerpt and profile_excerpt != "N/A":
                    st.info(f"**Current Profile Excerpt:**\n\n\"{profile_excerpt}\"")
                if specific_issue:
                    st.markdown(f"**Specific Issue:** {specific_issue}")
                st.warning(f"**Strategic Impact:** {strategic_impact}")
                
                if populated_prompt:
                    st.markdown(f"**Tailored Fix Prompt ({prompt_title}):**")
                    render_copy_button(populated_prompt, f"gap_{idx}_{recommended_id}")
                    st.code(populated_prompt, language="markdown", wrap_lines=True)
    else:
        st.info("No major profile gaps identified. Your profile appears strong for target positioning.")
        
    st.markdown("<br>", unsafe_allow_html=True)
            
    # Reset/Restart Option
    if st.button("🔄 Start New Optimization"):
        st.session_state.step = 1
        st.session_state.pdf_text = ""
        st.session_state.profile_sections = None
        st.session_state.strategy_inputs = {}
        st.session_state.gap_analysis_results = None
        st.rerun()




#-----------------------------


# import streamlit as st
# import streamlit.components.v1 as components
# import json
# from utils.pdf_parser import extract_text_from_pdf, parse_pdf_sections
# from utils.prompt_manager import (
#     load_prompt_library,
#     analyze_gaps_with_groq,
#     populate_prompt_template
# )

# def render_copy_button(text: str, button_id: str or int):
#     """
#     Renders a dedicated 1-click clipboard copy button using HTML/JS.
#     """
#     json_text = json.dumps(text)
#     html_code = f"""
#     <div style="font-family: sans-serif; display: flex; align-items: center; margin-bottom: 8px;">
#       <button id="copy_btn_{button_id}" onclick="doCopy_{button_id}()" style="
#         background-color: #0077b5;
#         color: #ffffff;
#         border: none;
#         padding: 8px 16px;
#         border-radius: 6px;
#         font-weight: 600;
#         font-size: 13px;
#         cursor: pointer;
#         display: inline-flex;
#         align-items: center;
#         gap: 6px;
#         box-shadow: 0 2px 4px rgba(0,0,0,0.1);
#         transition: all 0.2s ease;
#       ">
#         <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
#         Copy Prompt to Clipboard
#       </button>
#       <span id="copy_msg_{button_id}" style="margin-left: 10px; color: #28a745; font-weight: 600; font-size: 13px; display: none;">✓ Copied to clipboard!</span>
#     </div>
#     <script>
#     function doCopy_{button_id}() {{
#       const text = {json_text};
#       function showSuccess() {{
#         const btn = document.getElementById("copy_btn_{button_id}");
#         const msg = document.getElementById("copy_msg_{button_id}");
#         if (btn) {{
#           btn.style.backgroundColor = "#28a745";
#           btn.innerHTML = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg> Copied!`;
#         }}
#         if (msg) msg.style.display = "inline";
#         setTimeout(() => {{
#           if (btn) {{
#             btn.style.backgroundColor = "#0077b5";
#             btn.innerHTML = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg> Copy Prompt to Clipboard`;
#           }}
#           if (msg) msg.style.display = "none";
#         }}, 2500);
#       }}

#       if (navigator.clipboard && window.isSecureContext) {{
#         navigator.clipboard.writeText(text).then(showSuccess).catch(fallbackCopy);
#       }} else {{
#         fallbackCopy();
#       }}

#       function fallbackCopy() {{
#         const ta = document.createElement("textarea");
#         ta.value = text;
#         ta.style.position = "fixed";
#         ta.style.opacity = "0";
#         document.body.appendChild(ta);
#         ta.focus();
#         ta.select();
#         try {{
#           document.execCommand('copy');
#           showSuccess();
#         }} catch(e) {{
#           console.error("Copy failed", e);
#         }}
#         document.body.removeChild(ta);
#       }}
#     }}
#     </script>
#     """
#     components.html(html_code, height=45)

# # Page configuration
# st.set_page_config(
#     page_title="LinkedIn Profile AI Optimizer",
#     page_icon="💼",
#     layout="wide",
#     initial_sidebar_state="collapsed"
# )

# # Custom Premium Styling
# st.markdown("""
# <style>
#     .main {
#         background-color: #f8f9fa;
#     }
#     .stProgress > div > div > div > div {
#         background-color: #0077b5;
#     }
#     .step-title {
#         color: #0077b5;
#         font-family: 'Outfit', sans-serif;
#         font-weight: 700;
#         margin-bottom: 20px;
#     }
#     .card {
#         background-color: white;
#         padding: 24px;
#         border-radius: 12px;
#         box-shadow: 0 4px 6px rgba(0,0,0,0.05);
#         margin-bottom: 20px;
#         border-left: 5px solid #0077b5;
#     }
#     .gap-card {
#         background-color: #fff3cd;
#         padding: 15px;
#         border-radius: 8px;
#         border-left: 5px solid #ffc107;
#         margin-bottom: 10px;
#         color: #856404;
#     }
#     .pro-tip {
#         font-size: 0.9rem;
#         color: #555;
#         background-color: #e8f4fd;
#         padding: 10px;
#         border-radius: 6px;
#         border-left: 3px solid #0077b5;
#         margin-top: 10px;
#     }
#     .copy-box {
#         font-family: monospace;
#         background-color: #f1f3f4;
#         padding: 15px;
#         border-radius: 6px;
#         border: 1px solid #dadce0;
#     }
# </style>
# """, unsafe_allow_html=True)

# # Title
# st.title("💼 LinkedIn Profile AI Optimizer")
# st.markdown("Optimize your LinkedIn presence using advanced Groq AI Gap Analysis.")

# # Initialize session state
# if "step" not in st.session_state:
#     st.session_state.step = 1
# if "pdf_text" not in st.session_state:
#     st.session_state.pdf_text = ""
# if "profile_sections" not in st.session_state:
#     st.session_state.profile_sections = None
# if "strategy_inputs" not in st.session_state:
#     st.session_state.strategy_inputs = {}
# if "gap_analysis_results" not in st.session_state:
#     st.session_state.gap_analysis_results = None

# # Progress Bar
# progress_labels = ["Upload PDF Profile", "Define Positioning Strategy", "AI Gap Analysis & Prompts"]
# cols = st.columns(3)
# for idx, label in enumerate(progress_labels):
#     with cols[idx]:
#         if st.session_state.step == idx + 1:
#             st.markdown(f"**Step {idx+1}: {label}** 🔵")
#         elif st.session_state.step > idx + 1:
#             st.markdown(f"Step {idx+1}: {label} ✅")
#         else:
#             st.markdown(f"Step {idx+1}: {label} ⚪")

# st.progress(st.session_state.step / 3.0)
# st.markdown("---")

# # Wizard Steps
# if st.session_state.step == 1:
#     st.markdown("<h2 class='step-title'>Step 1: Upload LinkedIn Exported PDF</h2>", unsafe_allow_html=True)
#     st.info("Export your LinkedIn profile to PDF (More -> Save to PDF on your LinkedIn profile page) and upload it below.")
    
#     uploaded_file = st.file_uploader("Choose LinkedIn PDF Profile", type=["pdf"])
    
#     if uploaded_file is not None:
#         try:
#             with st.spinner("Extracting text and parsing profile sections..."):
#                 pdf_bytes = uploaded_file.read()
#                 raw_text = extract_text_from_pdf(pdf_bytes)
#                 sections = parse_pdf_sections(raw_text)
                
#                 # Store in session state
#                 st.session_state.pdf_text = raw_text
#                 st.session_state.profile_sections = sections
                
#             st.success("Successfully parsed your LinkedIn profile PDF!")
            
#             # Show preview of parsed sections
#             with st.expander("Preview Extracted Profile Sections"):
#                 for key, val in sections.items():
#                     st.subheader(key)
#                     if val:
#                         st.text(val[:300] + ("..." if len(val) > 300 else ""))
#                     else:
#                         st.caption("No data extracted for this section")
            
#             if st.button("Proceed to Strategy Form ➡️"):
#                 st.session_state.step = 2
#                 st.rerun()
                
#         except Exception as e:
#             st.error(f"Error parsing PDF file: {str(e)}")

# elif st.session_state.step == 2:
#     st.markdown("<h2 class='step-title'>Step 2: Target Positioning Strategy Form</h2>", unsafe_allow_html=True)
#     st.markdown("Provide context about your career target and potential positioning gaps to run the gap analysis.")
    
#     # Industry curated presets
#     industry_options = ["Software & Tech", "Fintech", "Healthcare & Biotech", "E-commerce & Retail", "Cybersecurity", "Artificial Intelligence", "➕ Other / Type Custom..."]
#     # Role curated presets
#     role_options = ["Software Engineer", "Senior / Staff Software Engineer", "Engineering Manager / Director", "Product Manager", "Data Scientist / AI Engineer", "➕ Other / Type Custom..."]
#     # Targets / Decision Makers presets
#     target_options = ["Technical Recruiters", "Engineering Managers", "Engineering Directors / VPs", "Executive Recruiters", "C-Level Executives", "➕ Other / Type Custom..."]
#     # Weakness presets
#     weakness_options = ["Profile lacks quantifiable metrics/impact", "Transitioning to a new role/industry", "Headline & Summary lack strategic positioning", "Skills section not aligned with target job keywords", "Lacks demonstrated leadership & strategic scale", "➕ Other / Type Custom..."]
    
#     # Read previous inputs to set default indexes
#     prev_industry = st.session_state.strategy_inputs.get("target_industry", "")
#     prev_role = st.session_state.strategy_inputs.get("target_role", "")
#     prev_target = st.session_state.strategy_inputs.get("decision_maker", "")
#     prev_weakness = st.session_state.strategy_inputs.get("weakness", "")
#     prev_seniority = st.session_state.strategy_inputs.get("seniority", "")
    
#     # Find matching preset index or return None for placeholder display
#     def get_preset_index(val, options):
#         if not val:
#             return None
#         if val in options:
#             return options.index(val)
#         return options.index("➕ Other / Type Custom...")
        
#     with st.form("strategy_form"):
#         # Target Industry Selection
#         industry_sel = st.selectbox(
#             "Target Industry",
#             options=industry_options,
#             index=get_preset_index(prev_industry, industry_options),
#             placeholder="Select or type target industry..."
#         )
#         custom_industry = ""
#         if industry_sel == "➕ Other / Type Custom..." or industry_sel == "Other (Specify custom...)":
#             custom_industry = st.text_input("Enter Custom Target Industry", value=prev_industry if prev_industry not in industry_options else "", placeholder="e.g. Clean Energy, Robotics")
            
#         # Target Role Selection
#         role_sel = st.selectbox(
#             "Target Role",
#             options=role_options,
#             index=get_preset_index(prev_role, role_options),
#             placeholder="Select or type target role..."
#         )
#         custom_role = ""
#         if role_sel == "➕ Other / Type Custom..." or role_sel == "Other (Specify custom...)":
#             custom_role = st.text_input("Enter Custom Target Role", value=prev_role if prev_role not in role_options else "", placeholder="e.g. Principal Distributed Systems Engineer")

#         # Seniority selection
#         seniority_options = ["Junior", "Mid-Level", "Senior", "Lead", "Director", "Executive"]
#         seniority_idx = seniority_options.index(prev_seniority) if prev_seniority in seniority_options else None
#         seniority = st.selectbox(
#             "Target Seniority Level",
#             options=seniority_options,
#             index=seniority_idx,
#             placeholder="Select target seniority level..."
#         )

#         # Target Decision Maker Selection
#         default_targets = []
#         if prev_target:
#             if prev_target in target_options:
#                 default_targets = [prev_target]
#             else:
#                 default_targets = ["➕ Other / Type Custom..."]
#         target_sel = st.multiselect(
#             "Target Decision Maker / Reader",
#             options=target_options,
#             default=default_targets,
#             placeholder="Select target decision maker(s)..."
#         )
#         custom_target = ""
#         if "➕ Other / Type Custom..." in target_sel or "Other (Specify custom...)" in target_sel:
#             custom_target = st.text_input("Enter Custom Target Decision Maker", value=prev_target if prev_target not in target_options else "", placeholder="e.g. Startup Founders, Venture Capitalists")
            
#         # Key Weakness / Gap Selection
#         weakness_sel = st.selectbox(
#             "Key Profile Weakness / Main Gap to Solve",
#             options=weakness_options,
#             index=get_preset_index(prev_weakness, weakness_options),
#             placeholder="Select key weakness or main gap to solve..."
#         )
#         custom_weakness = ""
#         if weakness_sel == "➕ Other / Type Custom..." or weakness_sel == "Other (Specify custom...)":
#             custom_weakness = st.text_area("Enter Custom Profile Weakness / Main Gap", value=prev_weakness if prev_weakness not in weakness_options else "", placeholder="e.g. Profile lacks quantifiable business metrics, or transitioning from QA to Dev")
        
#         submitted = st.form_submit_button("Run AI Gap Analysis 🚀")
        
#         if submitted:
#             final_industry = custom_industry if (industry_sel in ["➕ Other / Type Custom...", "Other (Specify custom...)"]) else (industry_sel if industry_sel else "")
#             final_role = custom_role if (role_sel in ["➕ Other / Type Custom...", "Other (Specify custom...)"]) else (role_sel if role_sel else "")
#             final_weakness = custom_weakness if (weakness_sel in ["➕ Other / Type Custom...", "Other (Specify custom...)"]) else (weakness_sel if weakness_sel else "")
            
#             # Combine multiselect options
#             targets_list = []
#             for t in target_sel:
#                 if t in ["➕ Other / Type Custom...", "Other (Specify custom...)"]:
#                     if custom_target:
#                         targets_list.append(custom_target)
#                 else:
#                     targets_list.append(t)
#             final_target = ", ".join(targets_list) if targets_list else "General Readers"
            
#             if not final_role or not final_industry:
#                 st.error("Please select or enter both Target Role and Target Industry to proceed.")
#             else:
#                 st.session_state.strategy_inputs = {
#                     "target_role": final_role,
#                     "target_industry": final_industry,
#                     "seniority": seniority or "Senior",
#                     "decision_maker": final_target,
#                     "weakness": final_weakness
#                 }
                
#                 with st.spinner("Analyzing profile gaps and selecting optimizer prompts..."):
#                     results = analyze_gaps_with_groq(st.session_state.profile_sections, st.session_state.strategy_inputs)
#                     st.session_state.gap_analysis_results = results
                
#                 st.session_state.step = 3
#                 st.rerun()
                
#     if st.button("⬅️ Back to Upload"):
#         st.session_state.step = 1
#         st.rerun()

# elif st.session_state.step == 3:
#     st.markdown("<h2 class='step-title'>Step 3: AI Gap Analysis & Tailored Prompts</h2>", unsafe_allow_html=True)
    
#     # Load prompt library and construct mapping
#     library = load_prompt_library()
#     prompt_map = {p.get("id"): p for p in library}
    
#     # Render identified gaps as clean expanders displaying excerpt, specific issue, strategic impact, and recommended fix
#     st.subheader("🔍 Identified Profile Gaps")
#     gaps = st.session_state.gap_analysis_results.get("gaps", [])
#     if gaps:
#         for gap in gaps:
#             gap_title = gap.get("title", "Identified Gap")
#             gap_location = gap.get("location", "General Profile")
#             profile_excerpt = gap.get("profile_excerpt", "N/A")
#             specific_issue = gap.get("specific_issue", "")
#             strategic_impact = gap.get("strategic_impact", gap.get("why_it_matters", gap.get("explanation", "N/A")))
#             recommended_id = gap.get("recommended_prompt_id")
#             prompt_obj = prompt_map.get(recommended_id)
#             prompt_title = prompt_obj.get("title", "Unknown Prompt") if prompt_obj else "Unknown Prompt"
            
#             with st.expander(label=f"⚠️ {gap_title} — Location: {gap_location}", expanded=True):
#                 st.markdown(f"**Location:** `{gap_location}`")
#                 if profile_excerpt and profile_excerpt != "N/A":
#                     st.info(f"**Current Profile Excerpt:**\n\n\"{profile_excerpt}\"")
#                 if specific_issue:
#                     st.markdown(f"**Specific Issue:** {specific_issue}")
#                 st.warning(f"**Strategic Impact:** {strategic_impact}")
#                 st.markdown(f"**Recommended Fix:** Prompt #{recommended_id} — **{prompt_title}**")
#     else:
#         st.info("No major gaps identified. Proceeding to recommended prompt templates.")
        
#     st.divider()
    
#     # Recommended Prompts inside collapsible expanders with 1-click copy box
#     st.subheader("💡 Recommended AI Optimizer Prompts")
#     st.markdown("Expand the recommended prompts below to view, copy, and run them in ChatGPT or Claude to optimize your profile sections.")
    
#     selected_ids = st.session_state.gap_analysis_results.get("selected_prompt_ids", [])
#     recommended_prompts = [p for p in library if p.get("id") in selected_ids]
    
#     if not recommended_prompts:
#         st.warning("No specific prompt matches found. Showing default general templates.")
#         recommended_prompts = [p for p in library if p.get("id") in [1, 2]]
        
#     for p in recommended_prompts:
#         p_id = p.get("id")
#         p_title = p.get("title")
#         p_section = p.get("section", "General")
#         with st.expander(label=f"💡 Prompt #{p_id}: {p_title} ({p_section})", expanded=False):
#             st.markdown(f"**Description:** {p.get('description')}")
            
#             # Populate prompt template
#             populated = populate_prompt_template(
#                 p.get("prompt", ""),
#                 st.session_state.profile_sections,
#                 st.session_state.strategy_inputs
#             )
            
#             # Dedicated 1-Click Copy Button
#             render_copy_button(populated, p_id)
            
#             # Display Copyable Box using st.code with wrap_lines=True
#             st.code(populated, language="markdown", wrap_lines=True)
            
#             # Display Pro Tips
#             tips = p.get("pro_tips", [])
#             if tips:
#                 st.markdown("**Pro Tips:**")
#                 for tip in tips:
#                     st.markdown(f"- {tip}")
#             st.markdown("<br>", unsafe_allow_html=True)
                
#     st.markdown("<br>", unsafe_allow_html=True)
            
#     # Reset/Restart Option
#     if st.button("🔄 Start New Optimization"):
#         st.session_state.step = 1
#         st.session_state.pdf_text = ""
#         st.session_state.profile_sections = None
#         st.session_state.strategy_inputs = {}
#         st.session_state.gap_analysis_results = None
#         st.rerun()

