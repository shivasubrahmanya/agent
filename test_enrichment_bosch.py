import os
import sys
from dotenv import load_dotenv

# Add project root to sys.path
sys.path.insert(0, os.getcwd())

from services.apollo_client import get_top_people, is_configured as apollo_configured
from services.snov_client import domain_search, is_configured as snov_configured
from agents.enrichment_agent import extract_domain

load_dotenv()

def test_bosch():
    company_name = "Robert Bosch GmbH"
    likely_domain = extract_domain(company_name)
    real_domain = "bosch.com"
    
    print(f"Testing Company: {company_name}")
    print(f"Extracted Domain: {likely_domain}")
    print(f"Real Domain: {real_domain}")
    print("-" * 30)

    # 1. Test Apollo
    if apollo_configured():
        print("Testing Apollo with Name...")
        results = get_top_people(company_name)
        print(f"Results with Name: {len(results)}")
        if results and "error" in results[0]:
             print(f"Error: {results[0]['error']}")
        
        print("\nTesting Apollo with Real Domain...")
        results_domain = get_top_people(real_domain)
        print(f"Results with Domain: {len(results_domain)}")
        if results_domain and results_domain[0].get("first_name"):
             print(f"Sample: {results_domain[0]['first_name']} {results_domain[0]['last_name']}")
    else:
        print("Apollo not configured")

    print("-" * 30)

    # 2. Test Snov
    if snov_configured():
        print(f"Testing Snov with Extracted Domain ({likely_domain})...")
        s_results = domain_search(likely_domain)
        print(f"Results: {len(s_results)}")
        if s_results and "error" in s_results[0]:
             print(f"Error: {s_results[0]['error']}")

        print(f"\nTesting Snov with Real Domain ({real_domain})...")
        s_results_real = domain_search(real_domain)
        print(f"Results: {len(s_results_real)}")
        if s_results_real and s_results_real[0].get("email"):
             print(f"Sample: {s_results_real[0]['email']}")
    else:
        print("Snov not configured")

if __name__ == "__main__":
    test_bosch()
