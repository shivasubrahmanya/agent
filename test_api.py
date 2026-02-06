
import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
print(f"Loaded Key: {api_key[:10]}...{api_key[-5:] if api_key else 'None'}")
print(f"Key Length: {len(api_key) if api_key else 0}")

if not api_key:
    print("❌ No API Key found!")
    exit(1)

try:
    client = Groq(api_key=api_key)
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": "Test",
            }
        ],
        model="llama-3.3-70b-versatile",
    )
    print("✅ API Call Successful!")
    print(chat_completion.choices[0].message.content)
except Exception as e:
    print(f"❌ API Call Failed: {e}")
