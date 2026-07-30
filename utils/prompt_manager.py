
import os
import json
from dotenv import load_dotenv
from groq import Groq

# Load environment variables
load_dotenv()

# Master ATS Framework Directive for external LLMs (ChatGPT / Claude)
ATS_FRAMEWORK_DIRECTIVE = """

================================================================================
CRITICAL ATS & COPY-READY FRAMEWORK DIRECTIVES (MANDATORY EXECUTION RULES)
================================================================================
You MUST follow these strict rules for generating your output:

1. ZERO META-TALK & FLUFF (STRICT):
   - Do NOT include any intro or outro text (e.g., "Sure!", "Here is your profile...", "Hope this helps!").
   - Output ONLY the requested sections below.

2. STRUCTURED RESPONSE PROTOCOL:
   Your response MUST consist exclusively of the following two sections:

   SECTION 1: PASTE-READY LINKEDIN CONTENT
   - Provide the complete, finalized content ready for direct copy-pasting into LinkedIn.
   - Formatting rules:
     * Use unicode bullets (•) for all experience and bulleted items. Do NOT use hyphens (-), asterisks (*), or numbered lists.
     * Use plain text pipe separators (|) for headlines or sub-headers.
     * Avoid tables, markdown formatting blocks, or emojis that break ATS parsing.
     * Include high-density ATS-scannable keywords relevant to the target role and industry.
   - STAR Method Constraint:
     * Format EVERY experience bullet point using the STAR method: [Action Verb] + [Skill/Tools/Tech Stack Used] + [Quantified Result/Impact (% or $)].

   SECTION 2: ATS KEYWORD MATCH SCORECARD
   - Provide a concise summary checklist showing:
     * Hard Skills & Tech Stack included.
     * Action Verbs used.
     * Quantifiable Impact Metrics (% / $) incorporated into the text.
================================================================================
"""


