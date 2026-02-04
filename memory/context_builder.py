"""
Context Builder for Long-Running Agent
Builds optimized context for each agent by intelligently selecting
and summarizing relevant information from memory.

Implements Context Engineering:
- Selective memory retrieval based on current task
- Context window optimization (token management)
- Summarization for large contexts
- Injection of learnings from past successes/failures
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime


class ContextBuilder:
    """
    Builds optimized context for agent prompts.
    
    Features:
    - Token-aware context construction
    - Relevance-based memory selection
    - Automatic summarization
    - Task-specific context injection
    """
    
    # Approximate token limits (characters / 4)
    MAX_CONTEXT_TOKENS = 2000
    MAX_CONTEXT_CHARS = 8000
    
    def __init__(self, memory_manager):
        """
        Initialize context builder.
        
        Args:
            memory_manager: MemoryManager instance for memory access
        """
        self.memory = memory_manager
    
    def build_discovery_context(self, company_name: str) -> str:
        """
        Build context for company discovery agent.
        
        Includes:
        - Previous analysis of this company (if any)
        - Similar company patterns
        - Past failures with similar companies
        
        Args:
            company_name: Company being analyzed
            
        Returns:
            Context string for injection into prompt
        """
        context_parts = []
        
        # Check for previous analysis
        prev = self.memory.recall_company(company_name)
        if prev:
            context_parts.append(
                f"[PREVIOUS ANALYSIS] This company was analyzed before:\n"
                f"  Outcome: {prev.get('outcome', 'unknown')}\n"
                f"  Last analyzed: {prev.get('analyzed_at', 'unknown')}\n"
                f"  Times analyzed: {prev.get('times_analyzed', 1)}"
            )
            
            # Include key findings if outcome was successful
            if prev.get("outcome") == "success":
                data = prev.get("data", {})
                if data.get("industry"):
                    context_parts.append(f"  Known industry: {data['industry']}")
                if data.get("size"):
                    context_parts.append(f"  Known size: {data['size']}")
        
        # Get relevant patterns
        patterns = self.memory.get_best_patterns("discovery", n=2)
        if patterns:
            pattern_hints = []
            for p in patterns:
                if p.get("success_rate", 0) > 0.7:
                    pattern_hints.append(
                        f"  - {p.get('pattern', {}).get('hint', 'No hint')}"
                    )
            if pattern_hints:
                context_parts.append(
                    "[SUCCESSFUL PATTERNS]\n" + "\n".join(pattern_hints)
                )
        
        # Check for similar failures
        failures = self.memory.get_similar_failures(company_name, n=2)
        if failures:
            failure_hints = []
            for f in failures:
                failure_hints.append(
                    f"  - Context: {f['context'][:50]}... Error: {f['error'][:50]}..."
                )
            context_parts.append(
                "[PAST FAILURES TO AVOID]\n" + "\n".join(failure_hints)
            )
        
        # Get recent relevant events
        recent = self.memory.get_recent_context(n=3, event_type="decision")
        if recent:
            decisions = []
            for event in recent:
                data = event.get("data", {})
                if data.get("summary"):
                    decisions.append(f"  - {data['summary'][:100]}")
            if decisions:
                context_parts.append(
                    "[RECENT DECISIONS]\n" + "\n".join(decisions)
                )
        
        return self._truncate_context("\n\n".join(context_parts))
    
    def build_enrichment_context(self, company_name: str, 
                                  roles: List[Dict]) -> str:
        """
        Build context for enrichment agent.
        
        Includes:
        - Cached contact data from memory
        - Successful enrichment patterns
        - API failure patterns to avoid
        
        Args:
            company_name: Company being enriched
            roles: Roles to enrich
            
        Returns:
            Context string for injection into prompt
        """
        context_parts = []
        
        # Check for cached company data
        prev = self.memory.recall_company(company_name)
        if prev and prev.get("data", {}).get("contacts"):
            contacts = prev["data"]["contacts"]
            context_parts.append(
                f"[CACHED CONTACTS] Found {len(contacts)} cached contacts for this company.\n"
                f"Consider using cached data if still valid."
            )
        
        # Get enrichment patterns
        patterns = self.memory.get_best_patterns("enrichment", n=2)
        if patterns:
            pattern_hints = []
            for p in patterns:
                hint = p.get("pattern", {}).get("hint", "")
                if hint:
                    pattern_hints.append(f"  - {hint}")
            if pattern_hints:
                context_parts.append(
                    "[ENRICHMENT TIPS]\n" + "\n".join(pattern_hints)
                )
        
        # Check for API failures
        api_failures = self.memory.get_similar_failures("apollo", n=2)
        api_failures += self.memory.get_similar_failures("snov", n=2)
        if api_failures:
            failure_hints = []
            for f in api_failures[:3]:
                if f.get("recovery"):
                    failure_hints.append(
                        f"  - Issue: {f['error'][:40]}... Recovery: {f['recovery'][:40]}..."
                    )
            if failure_hints:
                context_parts.append(
                    "[API ISSUES & RECOVERIES]\n" + "\n".join(failure_hints)
                )
        
        return self._truncate_context("\n\n".join(context_parts))
    
    def build_verification_context(self, company_data: Dict,
                                    lead_data: Dict) -> str:
        """
        Build context for verification agent.
        
        Includes:
        - Historical scoring patterns
        - Similar lead outcomes
        - Verification insights
        
        Args:
            company_data: Company information
            lead_data: Current lead data
            
        Returns:
            Context string for injection into prompt
        """
        context_parts = []
        
        # Get verification patterns
        patterns = self.memory.get_best_patterns("verification", n=2)
        if patterns:
            pattern_hints = []
            for p in patterns:
                pattern = p.get("pattern", {})
                if pattern.get("score_adjustment"):
                    pattern_hints.append(
                        f"  - {pattern.get('condition', 'N/A')}: {pattern['score_adjustment']}"
                    )
            if pattern_hints:
                context_parts.append(
                    "[SCORING ADJUSTMENTS LEARNED]\n" + "\n".join(pattern_hints)
                )
        
        # Check company history
        company_name = company_data.get("name", "")
        if company_name:
            prev = self.memory.recall_company(company_name)
            if prev:
                outcome = prev.get("outcome", "unknown")
                context_parts.append(
                    f"[HISTORICAL OUTCOME] Previous analysis: {outcome}"
                )
        
        # Get insights
        insights = [i for i in self.memory._long_term.get("insights", [])
                   if i.get("category") == "verification"][-3:]
        if insights:
            insight_text = [f"  - {i['insight'][:80]}" for i in insights]
            context_parts.append(
                "[VERIFICATION INSIGHTS]\n" + "\n".join(insight_text)
            )
        
        return self._truncate_context("\n\n".join(context_parts))
    
    def build_general_context(self, task_type: str, 
                              current_data: Dict = None) -> str:
        """
        Build general context for any task.
        
        Args:
            task_type: Type of task being performed
            current_data: Current task data
            
        Returns:
            Context string
        """
        context_parts = []
        
        # Memory stats
        stats = self.memory.get_stats()
        context_parts.append(
            f"[AGENT EXPERIENCE]\n"
            f"  Total analyses: {stats['total_analyses']}\n"
            f"  Successful leads: {stats['successful_leads']}\n"
            f"  Patterns learned: {stats['patterns_learned']}"
        )
        
        # Working memory (current task state)
        working = self.memory.get_all_working()
        if working:
            working_items = [f"  {k}: {str(v)[:50]}" for k, v in working.items()]
            context_parts.append(
                "[CURRENT TASK STATE]\n" + "\n".join(working_items[:5])
            )
        
        # Recent context
        recent = self.memory.get_recent_context(n=5)
        if recent:
            recent_items = []
            for event in recent:
                event_type = event.get("type", "unknown")
                data = event.get("data", {})
                summary = data.get("summary", str(data)[:50])
                recent_items.append(f"  [{event_type}] {summary}")
            context_parts.append(
                "[RECENT ACTIVITY]\n" + "\n".join(recent_items)
            )
        
        return self._truncate_context("\n\n".join(context_parts))
    
    def _truncate_context(self, context: str) -> str:
        """
        Truncate context to fit within token limits.
        
        Args:
            context: Full context string
            
        Returns:
            Truncated context
        """
        if len(context) <= self.MAX_CONTEXT_CHARS:
            return context
        
        # Truncate with indicator
        return context[:self.MAX_CONTEXT_CHARS - 50] + "\n\n[... context truncated ...]"
    
    def summarize_for_memory(self, data: Dict, max_chars: int = 500) -> str:
        """
        Summarize data for efficient memory storage.
        
        Args:
            data: Data to summarize
            max_chars: Maximum characters
            
        Returns:
            Summarized string
        """
        # Convert to string and truncate
        text = json.dumps(data, indent=2, default=str)
        
        if len(text) <= max_chars:
            return text
        
        # Try to extract key fields
        summary_fields = ["name", "status", "industry", "size", "confidence_score", 
                         "reason", "summary"]
        summary = {}
        
        for field in summary_fields:
            if field in data:
                value = data[field]
                if isinstance(value, str) and len(value) > 100:
                    value = value[:100] + "..."
                summary[field] = value
        
        result = json.dumps(summary, indent=2)
        if len(result) > max_chars:
            return result[:max_chars - 20] + "\n... [truncated]"
        
        return result
    
    def extract_learnings(self, execution_result: Dict) -> List[Dict]:
        """
        Extract learnings from a completed execution.
        
        Args:
            execution_result: Complete pipeline result
            
        Returns:
            List of learnings to store
        """
        learnings = []
        
        status = execution_result.get("status", "unknown")
        confidence = execution_result.get("confidence_score", 0)
        
        # Learning from outcome
        if status == "verified" and confidence > 0.8:
            # High-quality lead - extract what worked
            company = execution_result.get("company", {})
            if company.get("industry"):
                learnings.append({
                    "type": "pattern",
                    "category": "discovery",
                    "pattern": {
                        "hint": f"Industry '{company['industry']}' often produces quality leads",
                        "industry": company["industry"]
                    }
                })
        
        elif status == "rejected":
            # Failed lead - learn what to avoid
            reason = execution_result.get("reason", "")
            if reason:
                learnings.append({
                    "type": "insight",
                    "category": "verification",
                    "insight": f"Lead rejected: {reason[:100]}"
                })
        
        # Learn from enrichment success/failure
        contacts = execution_result.get("contacts", [])
        if contacts:
            email_count = len([c for c in contacts if c.get("email")])
            if email_count > 0:
                learnings.append({
                    "type": "pattern",
                    "category": "enrichment",
                    "pattern": {
                        "hint": f"Successfully enriched {email_count} contacts with emails"
                    }
                })
        
        return learnings
