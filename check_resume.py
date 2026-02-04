"""Simple diagnostic to check resumable executions"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from memory import StateManager
    
    state = StateManager()
    resumable = state.get_resumable_executions()
    
    print(f"Found {len(resumable)} resumable executions")
    
    for i, exec in enumerate(resumable, 1):
        print(f"\n{i}. Execution ID: {exec['id'][:8]}")
        print(f"   Company: {exec.get('input', {}).get('company', 'Unknown')}")
        print(f"   Status: {exec.get('status')}")
        print(f"   Current Stage: {exec.get('current_stage')}")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