def get_groq_api_key() -> str:
    """
    Retrieves the Groq API key from environment variables or .env file.
    """
    key = os.getenv("GROQ_API_KEY")
    if key:
        return key
    
    # Check if raw API key is in .env file (without key prefix or standard format)
    try:
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    line_str = line.strip()
                    if line_str.startswith("gsk_"):
                        return line_str
                    elif "GROQ_API_KEY=" in line_str:
                        return line_str.split("GROQ_API_KEY=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return None

def load_prompt_library() -> list:
    """
    Loads prompt templates from prompt_library.json.
    """
    dir_path = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(dir_path, "prompt_library.json")
    with open(file_path, "r") as f:
        return json.load(f)

def select_prompts_fallback(profile_sections: dict, strategy_inputs: dict) -> list:
    """
    Fallback keyword-matching heuristic.
    Matches words in target_gaps or prompt descriptions with strategy_inputs or profile weaknesses.
    """
    library = load_prompt_library()
    selected_ids = []
    
    # Collect all words from strategy inputs
    search_terms = set()
    for val in strategy_inputs.values():
        if val:
            if isinstance(val, list):
                for v in val:
                    search_terms.update(str(v).lower().replace(",", " ").replace(";", " ").split())
            else:
                search_terms.update(str(val).lower().replace(",", " ").replace(";", " ").split())
            
    # Always include the basic audit and visual strategy
    selected_ids.append(1) # Complete PDF Profile Audit
    selected_ids.append(2) # Profile Visual Branding Strategy
    
    # Check other prompts
    for p in library:
        pid = p.get("id")
        if pid in selected_ids:
            continue
            
        tags = [t.lower() for t in p.get("target_gaps", [])]
        desc = p.get("description", "").lower()
        title = p.get("title", "").lower()
        
        # Check if any search term matches tags, title or description
        match = False
        for term in search_terms:
            if len(term) < 3:
                continue
            if term in tags or term in desc or term in title:
                match = True
                break
                
        if match:
            selected_ids.append(pid)
            
    # If still too few, add a few popular ones
    popular_fallbacks = [4, 8, 12, 17]
    for p_id in popular_fallbacks:
        if p_id not in selected_ids and any(p.get("id") == p_id for p in library):
            selected_ids.append(p_id)
            
    return sorted(list(set(selected_ids)))

def analyze_gaps_with_groq(profile_sections: dict, strategy_inputs: dict) -> dict:
    """
    Queries Groq API (llama-3.3-70b-versatile) to run a gap analysis and select prompts.
    Maps populated prompts directly inside the gap payload.
    """
    library = load_prompt_library()
    prompt_map = {p.get("id"): p for p in library}
    api_key = get_groq_api_key()
    
    if not api_key:
        fallback_ids = select_prompts_fallback(profile_sections, strategy_inputs)
        gaps = []
        for pid in fallback_ids[:3]:
            p_obj = prompt_map.get(pid)
            p_title = clean_title(p_obj.get("title", "Optimizer Prompt")) if p_obj else "Optimizer Prompt"
            p_prompt = p_obj.get("prompt", "") if p_obj else ""
            populated = populate_prompt_template(p_prompt, profile_sections, strategy_inputs) if p_prompt else ""
            gaps.append({
                "title": f"Profile Optimization: {p_title}",
                "location": p_obj.get("section", "General Profile") if p_obj else "General Profile",
                "profile_excerpt": "N/A",
                "specific_issue": "GROQ_API_KEY environment variable is missing or unconfigured.",
                "strategic_impact": "The application could not connect to Groq API because GROQ_API_KEY is not configured.",
                "why_it_matters": "The application could not connect to Groq API because GROQ_API_KEY is not configured.",
                "recommended_prompt_id": pid,
                "recommended_prompt_title": p_title,
                "populated_prompt": populated
            })
        return {
            "gaps": gaps,
            "selected_prompt_ids": fallback_ids
        }
        
    prompt_choices = []
    for p in library:
        prompt_choices.append({
            "id": p.get("id"),
            "title": p.get("title"),
            "description": p.get("description"),
            "target_gaps": p.get("target_gaps", [])
        })
        
    system_instruction = (
        "You are an expert technical recruiter and personal branding strategist.\n"
        "Analyze the user's LinkedIn profile sections and their target career strategy thoroughly.\n"
        "Perform a deep gap analysis between their current profile text and their target role, industry, and decision maker.\n"
        "Recommend the most relevant prompt templates from the catalog to help them optimize their profile.\n"
        "Analyze the profile thoroughly against the target strategy and return ALL genuine positioning gaps found. Do not limit the count; return as many or as few as actually exist, ordered strictly by severity (highest strategic impact first).\n"
        "You must respond in JSON format with a single key 'gap_analysis' containing the list of all identified gaps.\n"
        "Each object in the 'gap_analysis' list must have exactly six keys:\n"
        "   - 'title': A sharp, concise gap title (e.g. 'Missing Quantifiable Metrics in Leadership Roles')\n"
        "   - 'location': Exact section or role in the profile where the issue exists (e.g. 'Experience — Senior Full Stack Lead')\n"
        "   - 'profile_excerpt': An exact quote or concise summary of the weak/flawed text found in their PDF profile\n"
        "   - 'specific_issue': Detailed explanation of exactly what is wrong or missing in that specific excerpt\n"
        "   - 'strategic_impact': Detailed explanation of why this specific flaw turns off their target decision maker (e.g. 'Technical Recruiters filter out candidates who list duties without mentioning tech stack or scale metrics.')\n"
        "   - 'recommended_prompt_id': The integer ID of the recommended prompt template from the catalog that best addresses this specific gap.\n"
        "Make sure to return ONLY a valid JSON object."
    )
    
    # Preprocess list-based strategy inputs to strings
    target_role_val = strategy_inputs.get('target_role', 'N/A')
    if isinstance(target_role_val, list):
        target_role_val = ", ".join(target_role_val)
    target_industry_val = strategy_inputs.get('target_industry', 'N/A')
    if isinstance(target_industry_val, list):
        target_industry_val = ", ".join(target_industry_val)
    decision_maker_val = strategy_inputs.get('decision_maker', 'N/A')
    if isinstance(decision_maker_val, list):
        decision_maker_val = ", ".join(decision_maker_val)
        
    user_message = f"""
Here is the user's strategy:
- Target Role: {target_role_val}
- Target Industry: {target_industry_val}
- Target Decision Maker: {decision_maker_val}
- Key Weakness/Gap to Address: {strategy_inputs.get('weakness', 'N/A')}
- Target Seniority: {strategy_inputs.get('seniority', 'N/A')}

Here are the extracted sections of the user's LinkedIn Profile:
- Summary/About:
{profile_sections.get('Summary', '')}
- Experience:
{profile_sections.get('Experience', '')}
- Education:
{profile_sections.get('Education', '')}
- Skills:
{profile_sections.get('Skills', '')}
- Honors & Awards:
{profile_sections.get('Honors', '')}

Here are the available prompt templates to recommend from (ID, Title, Description, target_gaps tags):
{json.dumps(prompt_choices, indent=2)}
"""
    
    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_message}
            ],
            response_format={"type": "json_object"},
            temperature=0.2
        )
        result = json.loads(response.choices[0].message.content)
        if not isinstance(result, dict) or ("gap_analysis" not in result and "gaps" not in result):
            raise ValueError("Invalid structure returned by Groq API")
        
        # Post-process gaps to ensure they conform to the new schema
        validated_gaps = []
        selected_prompt_ids = []
        gaps_list = result.get("gap_analysis", result.get("gaps", []))
        for gap in gaps_list:
            if isinstance(gap, dict):
                p_id = gap.get("recommended_prompt_id")
                try:
                    p_id = int(p_id) if p_id is not None else 1
                except ValueError:
                    p_id = 1
                strat_impact = gap.get("strategic_impact", gap.get("why_it_matters", gap.get("explanation", "No details provided")))
                
                prompt_obj = prompt_map.get(p_id)
                p_title = clean_title(prompt_obj.get("title", "")) if prompt_obj else ""
                p_prompt = prompt_obj.get("prompt", "") if prompt_obj else ""
                populated = populate_prompt_template(p_prompt, profile_sections, strategy_inputs) if p_prompt else ""

                validated_gaps.append({
                    "title": gap.get("title", gap.get("name", "Identified Gap")),
                    "location": gap.get("location", gap.get("section", "General Profile")),
                    "profile_excerpt": gap.get("profile_excerpt", gap.get("excerpt", "N/A")),
                    "specific_issue": gap.get("specific_issue", gap.get("issue", "No specific issue provided")),
                    "strategic_impact": strat_impact,
                    "why_it_matters": strat_impact,
                    "recommended_prompt_id": p_id,
                    "recommended_prompt_title": p_title,
                    "populated_prompt": populated
                })
                selected_prompt_ids.append(p_id)
            else:
                prompt_obj = prompt_map.get(1)
                p_title = clean_title(prompt_obj.get("title", "")) if prompt_obj else ""
                p_prompt = prompt_obj.get("prompt", "") if prompt_obj else ""
                populated = populate_prompt_template(p_prompt, profile_sections, strategy_inputs) if p_prompt else ""
                validated_gaps.append({
                    "title": "Identified Gap",
                    "location": "General Profile",
                    "profile_excerpt": "N/A",
                    "specific_issue": str(gap),
                    "strategic_impact": str(gap),
                    "why_it_matters": str(gap),
                    "recommended_prompt_id": 1,
                    "recommended_prompt_title": p_title,
                    "populated_prompt": populated
                })
                selected_prompt_ids.append(1)
                
        # Fallback if no prompt IDs were recommended
        if not selected_prompt_ids:
            selected_prompt_ids = select_prompts_fallback(profile_sections, strategy_inputs)
        else:
            # Always ensure basic audit is present
            if 1 not in selected_prompt_ids:
                selected_prompt_ids.append(1)
            selected_prompt_ids = sorted(list(set(selected_prompt_ids)))
            
        return {
            "gaps": validated_gaps,
            "selected_prompt_ids": selected_prompt_ids
        }
    except Exception as e:
        fallback_ids = select_prompts_fallback(profile_sections, strategy_inputs)
        gaps = []
        for pid in fallback_ids[:3]:
            p_obj = prompt_map.get(pid)
            p_title = clean_title(p_obj.get("title", "Optimizer Prompt")) if p_obj else "Optimizer Prompt"
            p_prompt = p_obj.get("prompt", "") if p_obj else ""
            populated = populate_prompt_template(p_prompt, profile_sections, strategy_inputs) if p_prompt else ""
            gaps.append({
                "title": f"Groq Query Gap: {p_title}",
                "location": p_obj.get("section", "General Profile") if p_obj else "General Profile",
                "profile_excerpt": "N/A",
                "specific_issue": f"Groq API call failed or timed out. Details: {str(e)}",
                "strategic_impact": f"Groq API call failed or timed out. Details: {str(e)}",
                "why_it_matters": f"Groq API call failed or timed out. Details: {str(e)}",
                "recommended_prompt_id": pid,
                "recommended_prompt_title": p_title,
                "populated_prompt": populated
            })
        return {
            "gaps": gaps,
            "selected_prompt_ids": fallback_ids
        }

