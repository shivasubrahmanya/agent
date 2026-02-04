"""
Memory Manager for Long-Running Agent
Implements three-tier memory system: Short-term, Long-term, and Working memory

Memory Architecture:
- Short-term: Current session context, recent actions (cleared on restart)
- Long-term: Persistent storage for past leads, learnings, patterns
- Working: Temporary scratchpad for current task reasoning
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import hashlib


DATA_DIR = Path(__file__).parent.parent / "data"


class MemoryManager:
    """
    Three-tier memory management for long-running agents.
    
    Implements the Plan -> Act -> Observe -> Remember -> Re-Plan cycle
    with persistent storage for cross-session learning.
    """
    
    # Token limits for context management
    MAX_SHORT_TERM_ITEMS = 20
    MAX_WORKING_MEMORY_ITEMS = 10
    MAX_CONTEXT_CHARS = 8000  # Approximate token limit
    
    def __init__(self, session_id: str = None):
        """
        Initialize memory manager.
        
        Args:
            session_id: Unique session identifier (auto-generated if not provided)
        """
        self.session_id = session_id or self._generate_session_id()
        self.session_start = datetime.now().isoformat()
        
        # In-memory stores (cleared on restart)
        self._short_term: List[Dict[str, Any]] = []
        self._working: Dict[str, Any] = {}
        
        # Ensure data directory exists
        DATA_DIR.mkdir(exist_ok=True)
        
        # Load long-term memory from disk
        self._long_term_path = DATA_DIR / "memory.json"
        self._long_term = self._load_long_term()
    
    def _generate_session_id(self) -> str:
        """Generate a unique session ID."""
        timestamp = datetime.now().isoformat()
        return hashlib.md5(timestamp.encode()).hexdigest()[:12]
    
    def _load_long_term(self) -> Dict[str, Any]:
        """Load long-term memory from persistent storage."""
        if self._long_term_path.exists():
            try:
                with open(self._long_term_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return self._init_long_term()
        return self._init_long_term()
    
    def _init_long_term(self) -> Dict[str, Any]:
        """Initialize long-term memory structure."""
        return {
            "companies": {},      # Company analyses and learnings
            "patterns": {},       # Successful patterns discovered
            "failures": [],       # Past failures to avoid
            "insights": [],       # General learnings
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "total_analyses": 0,
                "successful_leads": 0
            }
        }
    
    def _save_long_term(self):
        """Persist long-term memory to disk."""
        with open(self._long_term_path, "w", encoding="utf-8") as f:
            json.dump(self._long_term, f, indent=2, ensure_ascii=False)
    
    # ═══════════════════════════════════════════════════════════════
    # SHORT-TERM MEMORY (Current Session)
    # ═══════════════════════════════════════════════════════════════
    
    def add_to_short_term(self, event_type: str, data: Dict[str, Any], 
                          importance: int = 5):
        """
        Add an event to short-term memory.
        
        Args:
            event_type: Type of event (e.g., 'action', 'observation', 'decision')
            data: Event data
            importance: 1-10 scale, higher = more important (affects retention)
        """
        event = {
            "type": event_type,
            "data": data,
            "importance": importance,
            "timestamp": datetime.now().isoformat(),
            "session_id": self.session_id
        }
        
        self._short_term.append(event)
        
        # Prune old low-importance items if over limit
        if len(self._short_term) > self.MAX_SHORT_TERM_ITEMS:
            self._prune_short_term()
    
    def _prune_short_term(self):
        """Remove low-importance items from short-term memory."""
        # Keep high-importance items longer
        self._short_term.sort(key=lambda x: (-x["importance"], x["timestamp"]))
        self._short_term = self._short_term[:self.MAX_SHORT_TERM_ITEMS]
    
    def get_recent_context(self, n: int = 5, event_type: str = None) -> List[Dict]:
        """
        Get recent events from short-term memory.
        
        Args:
            n: Number of events to retrieve
            event_type: Optional filter by event type
        """
        events = self._short_term
        if event_type:
            events = [e for e in events if e["type"] == event_type]
        return events[-n:]
    
    def clear_short_term(self):
        """Clear short-term memory (e.g., at session end)."""
        self._short_term = []
    
    # ═══════════════════════════════════════════════════════════════
    # LONG-TERM MEMORY (Persistent)
    # ═══════════════════════════════════════════════════════════════
    
    def remember_company(self, company_name: str, data: Dict[str, Any],
                         outcome: str = "neutral"):
        """
        Remember company analysis for future reference.
        
        Args:
            company_name: Company name (normalized)
            data: Company data and analysis
            outcome: 'success', 'failure', or 'neutral'
        """
        normalized_name = company_name.lower().strip()
        
        self._long_term["companies"][normalized_name] = {
            "data": data,
            "outcome": outcome,
            "analyzed_at": datetime.now().isoformat(),
            "times_analyzed": self._long_term["companies"].get(
                normalized_name, {}
            ).get("times_analyzed", 0) + 1
        }
        
        self._long_term["metadata"]["total_analyses"] += 1
        if outcome == "success":
            self._long_term["metadata"]["successful_leads"] += 1
        
        self._save_long_term()
    
    def recall_company(self, company_name: str) -> Optional[Dict[str, Any]]:
        """
        Recall previous analysis of a company.
        
        Args:
            company_name: Company to look up
            
        Returns:
            Previous analysis data or None
        """
        normalized_name = company_name.lower().strip()
        return self._long_term["companies"].get(normalized_name)
    
    def remember_pattern(self, pattern_type: str, pattern: Dict[str, Any],
                         success_rate: float = 1.0):
        """
        Remember a successful pattern for future use.
        
        Args:
            pattern_type: Type of pattern (e.g., 'role_discovery', 'enrichment')
            pattern: The pattern data
            success_rate: How successful this pattern has been (0-1)
        """
        key = f"{pattern_type}:{hashlib.md5(json.dumps(pattern, sort_keys=True).encode()).hexdigest()[:8]}"
        
        existing = self._long_term["patterns"].get(key, {})
        uses = existing.get("uses", 0) + 1
        
        # Update running average of success rate
        old_rate = existing.get("success_rate", success_rate)
        new_rate = (old_rate * (uses - 1) + success_rate) / uses
        
        self._long_term["patterns"][key] = {
            "type": pattern_type,
            "pattern": pattern,
            "success_rate": new_rate,
            "uses": uses,
            "last_used": datetime.now().isoformat()
        }
        
        self._save_long_term()
    
    def get_best_patterns(self, pattern_type: str, n: int = 3) -> List[Dict]:
        """Get the most successful patterns of a given type."""
        patterns = [
            p for p in self._long_term["patterns"].values()
            if p["type"] == pattern_type
        ]
        patterns.sort(key=lambda x: -x["success_rate"])
        return patterns[:n]
    
    def remember_failure(self, context: str, error: str, recovery: str = None):
        """
        Remember a failure to avoid in the future.
        
        Args:
            context: What was being attempted
            error: What went wrong
            recovery: How it was recovered (if at all)
        """
        failure = {
            "context": context,
            "error": error,
            "recovery": recovery,
            "timestamp": datetime.now().isoformat()
        }
        
        self._long_term["failures"].append(failure)
        
        # Keep only recent failures
        if len(self._long_term["failures"]) > 50:
            self._long_term["failures"] = self._long_term["failures"][-50:]
        
        self._save_long_term()
    
    def get_similar_failures(self, context: str, n: int = 3) -> List[Dict]:
        """Get past failures similar to current context."""
        # Simple keyword matching (could be enhanced with embeddings)
        context_words = set(context.lower().split())
        scored = []
        
        for failure in self._long_term["failures"]:
            failure_words = set(failure["context"].lower().split())
            overlap = len(context_words & failure_words)
            if overlap > 0:
                scored.append((overlap, failure))
        
        scored.sort(key=lambda x: -x[0])
        return [f[1] for f in scored[:n]]
    
    def add_insight(self, insight: str, category: str = "general"):
        """Add a general learning/insight."""
        self._long_term["insights"].append({
            "insight": insight,
            "category": category,
            "timestamp": datetime.now().isoformat()
        })
        
        if len(self._long_term["insights"]) > 100:
            self._long_term["insights"] = self._long_term["insights"][-100:]
        
        self._save_long_term()
    
    # ═══════════════════════════════════════════════════════════════
    # WORKING MEMORY (Scratchpad)
    # ═══════════════════════════════════════════════════════════════
    
    def set_working(self, key: str, value: Any):
        """Set a value in working memory."""
        self._working[key] = {
            "value": value,
            "set_at": datetime.now().isoformat()
        }
        
        # Prune if too large
        if len(self._working) > self.MAX_WORKING_MEMORY_ITEMS:
            oldest_key = min(self._working.keys(), 
                           key=lambda k: self._working[k]["set_at"])
            del self._working[oldest_key]
    
    def get_working(self, key: str, default: Any = None) -> Any:
        """Get a value from working memory."""
        item = self._working.get(key)
        return item["value"] if item else default
    
    def clear_working(self):
        """Clear working memory (e.g., after task completion)."""
        self._working = {}
    
    def get_all_working(self) -> Dict[str, Any]:
        """Get all working memory as a dict."""
        return {k: v["value"] for k, v in self._working.items()}
    
    # ═══════════════════════════════════════════════════════════════
    # MEMORY STATISTICS
    # ═══════════════════════════════════════════════════════════════
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        return {
            "session_id": self.session_id,
            "session_start": self.session_start,
            "short_term_items": len(self._short_term),
            "working_memory_items": len(self._working),
            "companies_remembered": len(self._long_term["companies"]),
            "patterns_learned": len(self._long_term["patterns"]),
            "failures_recorded": len(self._long_term["failures"]),
            "insights_gathered": len(self._long_term["insights"]),
            "total_analyses": self._long_term["metadata"]["total_analyses"],
            "successful_leads": self._long_term["metadata"]["successful_leads"]
        }
    
    def forget_company(self, company_name: str) -> bool:
        """Forget a specific company from long-term memory."""
        normalized = company_name.lower().strip()
        if normalized in self._long_term["companies"]:
            del self._long_term["companies"][normalized]
            self._save_long_term()
            return True
        return False
    
    def forget_all(self):
        """Clear all long-term memory (use with caution!)."""
        self._long_term = self._init_long_term()
        self._save_long_term()
        self.clear_short_term()
        self.clear_working()
