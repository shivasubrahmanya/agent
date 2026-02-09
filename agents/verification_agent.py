"""
Verification Agent - Stage 5
Final verification and confidence scoring
"""

import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

VERIFICATION_PROMPT = """You are a B2B lead verification agent.

Review all gathered data and make a final verification decision.

Scoring Rules:
- Start with 0.5 base score
- Company accepted & B2B relevant: +0.2
- Has accepted roles with decision_power >= 7: +0.2
- Has enriched contacts with emails: +0.1
- Multiple decision-makers found: +0.1

Rejection Rules:
- Company rejected: Reject lead
- No roles with decision_power >= 7: Reject lead
- Final confidence < 0.7: Reject lead

Output Rules:
- Only output valid JSON
- No markdown

Required Output Format:
{
  "status": "verified | rejected",
  "confidence_score": 0.85,
  "reason": "detailed explanation",
  "summary": "one-line summary of the lead",
  "recommended_action": "what to do next"
}"""


def run(company: dict, roles: list, contacts: list, stop_event=None) -> dict:
    """
    Run final verification.
    
    Args:
        company: Company data from discovery
        roles: Role data from role mapping
        contacts: Contact data from enrichment
        stop_event: Optional threading.Event to check for stop signal
        
    Returns:
        Dict with final verification result
    """
    if stop_event and stop_event.is_set():
        raise KeyboardInterrupt("Stopped by user")

    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key:
        return {
            "status": "rejected",
            "confidence_score": 0.0,
            "reason": "GROQ_API_KEY not configured"
        }
    
    # Quick checks before LLM
    if company.get("status") == "rejected":
        return {
            "status": "rejected",
            "confidence_score": 0.0,
            "reason": f"Company rejected: {company.get('reason', 'Not suitable')}",
            "summary": f"{company.get('name')} - Company not suitable for B2B",
            "recommended_action": "Skip this company"
        }
    
    accepted_roles = [r for r in roles if r.get("status") == "accepted"]
    if not accepted_roles:
        return {
            "status": "rejected",
            "confidence_score": 0.2,
            "reason": "No decision-making roles identified",
            "summary": f"{company.get('name')} - No high-value targets",
            "recommended_action": "Try with more senior role titles"
        }
    
    client = Groq(api_key=api_key)
    
    try:
        # Build context for verification
        context = f"""
Company: {json.dumps(company, indent=2)}

Accepted Roles ({len(accepted_roles)}):
{json.dumps(accepted_roles, indent=2)}

Enriched Contacts ({len(contacts)}):
{json.dumps(contacts, indent=2)}
"""
        
        if stop_event and stop_event.is_set():
            raise KeyboardInterrupt("Stopped by user")

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=512,
            messages=[
                {"role": "system", "content": VERIFICATION_PROMPT},
                {"role": "user", "content": context}
            ]
        )
        
        result = response.choices[0].message.content
        
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            start = result.find("{")
            end = result.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(result[start:end])
            
            # Calculate score manually
            score = 0.5
            if company.get("status") == "accepted":
                score += 0.2
            if accepted_roles:
                score += 0.2
            if contacts:
                score += 0.1
            if len([c for c in contacts if c.get("email")]) > 0:
                score += 0.05
            
            return {
                "status": "verified" if score >= 0.7 else "rejected",
                "confidence_score": round(score, 2),
                "reason": "Calculated based on available data",
                "summary": f"{company.get('name')} - {len(accepted_roles)} decision-makers, {len(contacts)} contacts",
                "recommended_action": "Proceed with outreach" if score >= 0.7 else "Gather more data"
            }
            
    except Exception as e:
        return {
            "status": "rejected",
            "confidence_score": 0.0,
            "reason": f"Error: {str(e)}"
        }
