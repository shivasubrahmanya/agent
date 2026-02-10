import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

from services.linkedin_search import search_people_at_company

def test_search():
    print("Testing LinkedIn Search...")
    company = "Microsoft"
    print(f"Searching for people at {company}...")
    
    try:
        results = search_people_at_company(company, max_results=5)
        
        if not results:
            print("❌ No results found.")
            return

        print(f"✅ Found {len(results)} people:")
        for p in results:
            print(f"  - {p.get('name')} | {p.get('title')} | {p.get('linkedin_url')}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_search()
