"""
Snov.io API Client (API v2)
Email finding and domain search functionality
"""

import os
import time
import requests
from typing import Dict, Any, List
from dotenv import load_dotenv

load_dotenv(override=True)

SNOV_CLIENT_ID = os.getenv("SNOV_CLIENT_ID", "")
SNOV_CLIENT_SECRET = os.getenv("SNOV_CLIENT_SECRET", "")
SNOV_BASE_URL_V1 = "https://api.snov.io/v1"
SNOV_BASE_URL_V2 = "https://api.snov.io/v2"

# Cache for access token
_access_token = None
_token_expires = 0


def is_configured() -> bool:
    """Check if Snov.io API is configured."""
    return bool(SNOV_CLIENT_ID and SNOV_CLIENT_SECRET)


def get_access_token() -> str:
    """Get OAuth access token from Snov.io (valid for 1 hour)."""
    global _access_token, _token_expires
    
    # Return cached token if still valid
    if _access_token and time.time() < _token_expires:
        return _access_token
    
    if not is_configured():
        return ""
    
    try:
        response = requests.post(
            f"{SNOV_BASE_URL_V1}/oauth/access_token",
            json={
                "grant_type": "client_credentials",
                "client_id": SNOV_CLIENT_ID,
                "client_secret": SNOV_CLIENT_SECRET
            }
        )
        response.raise_for_status()
        data = response.json()
        _access_token = data.get("access_token", "")
        # Token valid for 1 hour, refresh 5 min early
        _token_expires = time.time() + 3300
        return _access_token
    except Exception:
        return ""


def _get_headers() -> Dict[str, str]:
    """Get authorization headers."""
    token = get_access_token()
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }


def domain_search(domain: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Search for emails at a domain using Snov.io API v2.
    
    Args:
        domain: Company domain (e.g., 'stripe.com')
        limit: Max number of results
    
    Returns:
        List of email/contact data
    """
    if not is_configured():
        return [{"error": "Snov.io API not configured"}]
    
    headers = _get_headers()
    
    try:
        # Step 1: Start domain search
        start_response = requests.post(
            f"{SNOV_BASE_URL_V2}/domain-search/start",
            json={"domain": domain},
            headers=headers
        )
        start_response.raise_for_status()
        start_data = start_response.json()
        
        # task_hash is in meta, result URL is in links
        task_hash = start_data.get("meta", {}).get("task_hash")
        result_url = start_data.get("links", {}).get("result")
        
        if not task_hash and not result_url:
            return [{"error": "Failed to start domain search"}]
        
        # Step 2: Wait and get results (with retry)
        max_retries = 5
        for attempt in range(max_retries):
            time.sleep(2)  # Wait for processing
            
            if result_url:
                result_response = requests.get(result_url, headers=headers)
            else:
                result_response = requests.get(
                    f"{SNOV_BASE_URL_V2}/domain-search/result/{task_hash}",
                    headers=headers
                )
            result_response.raise_for_status()
            result_data = result_response.json()
            
            # Check status in meta
            status = result_data.get("meta", {}).get("status")
            if status == "completed":
                break
            elif status == "failed":
                return [{"error": "Domain search failed"}]
        
        # Step 3: Get domain emails from links
        emails_url = result_data.get("links", {}).get("domain_emails")
        prospects_url = result_data.get("links", {}).get("prospects")
        
        results = []
        
        # Try prospects first (has more info)
        if prospects_url:
            prospects_response = requests.get(
                f"{prospects_url}?limit={limit}",
                headers=headers
            )
            if prospects_response.status_code == 200:
                prospects_data = prospects_response.json()
                items = prospects_data.get("data", [])
                if isinstance(items, list):
                    for prospect in items[:limit]:
                        if isinstance(prospect, dict):
                            results.append({
                                "first_name": prospect.get("firstName", prospect.get("first_name", "")),
                                "last_name": prospect.get("lastName", prospect.get("last_name", "")),
                                "email": prospect.get("email", ""),
                                "phone": "",
                                "linkedin_url": prospect.get("social", {}).get("linkedin", "") if isinstance(prospect.get("social"), dict) else "",
                                "title": prospect.get("position", ""),
                                "source": "snov"
                            })
        
        # Fallback to domain emails
        if not results and emails_url:
            emails_response = requests.get(emails_url, headers=headers)
            if emails_response.status_code == 200:
                emails_data = emails_response.json()
                items = emails_data.get("data", [])
                if isinstance(items, list):
                    for email_item in items[:limit]:
                        if isinstance(email_item, dict):
                            results.append({
                                "first_name": "",
                                "last_name": "",
                                "email": email_item.get("email", ""),
                                "phone": "",
                                "linkedin_url": "",
                                "title": email_item.get("type", ""),
                                "source": "snov"
                            })
        
        if not results:
            return [{"error": "No email data found for domain", "domain": domain}]
        
        return results
        
    except requests.exceptions.RequestException as e:
        if e.response is not None and e.response.status_code == 402:
            return [{"error": "Snov.io Plan Limit / Payment Required (402)", "code": "payment_required"}]
        return [{"error": str(e)}]


def find_email(domain: str, first_name: str, last_name: str) -> Dict[str, Any]:
    """
    Find email for a specific person at a company using API v1.
    
    Args:
        domain: Company domain
        first_name: Person's first name
        last_name: Person's last name
    
    Returns:
        Email data for the person
    """
    if not is_configured():
        return {"error": "Snov.io API not configured"}
    
    headers = _get_headers()
    
    try:
        # Use v1 endpoint for email finder
        response = requests.post(
            f"{SNOV_BASE_URL_V1}/get-emails-from-names",
            json={
                "firstName": first_name,
                "lastName": last_name,
                "domain": domain
            },
            headers=headers
        )
        response.raise_for_status()
        data = response.json()
        
        if data.get("success") and data.get("data", {}).get("emails"):
            email_info = data["data"]["emails"][0]
            return {
                "first_name": first_name,
                "last_name": last_name,
                "email": email_info.get("email", ""),
                "confidence": email_info.get("emailStatus", ""),
                "source": "snov"
            }
        
        return {
            "first_name": first_name,
            "last_name": last_name,
            "error": "Email not found"
        }
        
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


def get_prospect_by_email(email: str) -> Dict[str, Any]:
    """
    Get full prospect info by email address.
    
    Args:
        email: Email address to look up
    
    Returns:
        Full prospect data
    """
    if not is_configured():
        return {"error": "Snov.io API not configured"}
    
    headers = _get_headers()
    
    try:
        response = requests.post(
            f"{SNOV_BASE_URL_V1}/get-profile-by-email",
            json={"email": email},
            headers=headers
        )
        response.raise_for_status()
        data = response.json()
        
        if data.get("success") and data.get("data"):
            profile = data["data"]
            current_job = profile.get("currentJobs", [{}])[0] if profile.get("currentJobs") else {}
            return {
                "first_name": profile.get("firstName", ""),
                "last_name": profile.get("lastName", ""),
                "email": email,
                "title": current_job.get("position", ""),
                "company": current_job.get("companyName", ""),
                "linkedin_url": profile.get("social", {}).get("linkedin", "") if profile.get("social") else "",
                "source": "snov"
            }
        
        return {"email": email, "error": "Prospect not found"}
        
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}
