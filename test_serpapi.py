import os
import requests
from dotenv import load_dotenv

# Force load .env
load_dotenv(override=True)

def test_serpapi():
    api_key = os.getenv("SERP_API_KEY")
    if not api_key:
        print("❌ SERP_API_KEY not found in .env")
        return

    print(f"Using SerpApi Key: {api_key[:5]}...{api_key[-5:]}")
    
    url = "https://serpapi.com/search"
    params = {
        "api_key": api_key,
        "engine": "google",
        "q": "OpenAI",
        "num": 1
    }
    
    try:
        print("Sending request to SerpApi...")
        response = requests.get(url, params=params)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            results = data.get("organic_results", [])
            if results:
                print("✅ SUCCESS!")
                print(f"Result: {results[0].get('title')}")
                print(f"Link: {results[0].get('link')}")
            else:
                print("⚠️  Success response but no organic results found.")
        else:
            print("❌ ERROR BODY:")
            print(response.text)
            
    except Exception as e:
        print(f"EXCEPTION: {e}")

if __name__ == "__main__":
    test_serpapi()
