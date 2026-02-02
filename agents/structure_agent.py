"""
Structure Agent - Stage 2
Identifies company departments and decision-makers based on company SIZE
"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# Decision-maker mapping by company size
DECISION_MAKERS_BY_SIZE = {
    "small": {
        "Engineering": ["CTO", "Tech Lead", "Founder"],
        "Sales": ["CEO", "Founder", "Sales Lead"],
        "Marketing": ["CEO", "Marketing Lead", "Founder"],
        "Finance": ["CEO", "Founder", "Accountant"],
        "Operations": ["CEO", "COO", "Founder"]
    },
    "medium": {
        "Engineering": ["CTO", "VP Engineering", "Engineering Director"],
        "Sales": ["VP Sales", "Sales Director", "Head of Sales"],
        "Marketing": ["CMO", "VP Marketing", "Marketing Director"],
        "Finance": ["CFO", "Finance Director", "Controller"],
        "Operations": ["COO", "Operations Director", "Head of Operations"],
        "Product": ["CPO", "VP Product", "Product Director"],
        "HR": ["CHRO", "HR Director", "Head of HR"]
    },
    "large": {
        "Engineering": ["SVP Engineering", "VP Engineering", "Engineering Director"],
        "Sales": ["CRO", "SVP Sales", "VP Sales", "Regional VP"],
        "Marketing": ["CMO", "SVP Marketing", "VP Marketing"],
        "Finance": ["CFO", "VP Finance", "Controller"],
        "Operations": ["COO", "SVP Operations", "VP Operations"],
        "Product": ["CPO", "SVP Product", "VP Product"],
        "IT": ["CIO", "VP IT", "IT Director"],
        "HR": ["CHRO", "SVP HR", "VP HR"]
    },
    "enterprise": {
        "Engineering": ["EVP Engineering", "SVP Engineering", "VP Engineering", "Global Head Engineering"],
        "Sales": ["CRO", "EVP Sales", "SVP Sales", "VP Sales", "Global Sales Director"],
        "Marketing": ["CMO", "EVP Marketing", "SVP Marketing", "VP Marketing"],
        "Finance": ["CFO", "EVP Finance", "SVP Finance", "VP Finance"],
        "Operations": ["COO", "EVP Operations", "SVP Operations"],
        "Product": ["CPO", "EVP Product", "SVP Product"],
        "IT": ["CIO", "CISO", "CTO", "VP IT"],
        "HR": ["CHRO", "EVP HR", "SVP HR"],
        "Legal": ["CLO", "General Counsel", "VP Legal"],
        "Strategy": ["CSO", "VP Strategy", "Head of Strategy"]
    }
}


STRUCTURE_PROMPT = """You are a company structure analysis agent.

Given a company and its size, identify:
1. Key departments/functions in this type of company
2. Who makes purchase decisions in each department (based on company size)
3. The typical organizational hierarchy

Use the company size to determine appropriate decision-maker levels:
- Small: Founders, CEOs, Leads
- Medium: VPs, Directors, Heads
- Large: SVPs, VPs, Senior Directors
- Enterprise: EVPs, SVPs, VPs, Global Heads

Output Rules:
- Only output valid JSON
- No markdown, no explanations

Required Output Format:
{
  "company_name": "company name",
  "company_size": "small/medium/large/enterprise",
  "departments": [
    {
      "name": "Engineering",
      "decision_makers": ["CTO", "VP Engineering"],
      "hierarchy_level": "C-Suite / VP / Director"
    }
  ],
  "recommended_targets": ["list of top 3-5 roles to target"]
}"""


def run(company_data: dict) -> dict:
    """
    Run company structure identification.
    
    Args:
        company_data: Dict with company info from discovery stage
        
    Returns:
        Dict with company structure and decision-makers
    """
    company_name = company_data.get("name", "Unknown")
    industry = company_data.get("industry", "")
    size = company_data.get("size", "medium").lower()
    
    # Normalize size
    if size not in DECISION_MAKERS_BY_SIZE:
        size = "medium"
    
    # Get pre-defined decision makers for this size
    decision_makers = DECISION_MAKERS_BY_SIZE.get(size, DECISION_MAKERS_BY_SIZE["medium"])
    
    # Use LLM to refine based on industry
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        # Return default structure without LLM
        return build_default_structure(company_name, size, decision_makers)
    
    client = Groq(api_key=api_key)
    
    try:
        user_input = f"Company: {company_name}, Industry: {industry}, Size: {size}"
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=1024,
            messages=[
                {"role": "system", "content": STRUCTURE_PROMPT},
                {"role": "user", "content": user_input}
            ]
        )
        
        result = response.choices[0].message.content
        
        try:
            parsed = json.loads(result)
        except json.JSONDecodeError:
            start = result.find("{")
            end = result.rfind("}") + 1
            if start >= 0 and end > start:
                parsed = json.loads(result[start:end])
            else:
                return build_default_structure(company_name, size, decision_makers)
        
        # Ensure we have recommended targets
        if not parsed.get("recommended_targets"):
            parsed["recommended_targets"] = get_top_targets(size)
        
        return parsed
            
    except Exception as e:
        return build_default_structure(company_name, size, decision_makers)


def build_default_structure(company_name: str, size: str, decision_makers: dict) -> dict:
    """Build default structure from predefined mapping."""
    departments = []
    for dept, roles in decision_makers.items():
        departments.append({
            "name": dept,
            "decision_makers": roles,
            "hierarchy_level": get_hierarchy_level(roles[0]) if roles else "Manager"
        })
    
    return {
        "company_name": company_name,
        "company_size": size,
        "departments": departments,
        "recommended_targets": get_top_targets(size)
    }


def get_hierarchy_level(role: str) -> str:
    """Determine hierarchy level from role title."""
    role_lower = role.lower()
    if any(x in role_lower for x in ["ceo", "cto", "cfo", "coo", "cmo", "cro", "chief"]):
        return "C-Suite"
    elif any(x in role_lower for x in ["evp", "svp", "senior vice"]):
        return "EVP/SVP"
    elif any(x in role_lower for x in ["vp", "vice president"]):
        return "VP"
    elif any(x in role_lower for x in ["director", "head of"]):
        return "Director"
    elif any(x in role_lower for x in ["manager", "lead"]):
        return "Manager"
    else:
        return "Individual Contributor"


def get_top_targets(size: str) -> list:
    """Get top target roles based on company size."""
    targets = {
        "small": ["CEO", "CTO", "Founder"],
        "medium": ["VP Engineering", "VP Sales", "CTO", "Director"],
        "large": ["SVP", "VP Engineering", "VP Sales", "CTO"],
        "enterprise": ["SVP", "VP", "Global Head", "Senior Director"]
    }
    return targets.get(size, targets["medium"])
