"""
Lead Finder Agent
Parses natural language queries to find lists of companies using Web Search + LLM.
"""

import os
import sys
import json
import time

# Add parent dir to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from groq import Groq
from dotenv import load_dotenv


load_dotenv(override=True)

SEARCH_QUERY_PROMPT = """You are a Search Query Generator.
Your goal is to convert a user's natural language request into effective search queries to find lists of companies.

User Input: "{user_input}"

Rules:
1. Generate 5 distinct search queries to find these companies.
2. Focus on lists, directories, and "top X" articles.
3. Example: "find series b ai startups" -> ["top series b ai startups 2024", "list of series b artificial intelligence companies", "fast growing series b ai startups", "recently funded ai companies", "best ai startups to watch"]

Output ONLY a JSON array of strings:
["query 1", "query 2", "query 3", "query 4", "query 5"]"""

COMPANY_EXTRACTION_PROMPT = """You are a Company Extraction Specialist.
Your goal is to extract a list of relevant companies from search results.

User Request: "{user_input}"

Search Results:
{search_results}

Rules:
1. Identify ALL companies that match the user's request.
2. Extract the Company Name and a brief Context (why it fits).
3. Ignore job boards, generic articles, or irrelevant companies.
4. Extract as many relevant companies as possible (aim for 20-50).

Output ONLY a JSON array of objects:
[
  {{"name": "Company A", "context": "Series B AI startup in healthcare..."}},
  {{"name": "Company B", "context": "..."}}
]"""

from services.web_search import google_custom_search

def perform_web_search(query: str, max_results=10) -> str:
    """Perform a web search using Google Custom Search and return text summary."""
    try:
        results = google_custom_search(query, num_results=max_results)
        
        if not results:
             return "No results found."
        
        # Check for errors
        if results and results[0].get("error"):
            # If Google API fails (e.g. no key), we might want to return that error clearly
            return f"Search Error: {results[0]['error']}"

        summary_lines = []
        for r in results:
            summary_lines.append(f"Title: {r.get('title')}\nSnippet: {r.get('body')}\nLink: {r.get('href')}")
        
        return "\n\n".join(summary_lines)
    except Exception as e:
        return f"Error: {str(e)}"

def clean_json_response(text: str) -> str:
    """Extract JSON from potential markdown fences."""
    if "```json" in text:
        return text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        return text.split("```")[1].split("```")[0].strip()
    return text.strip()

def run(user_input: str, stop_event=None) -> dict:
    """
    Find companies based on natural language input.
    
    Returns:
        {
            "is_search": bool, # True if this was a search query, False if it looks like a direct company name
            "companies": [{"name": "...", "context": "..."}, ...],
            "message": "Found X companies..."
        }
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return {"error": "GROQ_API_KEY not configured"}
    
    client = Groq(api_key=api_key)
    
    if stop_event and stop_event.is_set():
        return {"companies": [], "message": "Stopped"}

    # 1. Heuristic Check: Is this a search query or a direct analysis request?
    is_search_heuristic = False
    
    # Strict triggers to differentiate search queries from company names
    triggers = ["find ", "search ", "list of", "who are", "companies in", "startups in", "firms in", "list ", "near "]
    
    word_count = len(user_input.split())
    has_trigger = any(t in user_input.lower() for t in triggers)
    
    if has_trigger or word_count >= 3:
        is_search_heuristic = True
        
    print(f"DEBUG LeadFinder: input='{user_input}', words={word_count}, is_search={is_search_heuristic}")

    if not is_search_heuristic:
        return {
            "is_search": False,
            "companies": [],
            "message": "Treating as direct company analysis"
        }

    # 2. Generate Search Queries
    try:
        search_prompt = SEARCH_QUERY_PROMPT.format(user_input=user_input)
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": search_prompt}],
            max_tokens=150
        )
        content = clean_json_response(response.choices[0].message.content)
        all_queries = json.loads(content)
        queries = all_queries[:3] # Limit to 3 for stability
    except Exception as e:
        # Fallback
        queries = [user_input]
        print(f"Error generating queries: {e}")

    # 3. Execute Searches
    search_context = ""
    for q in queries: # Execute top 3 queries
        if stop_event and stop_event.is_set(): break
        try:
            results = perform_web_search(q)
            search_context += f"Query: {q}\n{results}\n\n"
            time.sleep(1.5) # More polite delay to avoid rate limits
        except Exception:
            pass
            
    if not search_context or "Search Error:" in search_context:
        # FALLBACK: Try Apollo Company Search if web search failed
        error_info = search_context if "Search Error:" in search_context else "No results found"
        print(f"Web search failed ({error_info}). Trying Apollo fallback...")
        try:
            from services import apollo_client
            if apollo_client.is_configured():
                apollo_results = apollo_client.search_companies(user_input, limit=10)
                
                if apollo_results and not apollo_results[0].get("error"):
                    companies = []
                    for org in apollo_results:
                        if org.get("name"):
                            desc = org.get("short_description", "")
                            loc = f"{org.get('city', '')}, {org.get('country', '')}".strip(", ")
                            context = f"{desc} | Location: {loc}"
                            companies.append({"name": org.get("name"), "context": context})
                    
                    if companies:
                        return {
                            "is_search": True,
                            "companies": companies,
                            "message": f"Found {len(companies)} companies via Apollo (Web Search fallback)."
                        }
        except Exception as e:
            print(f"Apollo fallback error: {e}")

        msg = "No search results found to extract companies from."
        if "rate_limit_exceeded" in search_context.lower():
            msg = "Rate limit reached for Search. Please try again in 1 minute."
            
        return {
            "is_search": True,
            "companies": [],
            "message": msg
        }

    # 4. Extract Companies
    if stop_event and stop_event.is_set():
        return {"companies": [], "message": "Stopped"}
        
    try:
        extract_prompt = COMPANY_EXTRACTION_PROMPT.format(user_input=user_input, search_results=search_context)
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": extract_prompt}],
            max_tokens=4096
        )
        companies_json = clean_json_response(response.choices[0].message.content)
        companies = json.loads(companies_json)
        
        return {
            "is_search": True,
            "companies": companies,
            "message": f"Found {len(companies)} potential companies."
        }

    except Exception as e:
        print(f"Error extracting companies: {e}")
        return {
            "is_search": True,
            "companies": [],
            "message": f"Failed to extract companies: {str(e)}"
        }

if __name__ == "__main__":
    # Test run
    print(run("find series b ai startups in san francisco"))