def predict_career_next_step(pdf_text: str) -> dict:
    """
    Analyzes the user's PDF profile text using Groq JSON mode to predict their current role/industry
    and recommend logical next career targets.
    """
    api_key = get_groq_api_key()
    default_prediction = {
        "predicted_industry": "Software & Tech",
        "logical_next_role": "Senior / Staff Software Engineer",
        "logical_seniority": "Senior",
        "target_decision_maker": "Engineering Managers",
        "key_weakness": "Profile lacks quantifiable metrics/impact"
    }

    if not api_key or not pdf_text or not pdf_text.strip():
        return default_prediction

    system_instruction = (
        "You are an expert executive career strategist and technical recruiter.\n"
        "Analyze the provided LinkedIn profile text extracted from a PDF.\n"
        "Determine the candidate's current background and predict their logical next career move.\n"
        "Respond strictly in JSON format with a single object containing these exact 5 keys:\n"
        "  - 'predicted_industry': Candidate's current or adjacent target industry (e.g., 'Software & Tech', 'Fintech', 'Healthcare & Biotech', 'Cybersecurity', 'AI & Machine Learning').\n"
        "  - 'logical_next_role': Logical target role representing a clear step up (e.g., 'Senior / Staff Software Engineer', 'Engineering Manager / Director', 'Product Manager').\n"
        "  - 'logical_seniority': Target seniority level (e.g., 'Mid-Level', 'Senior', 'Lead', 'Director', 'Executive').\n"
        "  - 'target_decision_maker': Primary hiring decision maker/target reader (e.g., 'Engineering Managers', 'Technical Recruiters', 'Engineering Directors / VPs', 'Executive Recruiters').\n"
        "  - 'key_weakness': Likely positioning gap for this transition (e.g., 'Profile lacks quantifiable metrics/impact', 'Headline & Summary lack strategic positioning', 'Lacks demonstrated leadership & strategic scale').\n"
        "Make sure to return ONLY a valid JSON object."
    )

    user_message = f"Here is the candidate's profile text:\n\n{pdf_text[:4000]}"

    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_message}
            ],
            response_format={"type": "json_object"},
            temperature=0.2
        )
        result = json.loads(response.choices[0].message.content)
        if isinstance(result, dict):
            return {
                "predicted_industry": result.get("predicted_industry", default_prediction["predicted_industry"]),
                "logical_next_role": result.get("logical_next_role", default_prediction["logical_next_role"]),
                "logical_seniority": result.get("logical_seniority", default_prediction["logical_seniority"]),
                "target_decision_maker": result.get("target_decision_maker", default_prediction["target_decision_maker"]),
                "key_weakness": result.get("key_weakness", default_prediction["key_weakness"])
            }
        return default_prediction
    except Exception:
        return default_prediction

