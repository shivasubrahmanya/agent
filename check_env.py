import os
from dotenv import load_dotenv

# Try loading with override=True to see if it changes anything
print("--- Loading .env ---")
load_dotenv(override=True)

api_key = os.getenv("GOOGLE_API_KEY")
print(f"GOOGLE_API_KEY: {api_key[:5] if api_key else 'None'}...{api_key[-5:] if api_key else 'None'}")
print(f"CWD: {os.getcwd()}")
print(f"File exists: {os.path.exists('.env')}")

if os.path.exists(".env"):
    with open(".env", "r") as f:
        content = f.read()
        print("--- .env File Content (Google Section) ---")
        for line in content.splitlines():
            if "GOOGLE" in line:
                print(line)
