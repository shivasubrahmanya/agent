
import os
import sys
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

def test_groq():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("ERROR: GROQ_API_KEY not found in .env")
        return
    
    print(f"Testing Groq with key starting with: {api_key[:10]}...")
    client = Groq(api_key=api_key)
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": "Say hello"}],
            max_tokens=10
        )
        print("Groq Success:", response.choices[0].message.content)
    except Exception as e:
        print("Groq Error:", str(e))

def test_serp():
    api_key = os.getenv("SERP_API_KEY")
    if not api_key:
        print("ERROR: SERP_API_KEY not found in .env")
        return
    import requests
    try:
        url = f"https://serpapi.com/search.json?q=test&api_key={api_key}"
        resp = requests.get(url)
        if resp.status_code == 200:
            print("SerpApi Success")
        else:
            print(f"SerpApi Error: {resp.status_code} - {resp.text}")
    except Exception as e:
        print("SerpApi Exception:", str(e))

if __name__ == "__main__":
    print("--- API DIAGNOSTIC ---")
    test_groq()
    test_serp()