def clean_title(raw_title: str) -> str:
    """
    Strips prompt numbers, prefixes (e.g. 'Prompt #1:', '01 '), and parenthetical category text from raw prompt titles.
    Example: 'Prompt #1: Complete PDF Profile Audit (01 Profile Foundations & Audit)' -> 'Complete PDF Profile Audit'
    """
    import re
    if not raw_title:
        return ""
    
    # Remove leading prefixes like 'Prompt #1:', 'Prompt 1:', '01 ', etc.
    cleaned = re.sub(r"^(?:Prompt\s*#?\d+:?|\d+[\.\s-]+)", "", raw_title, flags=re.IGNORECASE).strip()
    
    # Remove parenthetical details at the end like '(01 Profile Foundations & Audit)' or '(#13)'
    cleaned = re.sub(r"\s*\([^)]*\)$", "", cleaned).strip()
    
    return cleaned

def populate_prompt_template(template: str, profile_sections: dict, strategy_inputs: dict) -> str:
    """
    Replaces dynamic placeholders with user PDF data and strategy inputs,
    and appends the master ATS_FRAMEWORK_DIRECTIVE.
    """
    replacements = {
        "[YOUR TARGET INDUSTRY]": strategy_inputs.get("target_industry", ""),
        "[TARGET INDUSTRY]": strategy_inputs.get("target_industry", ""),
        "[YOUR TARGET ROLE]": strategy_inputs.get("target_role", ""),
        "[TARGET ROLE]": strategy_inputs.get("target_role", ""),
        "[DECISION MAKER]": strategy_inputs.get("decision_maker", ""),
        "[DECISION_MAKER]": strategy_inputs.get("decision_maker", ""),
        "[WEAKNESS]": strategy_inputs.get("weakness", ""),
        "[SENIORITY]": strategy_inputs.get("seniority", ""),
        "[PASTE EXTRACTED PDF TEXT HERE]": (
            f"Summary/About:\n{profile_sections.get('Summary', '')}\n\n"
            f"Experience:\n{profile_sections.get('Experience', '')}\n\n"
            f"Skills:\n{profile_sections.get('Skills', '')}\n\n"
            f"Education:\n{profile_sections.get('Education', '')}\n\n"
            f"Honors & Awards:\n{profile_sections.get('Honors', '')}"
        ).strip(),
        "[PASTE DUTIES]": profile_sections.get("Experience", ""),
        "[PASTE EXISTING SUMMARY]": profile_sections.get("Summary", ""),
        "[PASTE SKILLS LIST]": profile_sections.get("Skills", ""),
        "[PASTE PATENTS, CERTIFICATIONS, AND AWARDS FROM PDF]": profile_sections.get("Honors", ""),
        "[SUMMARY]": profile_sections.get("Summary", ""),
        "[EXPERIENCE]": profile_sections.get("Experience", ""),
        "[EDUCATION]": profile_sections.get("Education", ""),
        "[SKILLS]": profile_sections.get("Skills", ""),
        "[HONORS]": profile_sections.get("Honors", "")
    }
    
    filled_prompt = template
    for placeholder, value in replacements.items():
        if value is None:
            value = ""
        filled_prompt = filled_prompt.replace(placeholder, str(value))
        
    if ATS_FRAMEWORK_DIRECTIVE.strip() not in filled_prompt:
        filled_prompt = filled_prompt.strip() + "\n\n" + ATS_FRAMEWORK_DIRECTIVE.strip()
        
    return filled_prompt


