import os
import json
from dotenv import load_dotenv
from groq import Groq

# Load environment variables
load_dotenv()

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
    """
    api_key = get_groq_api_key()
    if not api_key:
        return {
            "gaps": [
                {
                    "title": "API Key Missing",
                    "explanation": "The application could not connect to Groq API because GROQ_API_KEY is not configured.",
                    "recommended_prompt_id": 1
                }
            ],
            "selected_prompt_ids": select_prompts_fallback(profile_sections, strategy_inputs)
        }
        
    library = load_prompt_library()
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
        "Analyze the user's LinkedIn profile sections and their target career strategy.\n"
        "Perform a gap analysis between their current profile and their target role/industry.\n"
        "Recommend the most relevant prompt templates from the catalog to help them optimize their profile.\n"
        "You must respond in JSON format with one key:\n"
        "1. 'gap_analysis': a list of objects detailing specific, actionable gaps identified in their profile. Each object must have exactly three keys:\n"
        "   - 'title': The name/title of the gap (e.g. 'Missing Quantifiable Impact')\n"
        "   - 'explanation': A brief explanation of what this means and why it matters\n"
        "   - 'recommended_prompt_id': The ID (integer) of the recommended prompt template from the catalog that best addresses this specific gap.\n"
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
                validated_gaps.append({
                    "title": gap.get("title", gap.get("name", "Identified Gap")),
                    "explanation": gap.get("explanation", gap.get("meaning", "No details provided")),
                    "recommended_prompt_id": p_id
                })
                selected_prompt_ids.append(p_id)
            else:
                validated_gaps.append({
                    "title": "Identified Gap",
                    "explanation": str(gap),
                    "recommended_prompt_id": 1
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
        return {
            "gaps": [
                {
                    "title": "Groq API Query Error",
                    "explanation": f"Groq API call failed or timed out. Details: {str(e)}",
                    "recommended_prompt_id": fallback_ids[0] if fallback_ids else 1
                }
            ],
            "selected_prompt_ids": fallback_ids
        }

def populate_prompt_template(template: str, profile_sections: dict, strategy_inputs: dict) -> str:
    """
    Replaces dynamic placeholders with user PDF data and strategy inputs.
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
        
    return filled_prompt
