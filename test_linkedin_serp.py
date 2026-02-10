import os
import sys
from dotenv import load_dotenv

# Add project root to sys.path
sys.path.insert(0, os.getcwd())

from services.linkedin_search import search_decision_makers
from services.web_search import google_custom_search

load_dotenv()

def test_linkedin_search():
    company_name = "Robert Bosch GmbH"
    print(f"Testing LinkedIn Search for: {company_name}")
    print("-" * 30)

    # 1. Test raw SerpApi query
    query = f'site:linkedin.com/in "{company_name}" "CEO"'
    print(f"Testing raw query: {query}")
    results = google_custom_search(query, num_results=5)
    
    print(f"Found {len(results)} results")
    for r in results:
        if r.get("error"):
            print(f"Error: {r['error']}")
        else:
            print(f"Title: {r.get('title')}")
            print(f"Link: {r.get('href')}")
            print(f"Source: {r.get('source')}")
            print("-" * 10)

    # 2. Test high-level search_decision_makers
    print("\nTesting search_decision_makers...")
    decision_makers = search_decision_makers(company_name, company_size="enterprise")
    print(f"Found {len(decision_makers)} decision makers")
    for dm in decision_makers:
        print(f"Name: {dm.get('name')}")
        print(f"Title: {dm.get('title')}")
        print(f"LinkedIn: {dm.get('linkedin_url')}")
        print("-" * 10)

if __name__ == "__main__":
    test_linkedin_search()