#-------------------------------------

# import os
# import json
# from dotenv import load_dotenv
# from groq import Groq

# # Load environment variables
# load_dotenv()

# def get_groq_api_key() -> str:
#     """
#     Retrieves the Groq API key from environment variables or .env file.
#     """
#     key = os.getenv("GROQ_API_KEY")
#     if key:
#         return key
    
#     # Check if raw API key is in .env file (without key prefix or standard format)
#     try:
#         env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
#         if os.path.exists(env_path):
#             with open(env_path, "r") as f:
#                 for line in f:
#                     line_str = line.strip()
#                     if line_str.startswith("gsk_"):
#                         return line_str
#                     elif "GROQ_API_KEY=" in line_str:
#                         return line_str.split("GROQ_API_KEY=", 1)[1].strip().strip('"').strip("'")
#     except Exception:
#         pass
#     return None

# def load_prompt_library() -> list:
#     """
#     Loads prompt templates from prompt_library.json.
#     """
#     dir_path = os.path.dirname(os.path.abspath(__file__))
#     file_path = os.path.join(dir_path, "prompt_library.json")
#     with open(file_path, "r") as f:
#         return json.load(f)

# def select_prompts_fallback(profile_sections: dict, strategy_inputs: dict) -> list:
#     """
#     Fallback keyword-matching heuristic.
#     Matches words in target_gaps or prompt descriptions with strategy_inputs or profile weaknesses.
#     """
#     library = load_prompt_library()
#     selected_ids = []
    
