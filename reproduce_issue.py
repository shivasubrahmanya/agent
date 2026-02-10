
import os
from agents import lead_finder_agent

def test_heuristic():
    inputs = ["Bosch", "find startups", "list of AI companies", "Microsoft"]
    for inp in inputs:
        result = lead_finder_agent.run(inp)
        print(f"Input: '{inp}' -> is_search: {result.get('is_search')}, message: {result.get('message')}")

if __name__ == "__main__":
    test_heuristic()
