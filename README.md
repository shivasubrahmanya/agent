# B2B Lead Discovery Agent

Terminal-based B2B Lead Discovery Agent powered by Groq LLM + Apollo.io.

**Now with Long-Running Agent capabilities:** Persistent memory, checkpointing, and auto-recovery.

## Features

- **Web Search**: Searches company info, news, LinkedIn
- **Company Structure**: Maps decision-makers by company size
- **LinkedIn Discovery**: Finds people at target companies
- **Apollo Enrichment**: Gets verified contact data (emails, phones)
- **Lead Scoring**: Validates and scores leads

### 🆕 Long-Running Agent Features

- **Persistent Memory**: Remembers past analyses across sessions
- **Checkpointing**: Saves state at each pipeline stage
- **Resume**: Continue interrupted analyses from where they stopped
- **Learning**: Agent improves from past successes and failures
- **Context Injection**: Uses past knowledge to improve accuracy

## Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure API keys** - Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
   Add your keys:
   - GROQ_API_KEY (free at console.groq.com)
   - APOLLO_API_KEY (free at apollo.io - select `organization_top_people` API)

3. **Run the agent**:
   ```bash
   python agent.py
   ```

## Usage

```
> analyze Microsoft
> analyze TCS, Roles: CEO, VP Sales
> enrich Satya Nadella at Microsoft
> status              # View memory stats
> learn               # View learned patterns
> resume              # Resume interrupted analysis
> forget Microsoft    # Clear memory for a company
> history
> export
```

## Project Structure

```
├── agent.py              # Main CLI interface
├── workflow.py           # Pipeline orchestrator (with checkpointing)
├── agents/               # Agent modules
│   ├── discovery_agent.py
│   ├── structure_agent.py
│   ├── role_agent.py
│   ├── enrichment_agent.py
│   └── verification_agent.py
├── memory/               # Long-running agent memory
│   ├── memory_manager.py    # 3-tier memory system
│   ├── state_manager.py     # Checkpointing & resume
│   └── context_builder.py   # Context engineering
├── services/             # External services
│   ├── apollo_client.py
│   ├── linkedin_search.py
│   └── web_search.py
├── database.py           # JSON storage
└── data/
    ├── leads.json        # Saved leads
    ├── memory.json       # Long-term memory
    └── checkpoints.json  # Execution checkpoints
```

