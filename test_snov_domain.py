
from services.snov_client import domain_search
import json

print("Testing Snov.io Domain Search for microsoft.com...")
results = domain_search("microsoft.com", limit=3)
print(json.dumps(results, indent=2))
