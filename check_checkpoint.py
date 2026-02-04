import json

# Load checkpoints
with open('data/checkpoints.json', 'r') as f:
    data = json.load(f)

# Find execution c776d88f
exec_data = None
for v in data.values():
    if v['id'] == 'c776d88f':
        exec_data = v
        break

if exec_data:
    print("Execution c776d88f (Hindustan Petroleum Limited):")
    print(f"  Status: {exec_data['status']}")
    print(f"  Current stage: {exec_data.get('current_stage')}")
    print()
    
    discovery = exec_data['stages'].get('discovery', {})
    print(f"Discovery stage:")
    print(f"  Status: {discovery.get('status')}")
    print(f"  Has result key: {'result' in discovery}")
    
    result = discovery.get('result')
    print(f"  Result type: {type(result)}")
    print(f"  Result value: {result}")
    
    if result:
        if isinstance(result, dict):
            print(f"  Company name: {result.get('name', 'NOT FOUND')}")
            print(f"  Industry: {result.get('industry', 'NOT FOUND')}")
        else:
            print(f"  ERROR: Result is not a dict!")
else:
    print("Execution not found!")
