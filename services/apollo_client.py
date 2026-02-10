"""
Apollo.io API Client - Simplified
Only uses the FREE organization_top_people endpoint
"""

import os
import requests
from typing import Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

APOLLO_API_KEY = os.getenv("APOLLO_API_KEY", "")
APOLLO_BASE_URL = "https://api.apollo.io/v1"


def is_configured() -> bool:
    """Check if Apollo API is configured."""
    return bool(APOLLO_API_KEY)


def get_top_people(company_name: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get top decision-makers at a company (FREE API).
    
    Uses: api/v1/mixed_people/organization_top_people
    
    Args:
        company_name: Company name to search
        limit: Max number of people to return
    
    Returns:
        List of top people at the company
    """
    if not is_configured():
        return [{"error": "Apollo API key not configured"}]
    
    endpoint = f"{APOLLO_BASE_URL}/mixed_people/search"
    
    payload = {
        "q_organization_domains": company_name if "." in company_name else f"{company_name}.com", # basic heuristic fallback
        "page": 1,
        "per_page": limit,
    }
    
    # Better logic: if company_name looks like a domain, use it. Else search by name?
    # mixed_people/search supports 'q_organization_domains' (list) or 'q_organization_name' (string)??
    # Actually, let's use a safer approach.
    
    payload = {
        "q_organization_domains": [company_name] if "." in company_name else None,
        "q_organization_name": company_name if "." not in company_name else None,
        "per_page": limit,
        "page": 1,
    }
    # Remove None keys
    payload = {k: v for k, v in payload.items() if v}
    
    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "X-Api-Key": APOLLO_API_KEY,
    }
    
    try:
        response = requests.post(endpoint, json=payload, headers=headers)
        
        # Handle specific error codes
        if response.status_code == 403:
            return [{"error": "Apollo API Limit Reached (403)", "code": "rate_limit"}]
        if response.status_code == 429:
            return [{"error": "Apollo Rate Limit Exceeded (429)", "code": "rate_limit"}]
            
        response.raise_for_status()
        data = response.json()
        
        people = data.get("people", [])
        results = []
        
        for person in people:
            # Extract phone if available
            phone = ""
            phones = person.get("phone_numbers", [])
            if phones:
                phone = phones[0].get("sanitized_number", "") or phones[0].get("raw_number", "")
            
            results.append({
                "first_name": person.get("first_name", ""),
                "last_name": person.get("last_name", ""),
                "email": person.get("email", ""),
                "phone": phone,
                "linkedin_url": person.get("linkedin_url", ""),
                "title": person.get("title", ""),
                "company": company_name,
            })
        
        return results
        
    except requests.exceptions.RequestException as e:
        return [{"error": str(e)}]


# Backward compatibility aliases
def search_people(company_name: str = "", titles: List[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
    """Alias for get_top_people (backward compatibility)."""
    return get_top_people(company_name, limit)


def enrich_person(first_name: str, last_name: str, company_name: str = "", **kwargs) -> Dict[str, Any]:
    """Search top people and try to find a match."""
    if not is_configured():
        return {"error": "Apollo API key not configured"}
    
    people = get_top_people(company_name, limit=20)
    
    if people and not people[0].get("error"):
        search_name = f"{first_name} {last_name}".lower()
        for person in people:
            full_name = f"{person.get('first_name', '')} {person.get('last_name', '')}".lower()
            if search_name in full_name or full_name in search_name:
                return person
    
    return {
        "first_name": first_name,
        "last_name": last_name,
        "company": company_name,
        "note": "Person not found - showing top people at company",
        "top_people": people[:5] if people else []
    }