#     # Collect all words from strategy inputs
#     search_terms = set()
#     for val in strategy_inputs.values():
#         if val:
#             if isinstance(val, list):
#                 for v in val:
#                     search_terms.update(str(v).lower().replace(",", " ").replace(";", " ").split())
#             else:
#                 search_terms.update(str(val).lower().replace(",", " ").replace(";", " ").split())
            
#     # Always include the basic audit and visual strategy
#     selected_ids.append(1) # Complete PDF Profile Audit
#     selected_ids.append(2) # Profile Visual Branding Strategy
    
#     # Check other prompts
#     for p in library:
#         pid = p.get("id")
#         if pid in selected_ids:
#             continue
            
#         tags = [t.lower() for t in p.get("target_gaps", [])]
#         desc = p.get("description", "").lower()
#         title = p.get("title", "").lower()
        
#         # Check if any search term matches tags, title or description
#         match = False
#         for term in search_terms:
#             if len(term) < 3:
#                 continue
#             if term in tags or term in desc or term in title:
#                 match = True
#                 break
                
#         if match:
#             selected_ids.append(pid)
            
#     # If still too few, add a few popular ones
#     popular_fallbacks = [4, 8, 12, 17]
#     for p_id in popular_fallbacks:
#         if p_id not in selected_ids and any(p.get("id") == p_id for p in library):
#             selected_ids.append(p_id)
            
#     return sorted(list(set(selected_ids)))

# def analyze_gaps_with_groq(profile_sections: dict, strategy_inputs: dict) -> dict:
#     """
#     Queries Groq API (llama-3.3-70b-versatile) to run a gap analysis and select prompts.
#     """
#     api_key = get_groq_api_key()
#     if not api_key:
#         return {
#             "gaps": [
#                 {
#                     "title": "API Key Missing",
#                     "location": "System Configuration",
#                     "profile_excerpt": "N/A",
#                     "specific_issue": "GROQ_API_KEY environment variable is missing or unconfigured.",
#                     "strategic_impact": "The application could not connect to Groq API because GROQ_API_KEY is not configured.",
#                     "why_it_matters": "The application could not connect to Groq API because GROQ_API_KEY is not configured.",
#                     "recommended_prompt_id": 1
#                 }
#             ],
#             "selected_prompt_ids": select_prompts_fallback(profile_sections, strategy_inputs)
#         }
        
#     library = load_prompt_library()
#     prompt_choices = []
#     for p in library:
#         prompt_choices.append({
#             "id": p.get("id"),
#             "title": p.get("title"),
#             "description": p.get("description"),
#             "target_gaps": p.get("target_gaps", [])
#         })
        
