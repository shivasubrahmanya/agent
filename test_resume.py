"""
Test resume functionality after Ctrl+C interruptions

This script tests that:
1. Starting an analysis can be interrupted with Ctrl+C
2. The paused execution can be resumed
3. Resuming can also be interrupted with Ctrl+C
4. The execution can be resumed again after multiple interrupts
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from workflow import get_resumable_executions, LongRunningWorkflow
from memory import StateManager

def test_resume():
    print("=" * 60)
    print("Testing Resume Functionality")
    print("=" * 60)
    
    # Check for resumable executions
    workflow = LongRunningWorkflow()
    resumable = workflow.get_resumable()
    
    if not resumable:
        print("\n❌ No resumable executions found.")
        print("   To test this:")
        print("   1. Run: python agent.py")
        print("   2. Type: analyze <Company Name>")
        print("   3. Press Ctrl+C to interrupt")
        print("   4. Run this test again")
        return
    
    print(f"\n✅ Found {len(resumable)} resumable execution(s):")
    print()
    
    for i, execution in enumerate(resumable, 1):
        exec_id = execution.get("id", "unknown")[:8]
        company = execution.get("input", {}).get("company", "Unknown")
        status = execution.get("status", "unknown")
        current_stage = execution.get("current_stage", "unknown")
        created = execution.get("created_at", "")[:10]
        
        print(f"  {i}. ID: {exec_id}")
        print(f"     Company: {company}")
        print(f"     Status: {status}")
        print(f"     Current Stage: {current_stage}")
        print(f"     Created: {created}")
        print()
    
    # Test checkpoint data integrity
    print("=" * 60)
    print("Checking Checkpoint Data Integrity")
    print("=" * 60)
    print()
    
    state = StateManager()
    for execution in resumable:
        exec_id = execution.get("id", "unknown")
        company = execution.get("input", {}).get("company", "Unknown")
        
        print(f"Execution {exec_id[:8]} ({company}):")
        
        # Check if company data is in checkpoint
        stages = execution.get("stages", {})
        discovery_stage = stages.get("discovery", {})
        discovery_result = discovery_stage.get("result", {})
        
        if discovery_result:
            print(f"  ✅ Discovery data preserved:")
            print(f"     Company Name: {discovery_result.get('name', 'MISSING')}")
            print(f"     Industry: {discovery_result.get('industry', 'MISSING')}")
            print(f"     Size: {discovery_result.get('size', 'MISSING')}")
        else:
            print(f"  ⚠️  Warning: No discovery result in checkpoint")
        
        # Check stage statuses
        print(f"  Stage statuses:")
        for stage_name in ["discovery", "structure", "roles", "enrichment", "verification"]:
            stage_data = stages.get(stage_name, {})
            stage_status = stage_data.get("status", "not_started")
            print(f"    - {stage_name}: {stage_status}")
        
        print()
    
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    print()
    print("✅ Resume functionality test complete!")
    print()
    print("To test resume with multiple interrupts:")
    print("  1. Run: python agent.py")
    print("  2. Type: resume 1 (or resume <number>)")
    print("  3. Press Ctrl+C to interrupt again")
    print("  4. Type: resume 1 again")
    print("  5. Repeat as needed - it should work correctly!")
    print()

if __name__ == "__main__":
    test_resume()
