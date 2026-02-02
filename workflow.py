"""
Workflow Orchestrator
Runs all stages with the NEW FLOW:
1. Discovery - Web search for company info
2. Structure - Map departments and decision-makers by size
3. Role Discovery - LinkedIn search for actual people
4. Enrichment - Apollo for verified contact details
5. Verification - Final scoring
"""

import uuid
from typing import Callable, Optional
from datetime import datetime

from agents import discovery_agent, structure_agent, role_agent, enrichment_agent, verification_agent
import database as db


class WorkflowProgress:
    """Simple progress callback interface."""
    def __init__(self, callback: Optional[Callable] = None):
        self.callback = callback
    
    def update(self, stage: str, status: str, data: dict = None):
        if self.callback:
            self.callback(stage, status, data)


def parse_input(user_input: str) -> tuple:
    """
    Parse user input into company and optional roles.
    
    Formats supported:
    - "Microsoft" (company only - will auto-discover roles)
    - "Microsoft, Roles: CEO, VP Sales" (with specific roles)
    
    Returns:
        (company_name, roles_list)
    """
    company = ""
    roles = []
    
    text = user_input.strip()
    
    if "Roles:" in text or "roles:" in text:
        parts = text.replace("roles:", "Roles:").split("Roles:")
        company_part = parts[0].strip()
        roles_part = parts[1].strip() if len(parts) > 1 else ""
        
        company = company_part.replace("Company:", "").replace("company:", "").strip()
        company = company.rstrip(",").strip()
        
        if roles_part:
            roles = [r.strip() for r in roles_part.split(",") if r.strip()]
    else:
        company = text.replace("Company:", "").replace("company:", "").strip()
    
    return company, roles


def run_pipeline(
    user_input: str,
    progress: Optional[WorkflowProgress] = None
) -> dict:
    """
    Run the full lead discovery pipeline.
    
    NEW FLOW:
    1. Discovery: Web search for company info
    2. Structure: Map decision-makers by company size
    3. Role Discovery: LinkedIn search for actual people
    4. Enrichment: Apollo for verified contacts
    5. Verification: Final scoring
    """
    lead_id = str(uuid.uuid4())[:8]
    
    company_name, user_roles = parse_input(user_input)
    
    if not company_name:
        return {
            "id": lead_id,
            "error": "No company name provided",
            "status": "rejected"
        }
    
    lead_data = {
        "id": lead_id,
        "input": user_input,
        "status": "analyzing",
        "stages": {}
    }
    
    # ═══════════════════════════════════════════════════
    # STAGE 1: DISCOVERY (Web Search)
    # ═══════════════════════════════════════════════════
    if progress:
        progress.update("discovery", "running", {"company": company_name})
    
    company_result = discovery_agent.run(company_name, use_web_search=True)
    lead_data["company"] = company_result
    lead_data["stages"]["discovery"] = "completed"
    
    if progress:
        progress.update("discovery", "completed", company_result)
    
    # Early exit if company rejected
    if company_result.get("status") == "rejected":
        lead_data["status"] = "rejected"
        lead_data["reason"] = company_result.get("reason", "Company not suitable")
        lead_data["confidence_score"] = 0.0
        db.save_lead(lead_data)
        return lead_data
    
    company_size = company_result.get("size", "medium")
    
    # ═══════════════════════════════════════════════════
    # STAGE 2: STRUCTURE (Decision-Makers by Size)
    # ═══════════════════════════════════════════════════
    if progress:
        progress.update("structure", "running")
    
    structure_result = structure_agent.run(company_result)
    lead_data["structure"] = structure_result
    lead_data["stages"]["structure"] = "completed"
    
    if progress:
        progress.update("structure", "completed", structure_result)
    
    # ═══════════════════════════════════════════════════
    # STAGE 3: ROLE DISCOVERY (LinkedIn Search)
    # ═══════════════════════════════════════════════════
    if progress:
        progress.update("roles", "running", {"searching": "LinkedIn"})
    
    # Use new role agent that searches LinkedIn
    roles_result = role_agent.run(
        company_name=company_result.get("name", company_name),
        company_size=company_size,
        structure_data=structure_result
    )
    
    lead_data["people"] = roles_result.get("people", [])
    lead_data["people_summary"] = roles_result.get("summary", "")
    lead_data["linkedin_searched"] = roles_result.get("linkedin_searched", False)
    lead_data["stages"]["roles"] = "completed"
    
    if progress:
        progress.update("roles", "completed", roles_result)
    
    # Get accepted people for enrichment
    accepted_people = [p for p in lead_data["people"] if p.get("status") == "accepted"]
    
    # ═══════════════════════════════════════════════════
    # STAGE 4: ENRICHMENT (Apollo for Verified Contacts)
    # ═══════════════════════════════════════════════════
    if progress:
        progress.update("enrichment", "running")
    
    # Convert people to roles format for enrichment
    roles_for_enrichment = [
        {"title": p.get("title", ""), "status": p.get("status", "rejected")}
        for p in accepted_people
    ]
    
    enrichment_result = enrichment_agent.run(
        company_name=company_result.get("name", company_name),
        roles=roles_for_enrichment
    )
    lead_data["contacts"] = enrichment_result.get("contacts", [])
    lead_data["enrichment_note"] = enrichment_result.get("note", "")
    lead_data["stages"]["enrichment"] = "completed"
    
    if progress:
        progress.update("enrichment", "completed", enrichment_result)
    
    # ═══════════════════════════════════════════════════
    # STAGE 5: VERIFICATION (Final Scoring)
    # ═══════════════════════════════════════════════════
    if progress:
        progress.update("verification", "running")
    
    # Convert people to roles format for verification
    roles_for_verification = [
        {
            "title": p.get("title", ""),
            "status": p.get("status", "rejected"),
            "decision_power": p.get("decision_power", 0),
            "name": p.get("name", "")
        }
        for p in lead_data["people"]
    ]
    
    verification_result = verification_agent.run(
        company=company_result,
        roles=roles_for_verification,
        contacts=lead_data["contacts"]
    )
    
    lead_data["status"] = verification_result.get("status", "rejected")
    lead_data["confidence_score"] = verification_result.get("confidence_score", 0.0)
    lead_data["reason"] = verification_result.get("reason", "")
    lead_data["summary"] = verification_result.get("summary", "")
    lead_data["recommended_action"] = verification_result.get("recommended_action", "")
    lead_data["stages"]["verification"] = "completed"
    
    if progress:
        progress.update("verification", "completed", verification_result)
    
    # Save to database
    db.save_lead(lead_data)
    
    return lead_data


def enrich_person_direct(name: str, company: str, progress: Optional[WorkflowProgress] = None) -> dict:
    """Direct person enrichment via Apollo."""
    parts = name.strip().split()
    if len(parts) >= 2:
        first_name = parts[0]
        last_name = " ".join(parts[1:])
    else:
        first_name = name
        last_name = ""
    
    if progress:
        progress.update("enrichment", "running", {"name": name, "company": company})
    
    result = enrichment_agent.enrich_single(first_name, last_name, company)
    
    if progress:
        progress.update("enrichment", "completed", result)
    
    return result
