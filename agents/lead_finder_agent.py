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
from ddgs import DDGS

load_dotenv()

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

def perform_web_search(query: str, max_results=20) -> str:
    """Perform a DuckDuckGo search and return text summary."""
    try:
        results = []
        with DDGS() as ddgs:
            # Use 'text' for standard search
            search_gen = ddgs.text(query, max_results=max_results)
            for r in search_gen:
                results.append(f"Title: {r['title']}\nSnippet: {r['body']}\nLink: {r['href']}")
        
        return "\n\n".join(results)
    except Exception as e:
        print(f"Search error for '{query}': {e}")
        return ""

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
    
    # 1. Heuristic Check: Is this a search query or a direct analysis request?
    # If it's short and looks like a name (e.g. "Microsoft", "OpenAI"), treat as direct.
    # If it has "find", "list", "who are", "startups in", it's a search.
    is_likely_search = False
    triggers = ["find", "search", "list", "who are", "companies", "startups", "firms", "agencies"]
    if any(t in user_input.lower() for t in triggers) or len(user_input.split()) > 4:
        is_likely_search = True
        
    if not is_likely_search:
        # Return empty companies list, signifying "not a search, treat as direct input"
        return {
            "is_search": False,
            "companies": [],
            "message": "Treating as direct company analysis"
        }

    if stop_event and stop_event.is_set():
        return {"companies": [], "message": "Stopped"}

    # 2. Generate Search Queries
    try:
        search_prompt = SEARCH_QUERY_PROMPT.format(user_input=user_input)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": search_prompt}],
            max_tokens=200
        )
        queries = json.loads(response.choices[0].message.content)
    except Exception as e:
        # Fallback
        queries = [user_input]
        print(f"Error generating queries: {e}")

    # 3. Execute Searches
    search_context = ""
    for q in queries: # Execute all generated queries
        if stop_event and stop_event.is_set(): break
        try:
            results = perform_web_search(q)
            search_context += f"Query: {q}\n{results}\n\n"
            time.sleep(1) # Polite delay
        except Exception:
            pass
            
    if not search_context:
        return {
            "is_search": True,
            "companies": [],
            "message": "No search results found to extract companies from."
        }

    # 4. Extract Companies
    if stop_event and stop_event.is_set():
        return {"companies": [], "message": "Stopped"}
        
    try:
        extract_prompt = COMPANY_EXTRACTION_PROMPT.format(user_input=user_input, search_results=search_context)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": extract_prompt}],
            max_tokens=4096
        )
        companies_json = response.choices[0].message.content
        
        # Parse JSON (handle markdown fences if present)
        if "```json" in companies_json:
            companies_json = companies_json.split("```json")[1].split("```")[0]
        elif "```" in companies_json:
            companies_json = companies_json.split("```")[1].split("```")[0]
            
        companies = json.loads(companies_json.strip())
        
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
