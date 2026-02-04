import json

# Load checkpoints
with open('data/checkpoints.json', 'r') as f:
    data = json.load(f)

# Find execution bc619743 (continental)
exec_data = None
for v in data.values():
    if v['id'] == 'bc619743':
        exec_data = v
        break

if exec_data:
    print("=== Execution bc619743 (continental) ===")
    print(f"Status: {exec_data['status']}")
    print(f"Current stage: {exec_data.get('current_stage')}")
    print(f"Current stage index: {exec_data.get('current_stage_index')}")
    print()
    
    print("Input data:")
    print(f"  {exec_data.get('input')}")
    print()
    
    print("Stages:")
    for stage_name in ["discovery", "structure", "roles", "enrichment", "verification"]:
        stage_data = exec_data['stages'].get(stage_name, {})
        stage_status = stage_data.get('status')
        has_result = stage_data.get('result') is not None
        result = stage_data.get('result')
        
        print(f"  {stage_name}:")
        print(f"    Status: {stage_status}")
        print(f"    Has result: {has_result}")
        if has_result and isinstance(result, dict):
            print(f"    Result keys: {list(result.keys())[:5]}")
        print()
else:
    print("Execution not found!")
