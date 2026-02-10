import os
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

def test():
    api_key = os.getenv('GOOGLE_API_KEY')
    cx = os.getenv('GOOGLE_CX')
    
    print(f"API Key: {api_key[:5]}...{api_key[-5:] if api_key else 'None'}")
    print(f"CX: {cx}")

    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": api_key,
        "cx": cx,
        "q": "OpenAI",
        "num": 1
    }
    
    try:
        print("Sending request...")
        response = requests.get(url, params=params)
        
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("✅ SUCCESS!")
            items = response.json().get('items', [])
            if items:
                print(f"Result: {items[0].get('title')}")
                print(f"Link: {items[0].get('link')}")
            else:
                print("⚠️  Success response but no items found (check CX settings).")
        else:
            print("❌ ERROR BODY:")
            print(response.text)
            
    except Exception as e:
        print(f"EXCEPTION: {e}")

if __name__ == "__main__":
    test()
