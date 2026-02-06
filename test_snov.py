
import os
from dotenv import load_dotenv
import requests
import json

load_dotenv()

CLIENT_ID = os.getenv("SNOV_CLIENT_ID")
CLIENT_SECRET = os.getenv("SNOV_CLIENT_SECRET")

print(f"Testing Snov.io with:")
print(f"ID: {CLIENT_ID}")
print(f"Secret: {CLIENT_SECRET[:5]}...")

# 1. Authenticate
try:
    auth_resp = requests.post(
        "https://api.snov.io/v1/oauth/access_token",
        json={
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET
        }
    )
    print(f"\nAuth Status: {auth_resp.status_code}")
    if auth_resp.status_code == 200:
        token = auth_resp.json().get("access_token")
        print("✅ Authentication Successful")
        
        # 2. Test Email Find (known entity)
        print("\nTesting Email Find for: Satya Nadella @ microsoft.com")
        find_resp = requests.post(
            "https://api.snov.io/v1/get-emails-from-names",
            json={
                "firstName": "Satya",
                "lastName": "Nadella",
                "domain": "microsoft.com"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        print(f"Find Status: {find_resp.status_code}")
        print(json.dumps(find_resp.json(), indent=2))
        
    else:
        print("❌ Authentication Failed")
        print(auth_resp.text)

except Exception as e:
    print(f"❌ Error: {e}")
