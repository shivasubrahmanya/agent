"""
Role Agent - Stage 3
Finds ACTUAL people at companies using LinkedIn search
Then assigns decision-making power scores
"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from groq import Groq
from dotenv import load_dotenv

# Import LinkedIn search
try:
    from services.linkedin_search import search_decision_makers, is_available as linkedin_available
    LINKEDIN_SEARCH_ENABLED = True
except ImportError:
    LINKEDIN_SEARCH_ENABLED = False
    linkedin_available = lambda: False

load_dotenv()

# Decision power by title pattern
DECISION_POWER_MAP = {
    "ceo": 10, "chief executive": 10, "founder": 10, "owner": 10,
    "cto": 9, "cfo": 9, "coo": 9, "cmo": 9, "cro": 9, "cio": 9, "cso": 9,
    "president": 9, "managing director": 8,
    "evp": 8, "executive vice": 8,
    "svp": 8, "senior vice president": 8,
    "vp": 7, "vice president": 7,
    "global head": 7, "head of": 6,
    "director": 6, "senior director": 7,
    "manager": 4, "senior manager": 5,
    "lead": 3, "senior": 3,
    "analyst": 2, "associate": 2, "coordinator": 2,
    "intern": 1, "assistant": 1, "junior": 1,
}

ROLE_PROMPT = """You are a B2B role evaluation agent.

You are given REAL people found on LinkedIn at a specific company.
Evaluate each person's decision-making power for B2B purchases.

Decision Power Scale (1-10):
- 10: CEO, Founder, Owner
- 9: C-Suite (CTO, CFO, CMO)
- 8: President, EVP
- 7: VP, SVP
- 6: Director, Head of
- 5: Senior Manager
- 4: Manager
- 3: Lead
- 2: Senior Individual
- 1: Junior, Intern

Acceptance Threshold: decision_power >= 6

Output Rules:
- Only output valid JSON
- No markdown

Required Output Format:
{
  "people": [
    {
      "name": "person's full name",
      "title": "their job title",
      "company": "company name",
      "decision_power": 7,
      "status": "accepted | rejected",
      "reason": "brief explanation"
    }
  ],
  "summary": "brief summary of findings"
}"""


def get_decision_power(title: str) -> int:
    """Calculate decision power from title."""
    if not title:
        return 1
    
    title_lower = title.lower()
    
    for pattern, power in sorted(DECISION_POWER_MAP.items(), key=lambda x: -x[1]):
        if pattern in title_lower:
            return power
    
    return 3  # Default for unknown titles


def run(company_name: str, company_size: str = "medium", structure_data: dict = None, stop_event=None) -> dict:
    """
    Run role discovery - finds ACTUAL people at the company.
    
    Args:
        company_name: Company to search
        company_size: Company size for targeting
        structure_data: Optional structure data with recommended targets
        stop_event: Optional threading.Event to check for stop signal
        
    Returns:
        Dict with actual people found and their scores
    """
    if stop_event and stop_event.is_set():
        raise KeyboardInterrupt("Stopped by user")

    people = []
    
    # Step 1: Search LinkedIn for decision-makers
    if LINKEDIN_SEARCH_ENABLED and linkedin_available():
        try:
            if stop_event and stop_event.is_set():
                raise KeyboardInterrupt("Stopped by user")
                
            linkedin_results = search_decision_makers(company_name, company_size)
            
            if linkedin_results and not linkedin_results[0].get("error"):
                for person in linkedin_results:
                    if person.get("name"):
                        power = get_decision_power(person.get("title", ""))
                        people.append({
                            "name": person.get("name"),
                            "title": person.get("title", "Unknown"),
                            "company": company_name,
                            "linkedin_url": person.get("linkedin_url", ""),
                            "decision_power": power,
                            "status": "accepted" if power >= 6 else "rejected",
                            "reason": f"Decision power: {power}/10",
                            "source": "linkedin"
                        })
        except Exception as e:
            pass  # Continue without LinkedIn data
    
    # Step 2: If no LinkedIn results, use LLM to suggest typical roles
    if not people:
        if stop_event and stop_event.is_set():
            raise KeyboardInterrupt("Stopped by user")

        api_key = os.getenv("GROQ_API_KEY")
        if api_key:
            try:
                people = suggest_typical_roles(company_name, company_size, api_key)
            except:
                pass
    
    # Step 3: Sort by decision power
    people.sort(key=lambda x: -x.get("decision_power", 0))
    
    accepted = [p for p in people if p.get("status") == "accepted"]
    rejected = [p for p in people if p.get("status") == "rejected"]
    
    return {
        "company": company_name,
        "people_found": len(people),
        "accepted_count": len(accepted),
        "rejected_count": len(rejected),
        "people": people,
        "linkedin_searched": LINKEDIN_SEARCH_ENABLED and linkedin_available(),
        "summary": f"Found {len(accepted)} decision-makers at {company_name}"
    }


def suggest_typical_roles(company_name: str, company_size: str, api_key: str) -> list:
    """Use LLM to suggest typical roles when no LinkedIn data."""
    client = Groq(api_key=api_key)
    
    prompt = f"""For a {company_size} company like {company_name}, list 5 typical decision-maker roles.
Output valid JSON only:
{{"roles": ["CEO", "CTO", "VP Sales", "Director Engineering", "Head of Product"]}}"""
    
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}]
        )
        
        result = response.choices[0].message.content
        start = result.find("{")
        end = result.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(result[start:end])
            roles = data.get("roles", [])
            
            return [
                {
                    "name": f"[Target Role]",
                    "title": role,
                    "company": company_name,
                    "decision_power": get_decision_power(role),
                    "status": "accepted" if get_decision_power(role) >= 6 else "rejected",
                    "reason": "Suggested role - needs LinkedIn/Apollo enrichment",
                    "source": "suggested"
                }
                for role in roles
            ]
    except:
        pass
    
    return []


# Backward compatibility for old workflow
def run_legacy(roles_input: list, company_structure: dict = None) -> dict:
    """Legacy run function for old-style input."""
    people = []
    for title in roles_input:
        power = get_decision_power(title)
        people.append({
            "name": "[Unknown]",
            "title": title,
            "decision_power": power,
            "status": "accepted" if power >= 6 else "rejected",
            "reason": f"Decision power: {power}/10",
            "source": "user_input"
        })
    
    return {"roles": people}
