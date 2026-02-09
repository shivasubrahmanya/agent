"""
Discovery Agent - Stage 1
Validates company for B2B suitability using REAL WEB SEARCH
Searches: Google/DuckDuckGo, News articles, LinkedIn company pages
"""

import os
import sys
import json

# Add parent dir to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from groq import Groq
from dotenv import load_dotenv

# Import web search service
try:
    from services.web_search import get_company_info, extract_company_data, is_available as web_search_available
    WEB_SEARCH_ENABLED = True
except ImportError:
    WEB_SEARCH_ENABLED = False
    web_search_available = lambda: False

load_dotenv()

DISCOVERY_PROMPT = """You are a B2B company validation agent.

You are given REAL search results from the web including:
- Web search results (company websites, articles)
- Recent news about the company
- LinkedIn company page information

Analyze this REAL DATA and determine if the company is suitable for B2B sales targeting.

Evaluation Criteria:
1. Is this a real, established company? (Use the search results as evidence)
2. What industry is it in? (Extract from search results)
3. What is the company size? (Look for employee counts, revenue, office locations)
4. Is there evidence of growth? (Recent news, hiring, funding)
5. Is it B2B relevant? (Tech, SaaS, Finance, Consulting, Manufacturing, etc.)

Output Rules:
- Only output valid JSON
- No markdown, no explanations outside JSON
- Base your analysis on the ACTUAL search results provided

Required Output Format:
{
  "name": "official company name from search",
  "industry": "industry from search results",
  "size": "small / medium / large / enterprise",
  "location": "headquarters location if found",
  "website": "company website URL",
  "growth_signals": ["list of growth indicators found"],
  "status": "accepted | rejected",
  "reason": "explanation citing the search evidence"
}

Be strict but fair - use the real data to make your decision."""

DISCOVERY_PROMPT_NO_SEARCH = """You are a B2B company validation agent.

Analyze the company provided and determine if it's suitable for B2B sales targeting.

Evaluation Criteria:
1. Is this a real, recognizable company?
2. Is it in a B2B-relevant industry (Tech, SaaS, Finance, Consulting, Manufacturing, etc.)?
3. Is it large enough to have multiple decision-makers?

Output Rules:
- Only output valid JSON
- No markdown, no explanations outside JSON

Required Output Format:
{
  "name": "corrected company name",
  "industry": "identified industry",
  "size": "small / medium / large / enterprise",
  "website": "company domain if known",
  "status": "accepted | rejected",
  "reason": "brief explanation"
}

Be strict: reject unclear or consumer-focused companies."""


def run(company_input: str, use_web_search: bool = True, stop_event=None) -> dict:
    """
    Run company discovery validation with optional web search.
    
    Args:
        company_input: Company name or description
        use_web_search: Whether to search the web for real data
        stop_event: Optional threading.Event to check for stop signal
        
    Returns:
        Dict with company validation results
    """
    if stop_event and stop_event.is_set():
        raise KeyboardInterrupt("Stopped by user")

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return {
            "name": company_input,
            "status": "rejected",
            "reason": "GROQ_API_KEY not configured"
        }
    
    client = Groq(api_key=api_key)
    
    # Determine if we can use web search
    web_search_data = None
    if use_web_search and WEB_SEARCH_ENABLED and web_search_available():
        try:
            # Perform real web search
            web_search_data = get_company_info(company_input, stop_event=stop_event)
            search_text = extract_company_data(web_search_data)
            prompt = DISCOVERY_PROMPT
            user_content = f"Analyze this company based on the following REAL search results:\n\n{search_text}"
        except Exception as e:
            # Fall back to no search
            web_search_data = None
            prompt = DISCOVERY_PROMPT_NO_SEARCH
            user_content = f"Company: {company_input}"
    else:
        prompt = DISCOVERY_PROMPT_NO_SEARCH
        user_content = f"Company: {company_input}"
    
    if stop_event and stop_event.is_set():
        raise KeyboardInterrupt("Stopped by user")

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=1024,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_content}
            ]
        )
        
        result = response.choices[0].message.content
        
        # Parse JSON response
        try:
            parsed = json.loads(result)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            start = result.find("{")
            end = result.rfind("}") + 1
            if start >= 0 and end > start:
                parsed = json.loads(result[start:end])
            else:
                parsed = {
                    "name": company_input,
                    "status": "rejected",
                    "reason": "Failed to parse response"
                }
        
        # Add metadata about search sources used
        if web_search_data:
            parsed["_sources"] = web_search_data.get("sources", [])
            parsed["_web_search_used"] = True
        else:
            parsed["_web_search_used"] = False
        
        return parsed
            
    except Exception as e:
        return {
            "name": company_input,
            "status": "rejected",
            "reason": f"Error: {str(e)}"
        }
