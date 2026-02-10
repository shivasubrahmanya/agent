"""
Web Search Service
Uses Google Custom Search API (Reliable & Cloud-Compatible)
"""

import os
import requests
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv(override=True)

def is_available() -> bool:
    """Check if Search is configured (prefers SerpApi)."""
    return bool(os.getenv("SERP_API_KEY") or (os.getenv("GOOGLE_API_KEY") and os.getenv("GOOGLE_CX")))


def google_custom_search(query: str, num_results: int = 10, search_type: str = None) -> List[Dict[str, Any]]:
    """
    Execute a search using SerpApi (preferred) or Google Custom Search API.
    """
    serp_api_key = os.getenv("SERP_API_KEY")
    
    if serp_api_key:
        # Use SerpApi
        url = "https://serpapi.com/search"
        params = {
            "api_key": serp_api_key,
            "engine": "google",
            "q": query,
            "num": min(num_results, 10)
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            items = data.get("organic_results", [])
            results = []
            
            for item in items:
                results.append({
                    "title": item.get("title", ""),
                    "body": item.get("snippet", ""),
                    "href": item.get("link", ""),
                    "source": "serpapi"
                })
                
            return results
            
        except Exception as e:
            print(f"SerpApi Error: {e}")
            # Fallback to Google if configured, otherwise return error
            if not (os.getenv("GOOGLE_API_KEY") and os.getenv("GOOGLE_CX")):
                return [{"error": f"SerpApi Error: {str(e)}"}]

    # Official Google API Fallback
    api_key = os.getenv("GOOGLE_API_KEY")
    cx = os.getenv("GOOGLE_CX")
    
    if not api_key or not cx:
        return [{"error": "No search API (SerpApi or Google) configured"}]

    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": api_key,
        "cx": cx,
        "q": query,
        "num": min(num_results, 10)
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        items = data.get("items", [])
        results = []
        
        for item in items:
            results.append({
                "title": item.get("title", ""),
                "body": item.get("snippet", ""),
                "href": item.get("link", ""),
                "source": "google"
            })
            
        return results
        
    except Exception as e:
        return [{"error": f"Google API Error: {str(e)}"}]


def search_company(company_name: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """Search for company information."""
    return google_custom_search(f"{company_name} company", num_results=max_results)


def search_company_news(company_name: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """Search for recent news about a company."""
    # Google Custom Search doesn't have a strict 'news' mode in the basic API 
    # without advanced context config, but adding 'news' to query works reasonably well.
    return google_custom_search(f"{company_name} news", num_results=max_results)


def search_company_linkedin(company_name: str) -> Optional[Dict[str, Any]]:
    """Search for company's LinkedIn page."""
    results = google_custom_search(f"{company_name} site:linkedin.com/company", num_results=1)
    if results and not results[0].get("error"):
        return results[0]
    return None


def get_company_info(company_name: str, stop_event=None) -> Dict[str, Any]:
    """Gather comprehensive company information."""
    
    if not is_available():
        return {
            "error": "Google Search not configured",
            "install": "Update .env with GOOGLE_API_KEY and GOOGLE_CX"
        }
    
    info = {
        "company_name": company_name,
        "sources": []
    }
    
    if stop_event and stop_event.is_set():
        raise KeyboardInterrupt("Stopped by user")
    
    # General
    general = search_company(company_name)
    if general and not general[0].get("error"):
        info["web_results"] = general
        info["sources"].append("google_web")
        
    if stop_event and stop_event.is_set():
        raise KeyboardInterrupt("Stopped by user")
        
    # News
    news = search_company_news(company_name)
    if news and not news[0].get("error"):
        info["news"] = news
        info["sources"].append("google_news")
        
    # LinkedIn
    linkedin = search_company_linkedin(company_name)
    if linkedin and not linkedin.get("error"):
        info["linkedin"] = linkedin
        info["sources"].append("google_linkedin")
        
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
