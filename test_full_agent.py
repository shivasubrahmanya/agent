import os
import sys
import json
from dotenv import load_dotenv

# Add project root to sys.path
sys.path.insert(0, os.getcwd())

from agents import lead_finder_agent

load_dotenv(override=True)

def test_full_agent():
    user_input = "Some startups in mangalore"
    print(f"Testing input: '{user_input}'")
    
    result = lead_finder_agent.run(user_input)
    
    print("\nAGENT OUTPUT:")
    print(json.dumps(result, indent=2))
    
    if result.get("is_search"):
        print(f"\nSUCCESS: Correctly identified as search.")
        if result.get("companies"):
            print(f"Found {len(result['companies'])} companies.")
        else:
            print("WARNING: No companies found in search results.")
    else:
        print("\nFAILURE: Identified as direct analysis (incorrect).")

if __name__ == "__main__":
    test_full_agent()
