# B2B Lead Discovery Agent

Terminal-based B2B Lead Discovery Agent powered by Groq LLM + Apollo.io.

## Features

- **Web Search**: Searches company info, news, LinkedIn
- **Company Structure**: Maps decision-makers by company size
- **LinkedIn Discovery**: Finds people at target companies
- **Apollo Enrichment**: Gets verified contact data (emails, phones)
- **Lead Scoring**: Validates and scores leads

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
> history
> export
```

## Project Structure

```
├── agent.py              # Main CLI interface
├── workflow.py           # Pipeline orchestrator
├── agents/               # Agent modules
│   ├── discovery_agent.py
│   ├── structure_agent.py
│   ├── role_agent.py
│   ├── enrichment_agent.py
│   └── verification_agent.py
├── services/             # External services
│   ├── apollo_client.py
│   ├── linkedin_search.py
│   └── web_search.py
├── database.py           # JSON storage
└── data/leads.json       # Saved leads
```