#     system_instruction = (
#         "You are an expert technical recruiter and personal branding strategist.\n"
#         "Analyze the user's LinkedIn profile sections and their target career strategy.\n"
#         "Perform a deep gap analysis between their current profile text and their target role, industry, and decision maker.\n"
#         "Recommend the most relevant prompt templates from the catalog to help them optimize their profile.\n"
#         "You must respond in JSON format with a single key 'gap_analysis' containing a list of at most 3 specific, actionable gaps identified in their profile.\n"
#         "Each object in the 'gap_analysis' list must have exactly six keys:\n"
#         "   - 'title': A sharp, concise gap title (e.g. 'Missing Quantifiable Metrics in Leadership Roles')\n"
#         "   - 'location': Exact section or role in the profile where the issue exists (e.g. 'Experience — Senior Full Stack Lead')\n"
#         "   - 'profile_excerpt': An exact quote or concise summary of the weak/flawed text found in their PDF profile\n"
#         "   - 'specific_issue': Detailed explanation of exactly what is wrong or missing in that specific excerpt\n"
#         "   - 'strategic_impact': Detailed explanation of why this specific flaw turns off their target decision maker (e.g. 'Technical Recruiters filter out candidates who list duties without mentioning tech stack or scale metrics.')\n"
#         "   - 'recommended_prompt_id': The integer ID of the recommended prompt template from the catalog that best addresses this specific gap.\n"
#         "Make sure to return ONLY a valid JSON object."
#     )
    
#     # Preprocess list-based strategy inputs to strings
#     target_role_val = strategy_inputs.get('target_role', 'N/A')
#     if isinstance(target_role_val, list):
#         target_role_val = ", ".join(target_role_val)
#     target_industry_val = strategy_inputs.get('target_industry', 'N/A')
#     if isinstance(target_industry_val, list):
#         target_industry_val = ", ".join(target_industry_val)
#     decision_maker_val = strategy_inputs.get('decision_maker', 'N/A')
#     if isinstance(decision_maker_val, list):
#         decision_maker_val = ", ".join(decision_maker_val)
        
#     user_message = f"""
# Here is the user's strategy:
# - Target Role: {target_role_val}
# - Target Industry: {target_industry_val}
# - Target Decision Maker: {decision_maker_val}
# - Key Weakness/Gap to Address: {strategy_inputs.get('weakness', 'N/A')}
# - Target Seniority: {strategy_inputs.get('seniority', 'N/A')}

# Here are the extracted sections of the user's LinkedIn Profile:
# - Summary/About:
# {profile_sections.get('Summary', '')}
# - Experience:
# {profile_sections.get('Experience', '')}
# - Education:
# {profile_sections.get('Education', '')}
# - Skills:
# {profile_sections.get('Skills', '')}
# - Honors & Awards:
# {profile_sections.get('Honors', '')}

# Here are the available prompt templates to recommend from (ID, Title, Description, target_gaps tags):
# {json.dumps(prompt_choices, indent=2)}
# """
    
#     try:
#         client = Groq(api_key=api_key)
#         response = client.chat.completions.create(
#             model="llama-3.3-70b-versatile",
#             messages=[
#                 {"role": "system", "content": system_instruction},
#                 {"role": "user", "content": user_message}
#             ],
#             response_format={"type": "json_object"},
#             temperature=0.2
#         )
#         result = json.loads(response.choices[0].message.content)
#         if not isinstance(result, dict) or ("gap_analysis" not in result and "gaps" not in result):
#             raise ValueError("Invalid structure returned by Groq API")
        
#         # Post-process gaps to ensure they conform to the new schema
#         validated_gaps = []
#         selected_prompt_ids = []
#         gaps_list = result.get("gap_analysis", result.get("gaps", []))
#         for gap in gaps_list:
#             if isinstance(gap, dict):
#                 p_id = gap.get("recommended_prompt_id")
#                 try:
#                     p_id = int(p_id) if p_id is not None else 1
#                 except ValueError:
#                     p_id = 1
#                 strat_impact = gap.get("strategic_impact", gap.get("why_it_matters", gap.get("explanation", "No details provided")))
#                 validated_gaps.append({
#                     "title": gap.get("title", gap.get("name", "Identified Gap")),
#                     "location": gap.get("location", gap.get("section", "General Profile")),
#                     "profile_excerpt": gap.get("profile_excerpt", gap.get("excerpt", "N/A")),
#                     "specific_issue": gap.get("specific_issue", gap.get("issue", "No specific issue provided")),
#                     "strategic_impact": strat_impact,
#                     "why_it_matters": strat_impact,
#                     "recommended_prompt_id": p_id
#                 })
#                 selected_prompt_ids.append(p_id)
#             else:
#                 validated_gaps.append({
#                     "title": "Identified Gap",
#                     "location": "General Profile",
#                     "profile_excerpt": "N/A",
#                     "specific_issue": str(gap),
#                     "strategic_impact": str(gap),
#                     "why_it_matters": str(gap),
#                     "recommended_prompt_id": 1
#                 })
#                 selected_prompt_ids.append(1)
                
