
import os
import sys
import json
from dotenv import load_dotenv

# Ensure we can import agents
sys.path.append(os.getcwd())
load_dotenv()

def verify_agents():
    print("--- VERIFYING AGENT FIXES ---")
    
    print("1. Importing agents...", end=" ")
    try:
        from agents import discovery_agent
        from agents import structure_agent
        from agents import verification_agent
        print("SUCCESS")
    except Exception as e:
        print(f"FAILED: {e}")
        return

    print("\n2. Testing Discovery Agent (Mock)...")
    try:
        # We perform a real run but rely on existing behavior (or error handling)
        # To avoid rate limits/cost, we can try a simple input
        # But we need to verify indentation logic works, i.e. it doesn't return None immediately
        # We can mock Groq client or just see if it runs to the point of API call
        
        # Let's run with a known company "Google" 
        result = discovery_agent.run("Google", use_web_search=False) # Should fall back to Apollo or prompt
        print(f"   Result Type: {type(result)}")
        if result is None:
             print("   FAILED: returned None (Indentation bug still present?)")
        else:
             print(f"   SUCCESS: returned dict keys: {list(result.keys())}")
             print(f"   Run output summary: {result.get('status')}")
    except Exception as e:
        print(f"   FAILED with Exception: {e}")

    print("\n3. Testing Structure Agent...")
    try:
        company_data = {"name": "Google", "size": "enterprise", "industry": "Tech"}
        result = structure_agent.run(company_data)
        print(f"   Result Type: {type(result)}")
        if result is None:
             print("   FAILED: returned None")
        else:
             print(f"   SUCCESS: departments found: {len(result.get('departments', []))}")
    except Exception as e:
        print(f"   FAILED with Exception: {e}")

    print("\n4. Testing Verification Agent...")
    try:
        # Mock inputs
        roles = [{"name": "Sundar Pichai", "title": "CEO", "status": "accepted", "decision_power": 10}]
        contacts = [{"email": "sundar@google.com"}]
        result = verification_agent.run(company_data, roles, contacts)
        print(f"   Result Type: {type(result)}")
        if result is None:
             print("   FAILED: returned None")
        else:
             print(f"   SUCCESS: status={result.get('status')}, score={result.get('confidence_score')}")
    except Exception as e:
        print(f"   FAILED with Exception: {e}")

if __name__ == "__main__":
    verify_agents()
