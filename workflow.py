"""
Workflow Orchestrator - Long Running Agent Version
Runs all stages with checkpointing, memory integration, and auto-recovery.

NEW FLOW (with memory and checkpointing):
1. Discovery - Web search for company info (with memory context)
2. Structure - Map departments and decision-makers by size
3. Role Discovery - LinkedIn search for actual people
4. Enrichment - Apollo for verified contact details (with cached data)
5. Verification - Final scoring (with historical patterns)

Features:
- Checkpoint after each stage
- Resume from last checkpoint on failure
- Memory-aware context injection
- Auto-retry with error handling
- Execution history logging
"""

import uuid
import threading
from typing import Callable, Optional
from datetime import datetime

from agents import discovery_agent, structure_agent, role_agent, enrichment_agent, verification_agent
import database as db

# Import memory system
try:
    from memory import MemoryManager, StateManager, ContextBuilder
    MEMORY_ENABLED = True
except ImportError:
    MEMORY_ENABLED = False
    print("Note: Memory module not available. Running without memory features.")


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
    - "analyze Microsoft" (strips command word)
    - "analyse Microsoft" (strips typo command word)
    
    Returns:
        (company_name, roles_list)
    """
    company = ""
    roles = []
    
    text = user_input.strip()
    
    # Strip common command words
    command_words = ["analyze", "analyse", "company:"]
    for cmd in command_words:
        if text.lower().startswith(cmd):
            text = text[len(cmd):].strip()
            break
    
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


class LongRunningWorkflow:
    """
    Long-running workflow orchestrator with memory and checkpointing.
    
    Implements:
    - Plan -> Act -> Observe -> Remember -> Re-Plan cycle
    - Checkpoint at each stage
    - Resume from failure
    - Memory-aware context injection
    """
    
    def __init__(self, progress: Optional[WorkflowProgress] = None, stop_event: Optional[threading.Event] = None):
        """Initialize workflow with optional progress callback and stop event."""
        self.progress = progress
        self.stop_event = stop_event
        
        # Initialize memory system
        if MEMORY_ENABLED:
            self.memory = MemoryManager()
            self.state = StateManager()
            self.context_builder = ContextBuilder(self.memory)
        else:
            self.memory = None
            self.state = None
            self.context_builder = None
    
    def run_pipeline(self, user_input: str, resume_id: str = None) -> dict:
        """
        Run the full lead discovery pipeline with memory and checkpointing.
        
        Args:
            user_input: User's company/roles input
            resume_id: Optional execution ID to resume from
            
        Returns:
            Lead data with results from all stages
        """
        # Check for resume FIRST (before parsing input)
        if resume_id and self.state and self.state.can_resume(resume_id):
            return self._resume_pipeline(resume_id)
        
        # Handle "resume" command from input
        if user_input.strip().lower().startswith("resume"):
            if not self.state:
                return {"error": "State management not available", "status": "failed"}
            
            resumables = self.state.get_resumable_executions()
            if not resumables:
                return {"error": "No resumable sessions found", "status": "failed"}
            
            # Sort by updated_at to get the most recent one first
            resumables.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
            
            # Parse arguments: "resume" or "resume 1" or "resume <id>"
            parts = user_input.strip().split(maxsplit=1)
            target_execution = resumables[0] # Default to latest
            
            if len(parts) > 1:
                arg = parts[1].strip()
                
                # Check if index (1-based)
                if arg.isdigit():
                    idx = int(arg) - 1
                    if 0 <= idx < len(resumables):
                        target_execution = resumables[idx]
                    else:
                        return {"error": f"Invalid index {arg}. Available: 1-{len(resumables)}", "status": "failed"}
                else:
                    # Check if ID (partial match)
                    matches = [e for e in resumables if e["id"].startswith(arg)]
                    if len(matches) == 1:
                        target_execution = matches[0]
                    elif len(matches) > 1:
                        return {"error": f"Ambiguous ID '{arg}'. Search matches multiple executions.", "status": "failed"}
                    else:
                        return {"error": f"No execution found matching '{arg}'", "status": "failed"}
            
            return self._resume_pipeline(target_execution["id"])
        
        company_name, user_roles = parse_input(user_input)
        
        if not company_name:
            return {
                "id": str(uuid.uuid4())[:8],
                "error": "No company name provided",
                "status": "rejected"
            }
        
        # Start new execution
        lead_id = str(uuid.uuid4())[:8]
        
        lead_data = {
            "id": lead_id,
            "input": user_input,
            "status": "analyzing",
            "stages": {}
        }
        
        # Initialize state tracking
        if self.state:
            self.state.start_execution(lead_id, {"company": company_name, "roles": user_roles})
        
        # Store in working memory
        if self.memory:
            self.memory.set_working("current_lead_id", lead_id)
            self.memory.set_working("current_company", company_name)
            self.memory.add_to_short_term("execution_start", {
                "lead_id": lead_id,
                "company": company_name,
                "roles": user_roles
            }, importance=8)
        
        try:
            # Run all stages
            lead_data = self._run_all_stages(lead_data, company_name, user_roles)
            
            # Complete execution
            if self.state:
                self.state.complete_execution(lead_data)
                # Clear current execution to prevent conflicts
                self.state._current_execution = None
            
            # Learn from result
            self._learn_from_execution(lead_data)
            
        except KeyboardInterrupt:
            # User interrupted - save checkpoint as PAUSED (can resume)
            print("\n⏸️  Analysis paused. Use 'resume' command to continue.\n")
            if self.state:
                self.state.pause_execution("User interrupted")
            if self.memory:
                self.memory.add_to_short_term("execution_interrupted", {
                    "lead_id": lead_id,
                    "reason": "User interrupt"
                }, importance=9)
            lead_data["status"] = "paused"
            lead_data["can_resume"] = True
            lead_data["id"] = lead_id  # Ensure ID is preserved
        
        except Exception as e:
            # Error - save checkpoint and log
            if self.memory:
                self.memory.remember_failure(
                    context=f"Pipeline for {company_name}",
                    error=str(e),
                    recovery=None
                )
            lead_data["status"] = "failed"
            lead_data["error"] = str(e)
        
        return lead_data
    
    def _run_all_stages(self, lead_data: dict, company_name: str, user_roles: list) -> dict:
        """Run all pipeline stages with checkpointing."""
        
        # ═══════════════════════════════════════════════════════════════
        # STAGE 1: DISCOVERY (Web Search with Memory Context)
        # ═══════════════════════════════════════════════════════════════
        if self.stop_event and self.stop_event.is_set():
            raise KeyboardInterrupt("Analysis stopped by user")

        if self.state:
            self.state.start_stage("discovery")
        if self.progress:
            self.progress.update("discovery", "running", {"company": company_name})
        
        # Get memory context for discovery
        discovery_context = None
        if self.context_builder:
            discovery_context = self.context_builder.build_discovery_context(company_name)
        
        # Check for cached company data
        cached_company = self.memory.recall_company(company_name) if self.memory else None
        
        try:
            company_result = discovery_agent.run(company_name, use_web_search=True, stop_event=self.stop_event)
            
            # Enrich with cached data if available
            if cached_company and cached_company.get("outcome") == "success":
                prev_data = cached_company.get("data", {})
                # Add any missing fields from cache
                for key in ["industry", "location", "website", "growth_signals"]:
                    if not company_result.get(key) and prev_data.get(key):
                        company_result[key] = prev_data[key]
                        company_result["_from_cache"] = True
            
            lead_data["company"] = company_result
            lead_data["stages"]["discovery"] = "completed"
            
            if self.state:
                self.state.complete_stage("discovery", company_result)
            
            # Log to memory
            if self.memory:
                self.memory.add_to_short_term("discovery_complete", {
                    "company": company_name,
                    "status": company_result.get("status"),
                    "industry": company_result.get("industry")
                }, importance=7)
                
        except Exception as e:
            if self.state:
                self.state.fail_stage("discovery", str(e))
            raise
        
        if self.progress:
            self.progress.update("discovery", "completed", company_result)
        
        # Early exit if company rejected
        if company_result.get("status") == "rejected":
            lead_data["status"] = "rejected"
            lead_data["reason"] = company_result.get("reason", "Company not suitable")
            lead_data["confidence_score"] = 0.0
            
            # Remember rejection
            if self.memory:
                self.memory.remember_company(company_name, company_result, outcome="failure")
            
            db.save_lead(lead_data)
            return lead_data
        
        company_size = company_result.get("size", "medium")
        
        # ═══════════════════════════════════════════════════════════════
        # STAGE 2: STRUCTURE (Decision-Makers by Size)
        # ═══════════════════════════════════════════════════════════════
        if self.stop_event and self.stop_event.is_set():
            raise KeyboardInterrupt("Analysis stopped by user")

        if self.state:
            self.state.start_stage("structure")
        if self.progress:
            self.progress.update("structure", "running")
        
        try:
            structure_result = structure_agent.run(company_result, stop_event=self.stop_event)
            lead_data["structure"] = structure_result
            lead_data["stages"]["structure"] = "completed"
            
            if self.state:
                self.state.complete_stage("structure", structure_result)
                
        except Exception as e:
            if self.state:
                self.state.fail_stage("structure", str(e))
            raise
        
        if self.progress:
            self.progress.update("structure", "completed", structure_result)
        
        # ═══════════════════════════════════════════════════════════════
        # STAGE 3: ROLE DISCOVERY (LinkedIn Search)
        # ═══════════════════════════════════════════════════════════════
        if self.stop_event and self.stop_event.is_set():
            raise KeyboardInterrupt("Analysis stopped by user")

        if self.state:
            self.state.start_stage("roles")
        if self.progress:
            self.progress.update("roles", "running", {"searching": "LinkedIn"})
        
        # Extract domain for Snov fallback (Stage 3)
        company_domain_for_search = None
        if company_result.get("website"):
             company_domain_for_search = company_result.get("website").replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]

        try:
            roles_result = role_agent.run(
                company_name=company_result.get("name", company_name),
                company_size=company_size,
                structure_data=structure_result,
                company_domain=company_domain_for_search,
                stop_event=self.stop_event
            )
            
            lead_data["people"] = roles_result.get("people", [])
            lead_data["people_summary"] = roles_result.get("summary", "")
            lead_data["linkedin_searched"] = roles_result.get("linkedin_searched", False)
            lead_data["stages"]["roles"] = "completed"
            
            if self.state:
                self.state.complete_stage("roles", roles_result)
                
        except Exception as e:
            if self.state:
                self.state.fail_stage("roles", str(e))
            raise
        
        if self.progress:
            self.progress.update("roles", "completed", roles_result)
        
        accepted_people = [p for p in lead_data["people"] if p.get("status") == "accepted"]
        
        # ═══════════════════════════════════════════════════════════════
        # STAGE 4: ENRICHMENT (Apollo with Memory Context)
        # ═══════════════════════════════════════════════════════════════
        if self.stop_event and self.stop_event.is_set():
            raise KeyboardInterrupt("Analysis stopped by user")

        if self.state:
            self.state.start_stage("enrichment")
        if self.progress:
            self.progress.update("enrichment", "running")
        
        # Get enrichment context from memory
        enrichment_context = None
        if self.context_builder:
            roles_for_context = [
                {"name": p.get("name", ""), "title": p.get("title", "")}
                for p in accepted_people
            ]
            enrichment_context = self.context_builder.build_enrichment_context(
                company_name, roles_for_context
            )
        
        roles_for_enrichment = [
            {
                "name": p.get("name", ""),
                "title": p.get("title", ""), 
                "status": p.get("status", "rejected"),
                "linkedin_url": p.get("linkedin_url", "")
            }
            for p in accepted_people
        ]
        
        company_domain = None
        website = company_result.get("website", "")
        if website:
            domain = website.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
            company_domain = domain
        
        try:
            enrichment_result = enrichment_agent.run(
                company_name=company_result.get("name", company_name),
                roles=roles_for_enrichment,
                company_domain=company_domain,
                stop_event=self.stop_event
            )
            lead_data["contacts"] = enrichment_result.get("contacts", [])
            lead_data["enrichment_note"] = enrichment_result.get("note", "")
            lead_data["stages"]["enrichment"] = "completed"
            
            if self.state:
                self.state.complete_stage("enrichment", enrichment_result)
            
            # Log success pattern to memory
            if self.memory and lead_data["contacts"]:
                self.memory.remember_pattern("enrichment", {
                    "hint": f"Successfully enriched {len(lead_data['contacts'])} contacts for {company_name}"
                }, success_rate=1.0)
                
        except Exception as e:
            if self.state:
                self.state.fail_stage("enrichment", str(e))
            if self.memory:
                self.memory.remember_failure(
                    context=f"Enrichment for {company_name}",
                    error=str(e),
                    recovery="Try with different API or manual search"
                )
            raise
        
        if self.progress:
            self.progress.update("enrichment", "completed", enrichment_result)
        
        # ═══════════════════════════════════════════════════════════════
        # STAGE 5: VERIFICATION (Final Scoring with Memory)
        # ═══════════════════════════════════════════════════════════════
        if self.state:
            self.state.start_stage("verification")
        if self.progress:
            self.progress.update("verification", "running")
        
        # Get verification context
        verification_context = None
        if self.context_builder:
            verification_context = self.context_builder.build_verification_context(
                company_result, lead_data
            )
        
        roles_for_verification = [
            {
                "title": p.get("title", ""),
                "status": p.get("status", "rejected"),
                "decision_power": p.get("decision_power", 0),
                "name": p.get("name", "")
            }
            for p in lead_data["people"]
        ]
        
        try:
            verification_result = verification_agent.run(
                company=company_result,
                roles=roles_for_verification,
                contacts=lead_data["contacts"],
                stop_event=self.stop_event
            )
            
            lead_data["status"] = verification_result.get("status", "rejected")
            lead_data["confidence_score"] = verification_result.get("confidence_score", 0.0)
            lead_data["reason"] = verification_result.get("reason", "")
            lead_data["summary"] = verification_result.get("summary", "")
            lead_data["recommended_action"] = verification_result.get("recommended_action", "")
            lead_data["stages"]["verification"] = "completed"
            
            if self.state:
                self.state.complete_stage("verification", verification_result)
                
        except Exception as e:
            if self.state:
                self.state.fail_stage("verification", str(e))
            raise
        
        if self.progress:
            self.progress.update("verification", "completed", verification_result)
        
        # Save to database
        db.save_lead(lead_data)
        
        return lead_data
    
    def _resume_pipeline(self, execution_id: str) -> dict:
        """
        Resume a paused or failed execution from checkpoint.
        
        SIMPLIFIED APPROACH:
        1. Find last completed stage
        2. Restore ONLY completed stage data (not partial/in-progress)
        3. Re-run everything from the next stage
        """
        if not self.state:
            return {"error": "State management not available", "status": "failed"}
        
        try:
            resume_info = self.state.resume_execution(execution_id)
        except Exception as e:
            print(f"\n❌ Failed to load checkpoint: {e}\n")
            return {"error": f"Failed to resume: {e}", "status": "failed"}
        
        execution = resume_info["execution"]
        
        # Get original input
        company_name = execution["input"].get("company", "")
        user_roles = execution["input"].get("roles", [])
        
        if not company_name:
            print("\n❌ No company name in checkpoint\n")
            return {"error": "No company in checkpoint", "status": "failed"}
        
        print(f"\n🔄 Resuming {company_name}...")
        
        # Find last COMPLETED stage (ignore in_progress/failed)
        last_completed_index = -1
        completed_stages = {}
        
        for i, stage_name in enumerate(self.state.STAGES):
            stage_state = execution["stages"].get(stage_name, {})
            if stage_state.get("status") == "completed" and stage_state.get("result"):
                last_completed_index = i
                completed_stages[stage_name] = stage_state.get("result")
        
        # Start from the next stage after last completed
        start_index = last_completed_index + 1
        
        if start_index >= len(self.state.STAGES):
            print(" ✓ All stages already completed!")
            # Return the completed result
            lead_data = {"id": execution["id"], "status": "completed"}
            # Restore all completed stage results
            if "discovery" in completed_stages:
                lead_data["company"] = completed_stages["discovery"]
            if "structure" in completed_stages:
                lead_data["structure"] = completed_stages["structure"]
            if "roles" in completed_stages:
                roles_result = completed_stages["roles"]
                lead_data["people"] = roles_result.get("people", [])
            if "enrichment" in completed_stages:
                enrich_result = completed_stages["enrichment"]
                lead_data["contacts"] = enrich_result.get("contacts", [])
            if "verification" in completed_stages:
                verif_result = completed_stages["verification"]
                lead_data["status"] = verif_result.get("status", "verified")
                lead_data["confidence_score"] = verif_result.get("confidence_score", 0)
                lead_data["summary"] = verif_result.get("summary", "")
            return lead_data
        
        print(f"   Last completed: {self.state.STAGES[last_completed_index] if last_completed_index >= 0 else 'none'}")
        print(f"   Resuming from: {self.state.STAGES[start_index]}\n")
        
        # Build a fresh lead_data with ONLY completed stage results
        lead_data = {
            "id": execution["id"],
            "input": company_name,
            "status": "analyzing",
            "stages": {}
        }
        
        # Restore completed stages
        company_result = None
        structure_result = None
        
        if "discovery" in completed_stages:
            company_result = completed_stages["discovery"]
            lead_data["company"] = company_result
            lead_data["stages"]["discovery"] = "completed"
            print(f"   ✓ Restored company: {company_result.get('name', company_name)}")
        
        if "structure" in completed_stages:
            structure_result = completed_stages["structure"]
            lead_data["structure"] = structure_result
            lead_data["stages"]["structure"] = "completed"
            print(f"   ✓ Restored structure")
        
        if "roles" in completed_stages:
            roles_result = completed_stages["roles"]
            lead_data["people"] = roles_result.get("people", [])
            lead_data["people_summary"] = roles_result.get("summary", "")
            lead_data["linkedin_searched"] = roles_result.get("linkedin_searched", False)
            lead_data["stages"]["roles"] = "completed"
            print(f"   ✓ Restored {len(lead_data['people'])} people")
        
        if "enrichment" in completed_stages:
            enrichment_result = completed_stages["enrichment"]
            lead_data["contacts"] = enrichment_result.get("contacts", [])
            lead_data["enrichment_note"] = enrichment_result.get("note", "")
            lead_data["stages"]["enrichment"] = "completed"
            print(f"   ✓ Restored {len(lead_data['contacts'])} contacts")
        
        print()
        
        # Now re-run the complete pipeline from start_index onwards
        # This is simpler and more reliable than trying to resume mid-stage
        try:
            # Run remaining stages
            for i in range(start_index, len(self.state.STAGES)):
                stage = self.state.STAGES[i]
                
                if stage == "discovery":
                    self.state.start_stage("discovery")
                    if self.progress:
                        self.progress.update("discovery", "running", {"company": company_name})
                    
                    company_result = discovery_agent.run(company_name, use_web_search=True, stop_event=self.stop_event)
                    lead_data["company"] = company_result
                    lead_data["stages"]["discovery"] = "completed"
                    self.state.complete_stage("discovery", company_result)
                    
                    if self.progress:
                        self.progress.update("discovery", "completed", company_result)
                    
                    if company_result.get("status") == "rejected":
                        lead_data["status"] = "rejected"
                        lead_data["reason"] = company_result.get("reason", "")
                        lead_data["confidence_score"] = 0.0
                        db.save_lead(lead_data)
                        return lead_data
                
                elif stage == "structure":
                    self.state.start_stage("structure")
                    if self.progress:
                        self.progress.update("structure", "running")
                    
                    structure_result = structure_agent.run(company_result or lead_data.get("company", {}), stop_event=self.stop_event)
                    lead_data["structure"] = structure_result
                    lead_data["stages"]["structure"] = "completed"
                    self.state.complete_stage("structure", structure_result)
                    
                    if self.progress:
                        self.progress.update("structure", "completed", structure_result)
                
                elif stage == "roles":
                    self.state.start_stage("roles")
                    if self.progress:
                        self.progress.update("roles", "running")
                    
                    company_data = company_result or lead_data.get("company", {})
                    
                    # Extract domain for Snov fallback
                    company_domain_for_search = None
                    website = company_data.get("website", "")
                    if website:
                         company_domain_for_search = website.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
                    
                    roles_result = role_agent.run(
                        company_name=company_data.get("name", company_name),
                        company_size=company_data.get("size", "medium"),
                        structure_data=structure_result or lead_data.get("structure", {}),
                        company_domain=company_domain_for_search,
                        stop_event=self.stop_event
                    )
                    lead_data["people"] = roles_result.get("people", [])
                    lead_data["people_summary"] = roles_result.get("summary", "")
                    lead_data["linkedin_searched"] = roles_result.get("linkedin_searched", False)
                    lead_data["stages"]["roles"] = "completed"
                    self.state.complete_stage("roles", roles_result)
                    
                    if self.progress:
                        self.progress.update("roles", "completed", roles_result)
                
                elif stage == "enrichment":
                    self.state.start_stage("enrichment")
                    if self.progress:
                        self.progress.update("enrichment", "running")
                    
                    accepted_people = [p for p in lead_data.get("people", []) if p.get("status") == "accepted"]
                    roles_for_enrichment = [
                        {
                            "name": p.get("name", ""),
                            "title": p.get("title", ""),
                            "status": p.get("status", "rejected"),
                            "linkedin_url": p.get("linkedin_url", "")
                        }
                        for p in accepted_people
                    ]
                    
                    company_data = company_result or lead_data.get("company", {})
                    company_domain = None
                    website = company_data.get("website", "")
                    if website:
                        domain = website.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
                        company_domain = domain
                    
                    enrichment_result = enrichment_agent.run(
                        company_name=company_data.get("name", company_name),
                        roles=roles_for_enrichment,
                        company_domain=company_domain,
                        stop_event=self.stop_event
                    )
                    lead_data["contacts"] = enrichment_result.get("contacts", [])
                    lead_data["enrichment_note"] = enrichment_result.get("note", "")
                    lead_data["stages"]["enrichment"] = "completed"
                    self.state.complete_stage("enrichment", enrichment_result)
                    
                    if self.progress:
                        self.progress.update("enrichment", "completed", enrichment_result)
                
                elif stage == "verification":
                    self.state.start_stage("verification")
                    if self.progress:
                        self.progress.update("verification", "running")
                    
                    roles_for_verification = [
                        {
                            "title": p.get("title", ""),
                            "status": p.get("status", "rejected"),
                            "decision_power": p.get("decision_power", 0),
                            "name": p.get("name", "")
                        }
                        for p in lead_data.get("people", [])
                    ]
                    
                    verification_result = verification_agent.run(
                        company=company_result or lead_data.get("company", {}),
                        roles=roles_for_verification,
                        contacts=lead_data.get("contacts", []),
                        stop_event=self.stop_event
                    )
                    
                    lead_data["status"] = verification_result.get("status", "rejected")
                    lead_data["confidence_score"] = verification_result.get("confidence_score", 0.0)
                    lead_data["reason"] = verification_result.get("reason", "")
                    lead_data["summary"] = verification_result.get("summary", "")
                    lead_data["recommended_action"] = verification_result.get("recommended_action", "")
                    lead_data["stages"]["verification"] = "completed"
                    self.state.complete_stage("verification", verification_result)
                    
                    if self.progress:
                        self.progress.update("verification", "completed", verification_result)
            
            # Complete execution
            self.state.complete_execution(lead_data)
            self.state._current_execution = None
            self._learn_from_execution(lead_data)
            
            # Save to database
            db.save_lead(lead_data)
            
        except KeyboardInterrupt:
            print("\n⏸️  Paused. Use 'resume' to continue.\n")
            if self.state:
                self.state.pause_execution("User interrupted during resume")
            lead_data["status"] = "paused"
            lead_data["can_resume"] = True
            lead_data["id"] = execution["id"]
            
        except Exception as e:
            print(f"\n❌ Error during resume: {e}\n")
            if self.memory:
                self.memory.remember_failure(
                    context=f"Resume for {company_name}",
                    error=str(e),
                    recovery=None
                )
            lead_data["status"] = "failed"
            lead_data["error"] = str(e)
        
        return lead_data
    
    def _learn_from_execution(self, lead_data: dict):
        """Extract and store learnings from completed execution."""
        if not self.memory:
            return
        
        company_name = lead_data.get("company", {}).get("name", "")
        status = lead_data.get("status", "unknown")
        
        # Remember company outcome
        if company_name:
            outcome = "success" if status == "verified" else "failure"
            self.memory.remember_company(company_name, lead_data.get("company", {}), outcome)
        
        # Extract and store learnings
        if self.context_builder:
            learnings = self.context_builder.extract_learnings(lead_data)
            for learning in learnings:
                if learning["type"] == "pattern":
                    self.memory.remember_pattern(
                        learning["category"],
                        learning["pattern"]
                    )
                elif learning["type"] == "insight":
                    self.memory.add_insight(
                        learning["insight"],
                        learning["category"]
                    )
        
        # Log completion
        self.memory.add_to_short_term("execution_complete", {
            "lead_id": lead_data.get("id"),
            "status": status,
            "confidence": lead_data.get("confidence_score", 0)
        }, importance=8)
    
    def get_resumable(self) -> list:
        """Get list of executions that can be resumed."""
        if not self.state:
            return []
        return self.state.get_resumable_executions()
    
    def get_memory_stats(self) -> dict:
        """Get memory statistics."""
        if not self.memory:
            return {"error": "Memory not available"}
        return self.memory.get_stats()


# ═══════════════════════════════════════════════════════════════════════════
# BACKWARDS COMPATIBLE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def run_pipeline(
    user_input: str,
    progress: Optional[WorkflowProgress] = None
) -> dict:
    """
    Run the full lead discovery pipeline.
    Backwards compatible wrapper for LongRunningWorkflow.
    
    NEW FLOW:
    1. Discovery: Web search for company info (with memory)
    2. Structure: Map decision-makers by company size
    3. Role Discovery: LinkedIn search for actual people
    4. Enrichment: Apollo for verified contacts (with caching)
    5. Verification: Final scoring (with patterns)
    """
    workflow = LongRunningWorkflow(progress)
    return workflow.run_pipeline(user_input)


def resume_pipeline(
    execution_id: str,
    progress: Optional[WorkflowProgress] = None
) -> dict:
    """Resume a paused or failed pipeline execution."""
    workflow = LongRunningWorkflow(progress)
    return workflow.run_pipeline("", resume_id=execution_id)


def get_resumable_executions() -> list:
    """Get list of executions that can be resumed."""
    workflow = LongRunningWorkflow()
    return workflow.get_resumable()


def get_memory_stats() -> dict:
    """Get memory usage statistics."""
    workflow = LongRunningWorkflow()
    return workflow.get_memory_stats()


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
