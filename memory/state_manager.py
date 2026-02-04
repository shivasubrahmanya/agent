"""
State Manager for Long-Running Agent
Handles checkpointing, state persistence, and execution recovery

Enables:
- Checkpoint creation at each pipeline stage
- Resume from last checkpoint on failure/interruption
- Execution history tracking
- Auto-retry with re-planning
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from pathlib import Path
from enum import Enum
import traceback


DATA_DIR = Path(__file__).parent.parent / "data"


class ExecutionStatus(Enum):
    """Status of a pipeline execution."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StageStatus(Enum):
    """Status of an individual stage."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class StateManager:
    """
    Manages pipeline state, checkpointing, and execution recovery.
    
    Implements:
    - State serialization/deserialization
    - Checkpoint creation at each stage
    - Resume from checkpoint capability
    - Execution history with timestamps
    - Failure handling with retry logic
    """
    
    # Pipeline stages in order
    STAGES = ["discovery", "structure", "roles", "enrichment", "verification"]
    MAX_RETRIES = 3
    
    def __init__(self):
        """Initialize state manager."""
        DATA_DIR.mkdir(exist_ok=True)
        
        self._checkpoints_path = DATA_DIR / "checkpoints.json"
        self._history_path = DATA_DIR / "execution_history.json"
        
        self._checkpoints = self._load_json(self._checkpoints_path, {})
        self._history = self._load_json(self._history_path, [])
        
        # Current execution state (in-memory)
        self._current_execution: Optional[Dict[str, Any]] = None
    
    def _load_json(self, path: Path, default: Any) -> Any:
        """Load JSON file or return default."""
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return default
        return default
    
    def _save_checkpoints(self):
        """Persist checkpoints to disk."""
        with open(self._checkpoints_path, "w", encoding="utf-8") as f:
            json.dump(self._checkpoints, f, indent=2, ensure_ascii=False)
    
    def _save_history(self):
        """Persist execution history to disk."""
        with open(self._history_path, "w", encoding="utf-8") as f:
            json.dump(self._history, f, indent=2, ensure_ascii=False)
    
    # ═══════════════════════════════════════════════════════════════
    # EXECUTION MANAGEMENT
    # ═══════════════════════════════════════════════════════════════
    
    def start_execution(self, execution_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Start a new pipeline execution.
        
        Args:
            execution_id: Unique identifier for this execution
            input_data: Initial input data
            
        Returns:
            Execution state dict
        """
        now = datetime.now().isoformat()
        
        self._current_execution = {
            "id": execution_id,
            "status": ExecutionStatus.RUNNING.value,
            "input": input_data,
            "stages": {stage: {
                "status": StageStatus.NOT_STARTED.value,
                "started_at": None,
                "completed_at": None,
                "result": None,
                "error": None,
                "retries": 0
            } for stage in self.STAGES},
            "current_stage": None,
            "current_stage_index": -1,
            "created_at": now,
            "updated_at": now,
            "completed_at": None,
            "error": None
        }
        
        # Save initial checkpoint
        self._checkpoints[execution_id] = self._current_execution.copy()
        self._save_checkpoints()
        
        # Log to history
        self._log_event("execution_started", {
            "execution_id": execution_id,
            "input": input_data
        })
        
        return self._current_execution
    
    def get_current_execution(self) -> Optional[Dict[str, Any]]:
        """Get the current execution state."""
        return self._current_execution
    
    def get_all_executions(self) -> Dict[str, Dict[str, Any]]:
        """Get all stored executions."""
        return self._checkpoints
    
    def get_resumable_executions(self) -> List[Dict[str, Any]]:
        """Get list of executions that can be resumed."""
        resumable = []
        for exec_id, execution in self._checkpoints.items():
            status = execution.get("status")
            # Include CANCELLED so interrupted executions can be resumed
            if status in [ExecutionStatus.RUNNING.value, 
                         ExecutionStatus.PAUSED.value,
                         ExecutionStatus.FAILED.value,
                         ExecutionStatus.CANCELLED.value]:
                resumable.append(execution)
        return resumable
    
    # ═══════════════════════════════════════════════════════════════
    # STAGE MANAGEMENT
    # ═══════════════════════════════════════════════════════════════
    
    def start_stage(self, stage: str) -> Dict[str, Any]:
        """
        Mark a stage as started.
        
        Args:
            stage: Stage name
            
        Returns:
            Updated stage state
        """
        if not self._current_execution:
            raise RuntimeError("No active execution")
        
        if stage not in self.STAGES:
            raise ValueError(f"Unknown stage: {stage}")
        
        now = datetime.now().isoformat()
        stage_state = self._current_execution["stages"][stage]
        stage_state["status"] = StageStatus.IN_PROGRESS.value
        stage_state["started_at"] = now
        
        self._current_execution["current_stage"] = stage
        self._current_execution["current_stage_index"] = self.STAGES.index(stage)
        self._current_execution["updated_at"] = now
        
        # Checkpoint
        self._checkpoint()
        
        self._log_event("stage_started", {
            "execution_id": self._current_execution["id"],
            "stage": stage
        })
        
        return stage_state
    
    def complete_stage(self, stage: str, result: Any) -> Dict[str, Any]:
        """
        Mark a stage as completed with its result.
        
        Args:
            stage: Stage name
            result: Stage output
            
        Returns:
            Updated stage state
        """
        if not self._current_execution:
            raise RuntimeError("No active execution")
        
        now = datetime.now().isoformat()
        stage_state = self._current_execution["stages"][stage]
        stage_state["status"] = StageStatus.COMPLETED.value
        stage_state["completed_at"] = now
        stage_state["result"] = result
        
        self._current_execution["updated_at"] = now
        
        # Checkpoint after successful completion
        self._checkpoint()
        
        self._log_event("stage_completed", {
            "execution_id": self._current_execution["id"],
            "stage": stage,
            "success": True
        })
        
        return stage_state
    
    def fail_stage(self, stage: str, error: str, 
                   can_retry: bool = True) -> Dict[str, Any]:
        """
        Mark a stage as failed.
        
        Args:
            stage: Stage name
            error: Error message
            can_retry: Whether this stage can be retried
            
        Returns:
            Updated stage state
        """
        if not self._current_execution:
            raise RuntimeError("No active execution")
        
        now = datetime.now().isoformat()
        stage_state = self._current_execution["stages"][stage]
        stage_state["status"] = StageStatus.FAILED.value
        stage_state["error"] = error
        stage_state["retries"] += 1
        
        self._current_execution["updated_at"] = now
        
        # Check if we should pause for manual intervention
        if stage_state["retries"] >= self.MAX_RETRIES or not can_retry:
            self._current_execution["status"] = ExecutionStatus.PAUSED.value
            self._current_execution["error"] = f"Stage '{stage}' failed after {stage_state['retries']} retries: {error}"
        
        self._checkpoint()
        
        self._log_event("stage_failed", {
            "execution_id": self._current_execution["id"],
            "stage": stage,
            "error": error,
            "retry_count": stage_state["retries"]
        })
        
        return stage_state
    
    def skip_stage(self, stage: str, reason: str) -> Dict[str, Any]:
        """Mark a stage as skipped."""
        if not self._current_execution:
            raise RuntimeError("No active execution")
        
        now = datetime.now().isoformat()
        stage_state = self._current_execution["stages"][stage]
        stage_state["status"] = StageStatus.SKIPPED.value
        stage_state["error"] = reason
        
        self._current_execution["updated_at"] = now
        self._checkpoint()
        
        return stage_state
    
    # ═══════════════════════════════════════════════════════════════
    # CHECKPOINT & RESUME
    # ═══════════════════════════════════════════════════════════════
    
    def _checkpoint(self):
        """Create a checkpoint of current state."""
        if self._current_execution:
            exec_id = self._current_execution["id"]
            self._checkpoints[exec_id] = self._current_execution.copy()
            self._save_checkpoints()
    
    def can_resume(self, execution_id: str) -> bool:
        """Check if an execution can be resumed."""
        if execution_id not in self._checkpoints:
            return False
        
        execution = self._checkpoints[execution_id]
        return execution["status"] in [
            ExecutionStatus.RUNNING.value,
            ExecutionStatus.PAUSED.value,
            ExecutionStatus.FAILED.value,
            ExecutionStatus.CANCELLED.value  # Also allow resuming cancelled
        ]
    
    def resume_execution(self, execution_id: str) -> Dict[str, Any]:
        """
        Resume a paused or failed execution.
        
        Args:
            execution_id: Execution to resume
            
        Returns:
            Execution state with resume point info
        """
        if execution_id not in self._checkpoints:
            raise ValueError(f"Execution {execution_id} not found")
        
        execution = self._checkpoints[execution_id]
        
        if execution["status"] == ExecutionStatus.COMPLETED.value:
            raise ValueError(f"Execution {execution_id} already completed")
        
        # Clear any existing current execution first
        self._current_execution = None
        
        # Load as current execution - use deep copy to preserve nested stage results
        import copy
        self._current_execution = copy.deepcopy(execution)
        self._current_execution["status"] = ExecutionStatus.RUNNING.value
        self._current_execution["updated_at"] = datetime.now().isoformat()
        
        # Find resume point
        resume_stage = None
        for stage in self.STAGES:
            stage_state = self._current_execution["stages"][stage]
            if stage_state["status"] in [StageStatus.NOT_STARTED.value,
                                         StageStatus.IN_PROGRESS.value,
                                         StageStatus.FAILED.value]:
                resume_stage = stage
                break
        
        self._log_event("execution_resumed", {
            "execution_id": execution_id,
            "resume_stage": resume_stage
        })
        
        return {
            "execution": self._current_execution,
            "resume_stage": resume_stage,
            "resume_stage_index": self.STAGES.index(resume_stage) if resume_stage else -1
        }
    
    def get_stage_result(self, stage: str) -> Optional[Any]:
        """Get the result of a completed stage."""
        if not self._current_execution:
            return None
        
        stage_state = self._current_execution["stages"].get(stage)
        if stage_state and stage_state["status"] == StageStatus.COMPLETED.value:
            return stage_state["result"]
        return None
    
    # ═══════════════════════════════════════════════════════════════
    # EXECUTION COMPLETION
    # ═══════════════════════════════════════════════════════════════
    
    def complete_execution(self, final_result: Any) -> Dict[str, Any]:
        """
        Mark execution as completed.
        
        Args:
            final_result: Final pipeline output
            
        Returns:
            Final execution state
        """
        if not self._current_execution:
            raise RuntimeError("No active execution")
        
        now = datetime.now().isoformat()
        self._current_execution["status"] = ExecutionStatus.COMPLETED.value
        self._current_execution["completed_at"] = now
        self._current_execution["updated_at"] = now
        self._current_execution["final_result"] = final_result
        
        self._checkpoint()
        
        self._log_event("execution_completed", {
            "execution_id": self._current_execution["id"],
            "success": True
        })
        
        result = self._current_execution
        self._current_execution = None
        
        return result
    
    def cancel_execution(self, reason: str = None) -> Dict[str, Any]:
        """Cancel the current execution."""
        if not self._current_execution:
            raise RuntimeError("No active execution")
        
        now = datetime.now().isoformat()
        self._current_execution["status"] = ExecutionStatus.CANCELLED.value
        self._current_execution["updated_at"] = now
        self._current_execution["error"] = reason or "Cancelled by user"
        
        self._checkpoint()
        
        self._log_event("execution_cancelled", {
            "execution_id": self._current_execution["id"],
            "reason": reason
        })
        
        result = self._current_execution
        self._current_execution = None
        
        return result
    
    def pause_execution(self, reason: str = None) -> Dict[str, Any]:
        """Pause the current execution (can be resumed later)."""
        if not self._current_execution:
            raise RuntimeError("No active execution")
        
        now = datetime.now().isoformat()
        self._current_execution["status"] = ExecutionStatus.PAUSED.value
        self._current_execution["updated_at"] = now
        self._current_execution["error"] = reason or "Paused by user"
        
        self._checkpoint()
        
        self._log_event("execution_paused", {
            "execution_id": self._current_execution["id"],
            "reason": reason
        })
        
        # Don't clear current execution - keep it for proper checkpointing
        # Return a copy instead
        result = self._current_execution.copy()
        
        return result
    
    # ═══════════════════════════════════════════════════════════════
    # EXECUTION HISTORY
    # ═══════════════════════════════════════════════════════════════
    
    def _log_event(self, event_type: str, data: Dict[str, Any]):
        """Log an event to execution history."""
        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        
        self._history.append(event)
        
        # Keep history manageable
        if len(self._history) > 500:
            self._history = self._history[-500:]
        
        self._save_history()
    
    def get_history(self, execution_id: str = None, 
                    event_type: str = None,
                    n: int = 50) -> List[Dict[str, Any]]:
        """
        Get execution history.
        
        Args:
            execution_id: Filter by execution (optional)
            event_type: Filter by event type (optional)
            n: Number of events to return
            
        Returns:
            List of history events
        """
        events = self._history
        
        if execution_id:
            events = [e for e in events 
                     if e.get("data", {}).get("execution_id") == execution_id]
        
        if event_type:
            events = [e for e in events if e["type"] == event_type]
        
        return events[-n:]
    
    # ═══════════════════════════════════════════════════════════════
    # CLEANUP
    # ═══════════════════════════════════════════════════════════════
    
    def cleanup_old_checkpoints(self, days: int = 7):
        """Remove checkpoints older than specified days."""
        from datetime import timedelta
        
        cutoff = datetime.now() - timedelta(days=days)
        
        to_remove = []
        for exec_id, execution in self._checkpoints.items():
            created = datetime.fromisoformat(execution.get("created_at", "2000-01-01"))
            if created < cutoff and execution["status"] == ExecutionStatus.COMPLETED.value:
                to_remove.append(exec_id)
        
        for exec_id in to_remove:
            del self._checkpoints[exec_id]
        
        self._save_checkpoints()
        
        return len(to_remove)
    
    def delete_execution(self, execution_id: str) -> bool:
        """Delete a specific execution checkpoint."""
        if execution_id in self._checkpoints:
            del self._checkpoints[execution_id]
            self._save_checkpoints()
            return True
        return False
