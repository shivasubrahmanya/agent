"""
Enrichment Agent - Stage 4
Uses Apollo.io and Snov.io to fetch real contact data
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.apollo_client import enrich_person, search_people, is_configured as apollo_configured
from services.snov_client import domain_search as snov_domain_search, find_email as snov_find_email, is_configured as snov_configured


def extract_domain(company_name: str) -> str:
    """Extract likely domain from company name."""
    # Common company suffixes to remove
    suffixes = [
        " corporation", " corp", " incorporated", " inc",
        " limited", " ltd", " llc", " llp", " plc",
        " company", " co", " group", " holdings",
        " technologies", " technology", " tech",
        " solutions", " services", " systems",
        " international", " intl", " global",
    ]
    
    clean = company_name.lower().strip()
    
    # Remove common suffixes
    for suffix in suffixes:
        if clean.endswith(suffix):
            clean = clean[:-len(suffix)]
        clean = clean.replace(suffix + ",", "")
        clean = clean.replace(suffix + ".", "")
    
    # Remove remaining special characters
    clean = clean.replace(" ", "").replace(",", "").replace(".", "")
    clean = clean.replace("'", "").replace("-", "")
    
    return f"{clean}.com"


def deduplicate_contacts(contacts: list) -> list:
    """Remove duplicate contacts by email."""
    seen_emails = set()
    unique = []
    for contact in contacts:
        email = contact.get("email", "").lower()
        if email and email not in seen_emails:
            seen_emails.add(email)
            unique.append(contact)
        elif not email:
            # Keep contacts without email (might have other useful info)
            unique.append(contact)
    return unique


def run(company_name: str, roles: list, company_domain: str = None) -> dict:
    """
    Run contact enrichment using Apollo.io and Snov.io.
    
    Args:
        company_name: Company to search
        roles: List of role dicts from role_agent
        company_domain: Optional company domain for Snov.io
        
    Returns:
        Dict with enriched contacts from both sources
    """
    contacts = []
    sources_used = []
    errors = []
    
    accepted_roles = [r for r in roles if r.get("status") == "accepted"]
    
    if not accepted_roles:
        return {
            "contacts": [],
            "note": "No accepted roles to enrich"
        }
    
    titles = [r.get("title", "") for r in accepted_roles]
    
    # === Source 1: Apollo.io ===
    if apollo_configured():
        try:
            results = search_people(
                company_name=company_name,
                titles=titles,
                limit=10
            )
            
            if results and not results[0].get("error"):
                for person in results:
                    if person.get("first_name"):
                        contacts.append({
                            "first_name": person.get("first_name", ""),
                            "last_name": person.get("last_name", ""),
                            "email": person.get("email", ""),
                            "phone": person.get("phone", ""),
                            "linkedin_url": person.get("linkedin_url", ""),
                            "title": person.get("title", ""),
                            "company": company_name,
                            "source": "apollo",
                            "enriched": True
                        })
                sources_used.append("apollo")
        except Exception as e:
            errors.append(f"Apollo error: {str(e)}")
    else:
        errors.append("Apollo API not configured")
    
    # === Source 2: Snov.io (Email Finder) ===
    # Use Snov.io to find emails for people who don't have emails yet
    # Also try to find emails for role titles from Role Agent
    if snov_configured():
        domain = company_domain or extract_domain(company_name)
        
        # Try to find emails for contacts without emails
        contacts_needing_email = [c for c in contacts if not c.get("email")]
        for contact in contacts_needing_email:
            first_name = contact.get("first_name", "")
            last_name = contact.get("last_name", "")
            if first_name and last_name:
                try:
                    result = snov_find_email(domain, first_name, last_name)
                    if result.get("email") and not result.get("error"):
                        contact["email"] = result["email"]
                        contact["source"] = f"{contact.get('source', 'unknown')}+snov"
                except Exception:
                    pass
        
        # Also try for people in accepted roles who have names but no email in contacts
        for role in accepted_roles:
            name = role.get("name", "")
            if name and name != "[Target Role]" and name != "[Unknown]":
                # Split name into first/last
                parts = name.split()
                if len(parts) >= 2:
                    first_name = parts[0]
                    last_name = " ".join(parts[1:])
                    
                    # Check if we already have this person's email
                    existing = [c for c in contacts if 
                               c.get("first_name", "").lower() == first_name.lower() and
                               c.get("last_name", "").lower() == last_name.lower() and
                               c.get("email")]
                    
                    if not existing:
                        try:
                            result = snov_find_email(domain, first_name, last_name)
                            if result.get("email") and not result.get("error"):
                                contacts.append({
                                    "first_name": first_name,
                                    "last_name": last_name,
                                    "email": result["email"],
                                    "phone": "",
                                    "linkedin_url": role.get("linkedin_url", ""),
                                    "title": role.get("title", ""),
                                    "company": company_name,
                                    "source": "snov",
                                    "enriched": True
                                })
                                if "snov" not in sources_used:
                                    sources_used.append("snov")
                        except Exception as e:
                            errors.append(f"Snov.io error for {name}: {str(e)}")
    else:
        errors.append("Snov.io API not configured")
    
    # Deduplicate contacts from both sources
    contacts = deduplicate_contacts(contacts)
    
    # Build response
    if not contacts:
        return {
            "contacts": [],
            "sources_checked": sources_used if sources_used else ["none"],
            "errors": errors if errors else None,
            "note": "No matching contacts found",
            "suggestion": "Try adding API keys or use more specific role titles"
        }
    
    return {
        "contacts": contacts,
        "sources_used": sources_used,
        "total_found": len(contacts),
        "errors": errors if errors else None
    }


def enrich_single(first_name: str, last_name: str, company_name: str, company_domain: str = None) -> dict:
    """
    Enrich a single person's contact info using both Apollo and Snov.io.
    
    Args:
        first_name: Person's first name
        last_name: Person's last name
        company_name: Company they work at
        company_domain: Optional company domain
        
    Returns:
        Enriched contact data
    """
    result = None
    
    # Try Apollo first
    if apollo_configured():
        result = enrich_person(
            first_name=first_name,
            last_name=last_name,
            company_name=company_name
        )
        if result and result.get("email"):
            result["source"] = "apollo"
            return result
    
    # Fallback to Snov.io
    if snov_configured():
        domain = company_domain or extract_domain(company_name)
        result = snov_find_email(domain, first_name, last_name)
        if result and result.get("email"):
            result["source"] = "snov"
            result["company"] = company_name
            return result
    
    # No results from either source
    return {
        "error": "Person not found in Apollo or Snov.io",
        "first_name": first_name,
        "last_name": last_name,
        "company": company_name,
        "apis_configured": {
            "apollo": apollo_configured(),
            "snov": snov_configured()
        }
    }
