"""
LinkedIn Search Service
Searches LinkedIn for people at companies using Google Custom Search API.
"""

from typing import List, Dict, Any, Optional
import re
from services.web_search import google_custom_search, is_available as is_google_available

def is_available() -> bool:
    """Check if Google Search is available."""
    return is_google_available()

def search_people_at_company(
    company_name: str,
    role_titles: List[str] = None,
    max_results: int = 10
) -> List[Dict[str, Any]]:
    """
    Search LinkedIn for people at a specific company using Google Search.
    """
    if not is_available():
        return [{"error": "Google Search not configured. Add GOOGLE_API_KEY and GOOGLE_CX to .env"}]
    
    people = []
    
    # Execute Search
    # We can try to be specific with roles if provided, otherwise general search
    
    queries = []
    if role_titles:
        for title in role_titles[:3]: # limit to top 3 roles to save API calls
            queries.append({
                "q": f'site:linkedin.com/in "{company_name}" "{title}"',
                "role_context": title
            })
    else:
         queries.append({
            "q": f'site:linkedin.com/in "{company_name}"',
            "role_context": None
         })
         
    for query_obj in queries:
        results = google_custom_search(query_obj["q"], num_results=5) # 5 per query
        
        for r in results:
            if r.get("error"): continue
            
            person = parse_linkedin_result(r, company_name)
            if person and person.get("name"):
                 if query_obj["role_context"]:
                     person["searched_title"] = query_obj["role_context"]
                 person["source"] = "google_search"
                 people.append(person)
                 
    return _deduplicate(people)

def _deduplicate(people):
    seen = set()
    unique_people = []
    for p in people:
        name = p.get("name", "").lower()
        if name and name not in seen:
            seen.add(name)
            unique_people.append(p)
    return unique_people


def parse_linkedin_result(result: Dict[str, Any], company_name: str) -> Optional[Dict[str, Any]]:
    """
    Parse a LinkedIn search result to extract person info.
    
    Args:
        result: DuckDuckGo search result
        company_name: Company being searched
        
    Returns:
        Dict with name, title, company or None
    """
    title_text = result.get("title", "")
    body_text = result.get("body", "")
    url = result.get("href", "")
    
    # Skip if not a personal profile
    if "/in/" not in url:
        return None
    
    # Try to extract name from title (usually "Name - Title - Company | LinkedIn")
    name = ""
    job_title = ""
    
    # Pattern: "Name - Title - Company | LinkedIn" or "Name | LinkedIn"
    if " - " in title_text:
        parts = title_text.split(" - ")
        name = parts[0].strip()
        if len(parts) > 1:
            job_title = parts[1].strip()
    elif " | " in title_text:
        name = title_text.split(" | ")[0].strip()
    
    # Clean up name (remove emojis, extra characters)
    name = re.sub(r'[^\w\s\.\-]', '', name).strip()
    
    # Skip if name looks invalid
    if not name or len(name) < 2 or name.lower() == "linkedin":
        return None
    
    # Try to extract title from body if not found
    if not job_title and body_text:
        # Look for common title patterns
        title_patterns = [
            r"(CEO|CTO|CFO|COO|CMO|VP|Director|Manager|Head of|Chief|President|Founder)",
        ]
        for pattern in title_patterns:
            match = re.search(pattern, body_text, re.IGNORECASE)
            if match:
                job_title = match.group(0)
                break
    
    return {
        "name": name,
        "title": job_title,
        "company": company_name,
        "linkedin_url": url,
        "source": "linkedin_search"
    }


def search_decision_makers(
    company_name: str,
    company_size: str = "medium"
) -> List[Dict[str, Any]]:
    """
    Search for decision-makers at a company based on size.
    
    Args:
        company_name: Company to search
        company_size: small/medium/large/enterprise
        
    Returns:
        List of decision-makers found
    """
    # Define decision-maker titles by company size
    titles_by_size = {
        "small": ["Founder", "CEO", "CTO", "Owner", "Managing Director"],
        "medium": ["CEO", "CTO", "VP", "Director", "Head of"],
        "large": ["VP", "SVP", "Director", "Senior Director", "Head of"],
        "enterprise": ["SVP", "EVP", "VP", "Senior Director", "Global Head"]
    }
    
    titles = titles_by_size.get(company_size, titles_by_size["medium"])
    
    return search_people_at_company(company_name, role_titles=titles, max_results=10)


def format_people_for_display(people: List[Dict[str, Any]]) -> str:
    """Format people list for display or LLM input."""
    if not people:
        return "No people found on LinkedIn"
    
    lines = [f"Found {len(people)} people on LinkedIn:"]
    for p in people:
        lines.append(f"  - {p.get('name', 'Unknown')}")
        lines.append(f"    Title: {p.get('title', 'Unknown')}")
        lines.append(f"    Company: {p.get('company', 'Unknown')}")
        if p.get('linkedin_url'):
            lines.append(f"    LinkedIn: {p.get('linkedin_url')}")
    
    return "\n".join(lines)
