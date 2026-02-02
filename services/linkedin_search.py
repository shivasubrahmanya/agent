"""
LinkedIn Search Service
Searches LinkedIn for people at companies using DuckDuckGo (no API required)
Only collects: name, job title, company - NO personal info
"""

try:
    from ddgs import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False

from typing import List, Dict, Any, Optional
import re


def is_available() -> bool:
    """Check if LinkedIn search is available."""
    return DDGS_AVAILABLE


def search_people_at_company(
    company_name: str,
    role_titles: List[str] = None,
    max_results: int = 10
) -> List[Dict[str, Any]]:
    """
    Search LinkedIn for people at a specific company.
    
    Args:
        company_name: Company name to search
        role_titles: Optional list of role titles to filter
        max_results: Maximum results to return
        
    Returns:
        List of people found with name, title, company
    """
    if not DDGS_AVAILABLE:
        return [{"error": "Install duckduckgo-search: pip install duckduckgo-search"}]
    
    people = []
    
    try:
        with DDGS() as ddgs:
            # Search for people at the company on LinkedIn
            if role_titles:
                for title in role_titles[:3]:  # Limit to top 3 titles
                    query = f'site:linkedin.com/in "{company_name}" "{title}"'
                    results = list(ddgs.text(query, max_results=3))
                    
                    for r in results:
                        person = parse_linkedin_result(r, company_name)
                        if person and person.get("name"):
                            person["searched_title"] = title
                            people.append(person)
            else:
                # General search for people at company
                query = f'site:linkedin.com/in "{company_name}"'
                results = list(ddgs.text(query, max_results=max_results))
                
                for r in results:
                    person = parse_linkedin_result(r, company_name)
                    if person and person.get("name"):
                        people.append(person)
        
        # Remove duplicates by name
        seen = set()
        unique_people = []
        for p in people:
            name = p.get("name", "").lower()
            if name and name not in seen:
                seen.add(name)
                unique_people.append(p)
        
        return unique_people
        
    except Exception as e:
        return [{"error": str(e)}]


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
