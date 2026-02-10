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

# Import Apollo client for fallback
try:
    from services import apollo_client
    APOLLO_ENABLED = True
except ImportError:
    APOLLO_ENABLED = False

# Date: ... (keeping existing imports) ...

# ... (Decision Power Map remains same) ...

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
            pass  # Continue to fallback
            
    # Step 1.5: Fallback to Apollo if LinkedIn failed or returned nothing
    if not people and APOLLO_ENABLED and apollo_client.is_configured():
        try:
            if stop_event and stop_event.is_set():
                raise KeyboardInterrupt("Stopped by user")
            
            # Search Apollo
            apollo_results = apollo_client.get_top_people(company_name, limit=10)
            
            if apollo_results and not apollo_results[0].get("error"):
                for person in apollo_results:
                    full_name = f"{person.get('first_name', '')} {person.get('last_name', '')}".strip()
                    if full_name:
                        power = get_decision_power(person.get("title", ""))
                        people.append({
                            "name": full_name,
                            "title": person.get("title", "Unknown"),
                            "company": company_name,
                            "linkedin_url": person.get("linkedin_url", ""),
                            "decision_power": power,
                            "status": "accepted" if power >= 6 else "rejected",
                            "reason": f"Decision power: {power}/10",
                            "source": "apollo_fallback"
                        })
        except Exception:
            pass

    # Step 2: If no results from ANY source, use LLM to suggest typical roles
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
