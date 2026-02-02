"""
Enrichment Agent - Stage 4
Uses Apollo.io to fetch real contact data
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.apollo_client import enrich_person, search_people, is_configured


def run(company_name: str, roles: list) -> dict:
    """
    Run contact enrichment using Apollo.io.
    
    Args:
        company_name: Company to search
        roles: List of role dicts from role_agent
        
    Returns:
        Dict with enriched contacts
    """
    if not is_configured():
        return {
            "contacts": [],
            "error": "Apollo API not configured. Add APOLLO_API_KEY to .env",
            "note": "Get free key at: https://www.apollo.io"
        }
    
    contacts = []
    accepted_roles = [r for r in roles if r.get("status") == "accepted"]
    
    if not accepted_roles:
        return {
            "contacts": [],
            "note": "No accepted roles to enrich"
        }
    
    # Try to search for people with these titles at the company
    titles = [r.get("title", "") for r in accepted_roles]
    
    try:
        # Search for people at company with matching titles
        results = search_people(
            company_name=company_name,
            titles=titles,
            limit=10
        )
        
        if results and not results[0].get("error"):
            for person in results:
                if person.get("first_name"):  # Valid result
                    contacts.append({
                        "first_name": person.get("first_name", ""),
                        "last_name": person.get("last_name", ""),
                        "email": person.get("email", ""),
                        "phone": person.get("phone", ""),
                        "linkedin_url": person.get("linkedin_url", ""),
                        "title": person.get("title", ""),
                        "company": company_name,
                        "enriched": True
                    })
        
        # If no results from search, indicate this
        if not contacts:
            return {
                "contacts": [],
                "note": "No matching contacts found in Apollo database",
                "suggestion": "Try with more specific role titles or manual enrichment"
            }
        
        return {"contacts": contacts}
        
    except Exception as e:
        return {
            "contacts": [],
            "error": str(e)
        }


def enrich_single(first_name: str, last_name: str, company_name: str) -> dict:
    """
    Enrich a single person's contact info.
    
    Args:
        first_name: Person's first name
        last_name: Person's last name
        company_name: Company they work at
        
    Returns:
        Enriched contact data
    """
    if not is_configured():
        return {
            "error": "Apollo API not configured",
            "note": "Get free key at: https://www.apollo.io"
        }
    
    result = enrich_person(
        first_name=first_name,
        last_name=last_name,
        company_name=company_name
    )
    
    if result:
        return result
    
    return {
        "error": "Person not found in Apollo database",
        "first_name": first_name,
        "last_name": last_name,
        "company": company_name
    }
