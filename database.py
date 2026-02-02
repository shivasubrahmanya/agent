"""
Local JSON Database for Lead Storage
"""

import os
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

# Data directory
DATA_DIR = Path(__file__).parent / "data"


def ensure_data_dir():
    """Create data directory if it doesn't exist."""
    DATA_DIR.mkdir(exist_ok=True)


def _get_file_path(collection: str) -> Path:
    """Get path for a collection file."""
    ensure_data_dir()
    return DATA_DIR / f"{collection}.json"


def _load_collection(collection: str) -> List[Dict[str, Any]]:
    """Load all items from a collection."""
    file_path = _get_file_path(collection)
    if not file_path.exists():
        return []
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_collection(collection: str, data: List[Dict[str, Any]]):
    """Save items to a collection."""
    file_path = _get_file_path(collection)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# Lead operations
def save_lead(lead_data: Dict[str, Any]) -> str:
    """Save or update a lead."""
    leads = _load_collection("leads")
    lead_id = lead_data.get("id")
    
    # Update existing or append new
    found = False
    for i, lead in enumerate(leads):
        if lead.get("id") == lead_id:
            lead_data["updated_at"] = datetime.now().isoformat()
            leads[i] = lead_data
            found = True
            break
    
    if not found:
        lead_data["created_at"] = datetime.now().isoformat()
        lead_data["updated_at"] = lead_data["created_at"]
        leads.append(lead_data)
    
    _save_collection("leads", leads)
    return lead_id


def get_lead(lead_id: str) -> Optional[Dict[str, Any]]:
    """Get a lead by ID."""
    leads = _load_collection("leads")
    for lead in leads:
        if lead.get("id") == lead_id:
            return lead
    return None


def list_leads(status: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all leads, optionally filtered by status."""
    leads = _load_collection("leads")
    if status:
        return [l for l in leads if l.get("status") == status]
    return leads


def delete_lead(lead_id: str) -> bool:
    """Delete a lead by ID."""
    leads = _load_collection("leads")
    original_len = len(leads)
    leads = [l for l in leads if l.get("id") != lead_id]
    if len(leads) < original_len:
        _save_collection("leads", leads)
        return True
    return False


# Company operations
def save_company(company_data: Dict[str, Any]) -> str:
    """Save a company."""
    companies = _load_collection("companies")
    name = company_data.get("name", "").lower()
    
    # Update existing or append new
    found = False
    for i, company in enumerate(companies):
        if company.get("name", "").lower() == name:
            companies[i] = company_data
            found = True
            break
    
    if not found:
        companies.append(company_data)
    
    _save_collection("companies", companies)
    return name


def get_company(name: str) -> Optional[Dict[str, Any]]:
    """Get a company by name."""
    companies = _load_collection("companies")
    name_lower = name.lower()
    for company in companies:
        if company.get("name", "").lower() == name_lower:
            return company
    return None


# Export functionality
def export_leads_to_csv(filepath: str = "leads_export.csv") -> str:
    """Export all leads to CSV."""
    import csv
    
    leads = _load_collection("leads")
    if not leads:
        return "No leads to export"
    
    # Flatten lead data for CSV
    rows = []
    for lead in leads:
        company = lead.get("company", {})
        contacts = lead.get("contacts", [])
        
        if contacts:
            for contact in contacts:
                rows.append({
                    "lead_id": lead.get("id", ""),
                    "company_name": company.get("name", ""),
                    "company_industry": company.get("industry", ""),
                    "company_status": company.get("status", ""),
                    "contact_name": f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip(),
                    "contact_title": contact.get("title", ""),
                    "contact_email": contact.get("email", ""),
                    "contact_phone": contact.get("phone", ""),
                    "contact_linkedin": contact.get("linkedin_url", ""),
                    "lead_status": lead.get("status", ""),
                    "confidence_score": lead.get("confidence_score", 0),
                })
        else:
            rows.append({
                "lead_id": lead.get("id", ""),
                "company_name": company.get("name", ""),
                "company_industry": company.get("industry", ""),
                "company_status": company.get("status", ""),
                "contact_name": "",
                "contact_title": "",
                "contact_email": "",
                "contact_phone": "",
                "contact_linkedin": "",
                "lead_status": lead.get("status", ""),
                "confidence_score": lead.get("confidence_score", 0),
            })
    
    if rows:
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        return filepath
    
    return "No data to export"
