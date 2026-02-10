import os
import sys
import json
from dotenv import load_dotenv

# Load env vars
load_dotenv()

# Add current directory to path
sys.path.append(os.getcwd())

import agents.discovery_agent as discovery_agent
import agents.role_agent as role_agent
import agents.enrichment_agent as enrichment_agent
import agents.verification_agent as scoring_agent

def debug_run():
    # print(f"Checking Keys: GROQ={bool(os.getenv('GROQ_API_KEY'))}, APOLLO={bool(os.getenv('APOLLO_API_KEY'))}, SNOV={bool(os.getenv('SNOV_CLIENT_ID'))}")
    
    # # Test Apollo Direct
    # if os.getenv("APOLLO_API_KEY"):
    #     print("Testing Apollo API direct call...")
    #     try:
    #         from services import apollo_client
    #         test_res = apollo_client.get_top_people("Bosch", limit=1)
    #         print(f"Apollo Test Result: {json.dumps(test_res, indent=2)}")
    #     except Exception as e:
    #         print(f"Apollo Test Failed: {e}")

    # # Test Snov Direct
    # if os.getenv("SNOV_CLIENT_ID"):
    #     print("Testing Snov API direct call...")
    #     try:
    #         from services import snov_client
    #         test_res = snov_client.domain_search("bosch.com", limit=1)
    #         print(f"Snov Test Result: {json.dumps(test_res, indent=2)}")
    #     except Exception as e:
    #         print(f"Snov Test Failed: {e}")

    company_input = "Bosch"
    print(f"DEBUG: Starting Run for '{company_input}'...")

    # 1. Discovery
    print("\n--- 1. Running Discovery Agent ---")
    try:
        discovery_result = discovery_agent.run(company_input)
        print(json.dumps(discovery_result, indent=2))
        
        if discovery_result.get("status") == "rejected":
            print("Company Rejected at Discovery")
            return
            
    except Exception as e:
        print(f"Discovery Failed: {e}")
        return

    company_name = discovery_result.get("name")
    company_size = discovery_result.get("size", "medium")
    print(f"Company Identified: {company_name} ({company_size})")

    # 2. Roles
    print("\n--- 2. Running Role Agent ---")
    try:
        # Extract domain
        domain = discovery_result.get("website")
        if domain:
             domain = domain.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
             
        role_result = role_agent.run(company_name, company_size, company_domain=domain)
        print(json.dumps(role_result, indent=2))
    except Exception as e:
        print(f"Role Agent Failed: {e}")
        role_result = {"people": []}

    # 3. Enrichment
    print("\n--- 3. Running Enrichment Agent ---")
    try:
        # Extract domain from website or name
        domain = discovery_result.get("website")
        if not domain:
            from agents.enrichment_agent import extract_domain
            domain = extract_domain(company_name)
            
        print(f"Using Domain: {domain}")
        
        # Get roles to search for
        roles_to_enrich = role_result.get("people", [])
        
        enrichment_result = enrichment_agent.run(
            company_name=company_name,
            roles=roles_to_enrich,
            company_domain=domain
        )
        print(json.dumps(enrichment_result, indent=2))
    except Exception as e:
        print(f"Enrichment Failed: {e}")
        enrichment_result = {}

    # 4. Scoring
    print("\n--- 4. Running Scoring Agent ---")
    try:
        score_result = scoring_agent.run(
            company=discovery_result, 
            roles=role_result.get("people", []), 
            contacts=enrichment_result.get("contacts", [])
        )
        print(json.dumps(score_result, indent=2))
    except Exception as e:
        print(f"Scoring Failed: {e}")

if __name__ == "__main__":
    debug_run()
