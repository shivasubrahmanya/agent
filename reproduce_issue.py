import os
import sys
from dotenv import load_dotenv

# Add project root to sys.path
sys.path.insert(0, os.getcwd())

from agents import lead_finder_agent

load_dotenv(override=True)

def test_heuristic():
    user_input = "Some startups in mangalore"
    print(f"Input: '{user_input}'")
    
    triggers = ["find", "search", "list", "who are", "companies", "startups", "firms", "agencies"]
    is_search = any(t in user_input.lower() for t in triggers) or len(user_input.split()) > 4
    
    print(f"Triggers check: {any(t in user_input.lower() for t in triggers)}")
    print(f"Split check (len {len(user_input.split())} > 4): {len(user_input.split()) > 4}")
    print(f"Final is_search: {is_search}")
    
    print("\nRunning full agent...")
    result = lead_finder_agent.run(user_input)
    print(f"Result is_search: {result.get('is_search')}")
    print(f"Message: {result.get('message')}")
    print(f"Companies found: {len(result.get('companies', []))}")

if __name__ == "__main__":
    test_heuristic()
