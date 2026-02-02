"""
Web Search Service
Uses DuckDuckGo for free web search (no API key required)
"""

try:
    from ddgs import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False

from typing import List, Dict, Any, Optional
import json


def is_available() -> bool:
    """Check if DuckDuckGo search is available."""
    return DDGS_AVAILABLE


def search_company(company_name: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Search for company information on the web.
    
    Args:
        company_name: Company to search for
        max_results: Maximum results to return
        
    Returns:
        List of search results with title, body, href
    """
    if not DDGS_AVAILABLE:
        return [{"error": "Install duckduckgo-search: pip install duckduckgo-search"}]
    
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(
                f"{company_name} company",
                max_results=max_results
            ))
        return results
    except Exception as e:
        return [{"error": str(e)}]


def search_company_news(company_name: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Search for recent news about a company.
    
    Args:
        company_name: Company to search for
        max_results: Maximum results to return
        
    Returns:
        List of news results
    """
    if not DDGS_AVAILABLE:
        return [{"error": "Install duckduckgo-search: pip install duckduckgo-search"}]
    
    try:
        with DDGS() as ddgs:
            results = list(ddgs.news(
                f"{company_name}",
                max_results=max_results
            ))
        return results
    except Exception as e:
        return [{"error": str(e)}]


def search_company_linkedin(company_name: str) -> Optional[Dict[str, Any]]:
    """
    Search for company's LinkedIn page.
    
    Args:
        company_name: Company to search for
        
    Returns:
        LinkedIn search result or None
    """
    if not DDGS_AVAILABLE:
        return {"error": "Install duckduckgo-search: pip install duckduckgo-search"}
    
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(
                f"{company_name} site:linkedin.com/company",
                max_results=1
            ))
        if results:
            return results[0]
        return None
    except Exception as e:
        return {"error": str(e)}


def get_company_info(company_name: str) -> Dict[str, Any]:
    """
    Gather comprehensive company information from web search.
    
    Args:
        company_name: Company to research
        
    Returns:
        Dict with company info from various sources
    """
    if not DDGS_AVAILABLE:
        return {
            "error": "Web search not available",
            "install": "pip install duckduckgo-search"
        }
    
    info = {
        "company_name": company_name,
        "sources": []
    }
    
    # Get general search results
    general_results = search_company(company_name, max_results=3)
    if general_results and not general_results[0].get("error"):
        info["web_results"] = general_results
        info["sources"].append("web_search")
    
    # Get news
    news_results = search_company_news(company_name, max_results=3)
    if news_results and not news_results[0].get("error"):
        info["news"] = news_results
        info["sources"].append("news")
    
    # Get LinkedIn
    linkedin = search_company_linkedin(company_name)
    if linkedin and not linkedin.get("error"):
        info["linkedin"] = linkedin
        info["sources"].append("linkedin")
    
    return info


def extract_company_data(search_results: Dict[str, Any]) -> str:
    """
    Convert search results to a text summary for LLM analysis.
    
    Args:
        search_results: Results from get_company_info
        
    Returns:
        Text summary of findings
    """
    lines = [f"Company: {search_results.get('company_name', 'Unknown')}"]
    lines.append(f"Sources checked: {', '.join(search_results.get('sources', []))}")
    lines.append("")
    
    # Web results
    if search_results.get("web_results"):
        lines.append("Web Search Results:")
        for r in search_results["web_results"]:
            lines.append(f"  - {r.get('title', '')}")
            lines.append(f"    {r.get('body', '')[:200]}")
            lines.append(f"    URL: {r.get('href', '')}")
        lines.append("")
    
    # News
    if search_results.get("news"):
        lines.append("Recent News:")
        for n in search_results["news"]:
            lines.append(f"  - {n.get('title', '')}")
            lines.append(f"    {n.get('body', '')[:150]}")
        lines.append("")
    
    # LinkedIn
    if search_results.get("linkedin"):
        lines.append("LinkedIn:")
        lines.append(f"  {search_results['linkedin'].get('title', '')}")
        lines.append(f"  {search_results['linkedin'].get('href', '')}")
    
    return "\n".join(lines)
