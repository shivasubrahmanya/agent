
import os
import sys
import json
from dotenv import load_dotenv

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents import enrichment_agent
from services import apollo_client, snov_client

def debug_enrichment():
    load_dotenv()
    
    print("=== DEBUGGING ENRICHMENT AGENT ===")
    
    # 1. Config Check
    print("\n1. Configuration Check:")
    print(f"Apollo API Key Present: {bool(os.getenv('APOLLO_API_KEY'))}")
    print(f"Snov Client ID Present: {bool(os.getenv('SNOV_CLIENT_ID'))}")
    print(f"Snov Client Secret Present: {bool(os.getenv('SNOV_CLIENT_SECRET'))}")
    
    print(f"Apollo Client Configured: {apollo_client.is_configured()}")
    print(f"Snov Client Configured: {snov_client.is_configured()}")

    # 2. Test Data
    company = "Stripe"
    domain = "stripe.com"
    roles = [
        {"title": "CTO", "status": "accepted", "name": "[Target Role]"},
        {"title": "VP of Engineering", "status": "accepted", "name": "[Target Role]"}
    ]
    
    print(f"\n2. Running Enrichment for: {company} ({domain})")
    print(f"Roles: {[r['title'] for r in roles]}")
    
    try:
        # Run the agent function directly
        result = enrichment_agent.run(company, roles, company_domain=domain)
        
        print("\n3. Agent Result:")
        print(f"Total Contacts Found: {result.get('total_found', 0)}")
        print(f"Sources Used: {result.get('sources_used', [])}")
        
        # Check specific errors
        apollo_err = result.get('apollo_error')
        snov_err = result.get('snov_error')
        
        if apollo_err:
            print(f"⚠️  Apollo Error: {apollo_err}")
        else:
            print("✅ Apollo: No error reported")
            
        if snov_err:
            print(f"⚠️  Snov Error: {snov_err}")
        else:
            print("✅ Snov: No error reported")
            
        # Check contacts
        contacts = result.get('contacts', [])
        if contacts:
            print(f"\n✅ Found {len(contacts)} contacts:")
            for c in contacts[:3]:
                print(f" - {c.get('first_name')} {c.get('last_name')}")
                print(f"   Email: {c.get('email')}")
                print(f"   LinkedIn: {c.get('linkedin_url')}")
                print(f"   Source: {c.get('source')}")
                print("   ---")
        else:
            print("❌ No contacts returned.")
            
            # If no contacts, try direct client calls to see raw output
            print("\n4. Direct Client Diagnostics:")
            
            print("   --- Direct Apollo ---")
            try:
                raw_apollo = apollo_client.get_top_people(company, limit=1)
                print(f"   Raw Response: {raw_apollo}")
            except Exception as e:
                print(f"   Exception: {e}")
                
            print("   --- Direct Snov ---")
            try:
                raw_snov = snov_client.domain_search(domain, limit=1)
                print(f"   Raw Response: {raw_snov}")
            except Exception as e:
                print(f"   Exception: {e}")

    except Exception as e:
        print(f"\n❌ CRITICAL ERROR running agent: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_enrichment()
