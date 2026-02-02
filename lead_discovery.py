"""
B2B Lead Discovery and Validation Chatbot
Powered by Groq API (Free & Fast!)
"""

import os
import json
from dotenv import load_dotenv
from groq import Groq

# Load environment variables
load_dotenv()

# System prompt for lead discovery
SYSTEM_PROMPT = """You are an AI agent designed to assist with B2B lead discovery and validation.

You must only analyze the information explicitly provided by the user.
You must never invent or assume companies, people, roles, emails, phone numbers, or any personal data.

If any required information is missing, unclear, or ambiguous, you must reject the lead with a clear reason.

Your Responsibilities

Company Evaluation
- Analyze the company's industry and size.
- Decide whether the company is suitable for B2B sales targeting.
- Clearly accept or reject the company.

Role Evaluation
- Evaluate each role title provided.
- Accept only roles that clearly have decision-making or strong influence.
- Reject vague, junior, or unrelated roles.

Lead Verification
- Combine company and role evaluations.
- Assign a confidence score between 0.0 and 1.0.
- Decide whether this is a verified lead.

Decision Rules
- Reject if company relevance is unclear.
- Reject if no valid decision-making role exists.
- Reject if confidence score is below 0.7.
- Prefer rejecting uncertain data over accepting it.

Output Rules (Strict)
- Output only valid JSON.
- Do not include markdown.
- Do not include explanations outside JSON.
- Do not add extra fields.

Required Output Format:
{
  "company": {
    "name": "",
    "status": "accepted | rejected",
    "reason": ""
  },
  "roles": [
    {
      "title": "",
      "status": "accepted | rejected",
      "reason": ""
    }
  ],
  "lead": {
    "status": "verified | rejected",
    "confidence_score": 0.0,
    "reason": ""
  }
}

Behavior Constraints
- Never guess missing information.
- Never fabricate personal or contact data.
- If unsure, reject with explanation.
- Be deterministic and consistent."""


def create_client():
    """Create Groq client with API key from environment."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("\n❌ Error: GROQ_API_KEY not found in environment.")
        print("Please create a .env file with your API key:")
        print("  GROQ_API_KEY=your_api_key_here")
        print("\nGet a FREE API key at: https://console.groq.com\n")
        exit(1)
    return Groq(api_key=api_key)


def analyze_lead(client, user_input):
    """Send user input to Groq and get lead analysis."""
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=1024,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_input}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "company": {"name": "", "status": "rejected", "reason": "API error occurred"},
            "roles": [],
            "lead": {"status": "rejected", "confidence_score": 0.0, "reason": f"Error: {str(e)}"}
        }, indent=2)


def format_output(response_text):
    """Pretty print the JSON response."""
    try:
        # Try to parse and re-format the JSON
        data = json.loads(response_text)
        return json.dumps(data, indent=2)
    except json.JSONDecodeError:
        # If not valid JSON, return as-is
        return response_text


def print_banner():
    """Print the chatbot banner."""
    print("\n" + "=" * 60)
    print("  🎯 B2B Lead Discovery & Validation Chatbot")
    print("  Powered by Groq (Llama 3.3 70B)")
    print("=" * 60)
    print("\nEnter company and role details to analyze leads.")
    print("Type 'quit' or 'exit' to stop.\n")
    print("Example input:")
    print("  Company: Acme Corp, Industry: SaaS, Size: 500 employees")
    print("  Roles: CEO, Marketing Manager, Sales Intern")
    print("-" * 60 + "\n")


def main():
    """Main chatbot loop."""
    print_banner()
    
    # Initialize client
    client = create_client()
    print("✅ Connected to Groq API\n")
    
    while True:
        try:
            # Get user input
            user_input = input("📝 Enter lead details:\n> ").strip()
            
            # Check for exit commands
            if user_input.lower() in ["quit", "exit", "q"]:
                print("\n👋 Goodbye!\n")
                break
            
            # Skip empty input
            if not user_input:
                print("⚠️  Please enter some lead details.\n")
                continue
            
            # Analyze the lead
            print("\n🔄 Analyzing lead...\n")
            response = analyze_lead(client, user_input)
            formatted = format_output(response)
            
            # Print result
            print("📊 Lead Analysis Result:")
            print("-" * 40)
            print(formatted)
            print("-" * 40 + "\n")
            
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Goodbye!\n")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")


if __name__ == "__main__":
    main()