#         # Fallback if no prompt IDs were recommended
#         if not selected_prompt_ids:
#             selected_prompt_ids = select_prompts_fallback(profile_sections, strategy_inputs)
#         else:
#             # Always ensure basic audit is present
#             if 1 not in selected_prompt_ids:
#                 selected_prompt_ids.append(1)
#             selected_prompt_ids = sorted(list(set(selected_prompt_ids)))
            
#         return {
#             "gaps": validated_gaps,
#             "selected_prompt_ids": selected_prompt_ids
#         }
#     except Exception as e:
#         fallback_ids = select_prompts_fallback(profile_sections, strategy_inputs)
#         return {
#             "gaps": [
#                 {
#                     "title": "Groq API Query Error",
#                     "location": "API Communication",
#                     "profile_excerpt": "N/A",
#                     "specific_issue": "Groq API call failed or timed out.",
#                     "strategic_impact": f"Groq API call failed or timed out. Details: {str(e)}",
#                     "why_it_matters": f"Groq API call failed or timed out. Details: {str(e)}",
#                     "recommended_prompt_id": fallback_ids[0] if fallback_ids else 1
#                 }
#             ],
#             "selected_prompt_ids": fallback_ids
#         }

# def populate_prompt_template(template: str, profile_sections: dict, strategy_inputs: dict) -> str:
#     """
#     Replaces dynamic placeholders with user PDF data and strategy inputs.
#     """
#     replacements = {
#         "[YOUR TARGET INDUSTRY]": strategy_inputs.get("target_industry", ""),
#         "[TARGET INDUSTRY]": strategy_inputs.get("target_industry", ""),
#         "[YOUR TARGET ROLE]": strategy_inputs.get("target_role", ""),
#         "[TARGET ROLE]": strategy_inputs.get("target_role", ""),
#         "[DECISION MAKER]": strategy_inputs.get("decision_maker", ""),
#         "[DECISION_MAKER]": strategy_inputs.get("decision_maker", ""),
#         "[WEAKNESS]": strategy_inputs.get("weakness", ""),
#         "[SENIORITY]": strategy_inputs.get("seniority", ""),
#         "[PASTE EXTRACTED PDF TEXT HERE]": (
#             f"Summary/About:\n{profile_sections.get('Summary', '')}\n\n"
#             f"Experience:\n{profile_sections.get('Experience', '')}\n\n"
#             f"Skills:\n{profile_sections.get('Skills', '')}\n\n"
#             f"Education:\n{profile_sections.get('Education', '')}\n\n"
#             f"Honors & Awards:\n{profile_sections.get('Honors', '')}"
#         ).strip(),
#         "[PASTE DUTIES]": profile_sections.get("Experience", ""),
#         "[PASTE EXISTING SUMMARY]": profile_sections.get("Summary", ""),
#         "[PASTE SKILLS LIST]": profile_sections.get("Skills", ""),
#         "[PASTE PATENTS, CERTIFICATIONS, AND AWARDS FROM PDF]": profile_sections.get("Honors", ""),
#         "[SUMMARY]": profile_sections.get("Summary", ""),
#         "[EXPERIENCE]": profile_sections.get("Experience", ""),
#         "[EDUCATION]": profile_sections.get("Education", ""),
#         "[SKILLS]": profile_sections.get("Skills", ""),
#         "[HONORS]": profile_sections.get("Honors", "")
#     }
    
#     filled_prompt = template
#     for placeholder, value in replacements.items():
#         if value is None:
#             value = ""
#         filled_prompt = filled_prompt.replace(placeholder, str(value))
        
#     return filled_prompt
