# B2B Lead Discovery Agent

**Modern, Full-Stack B2B Lead Discovery Agent** with React Frontend, FastAPI Backend, and Persistent Memory.

Powered by: **Groq LLM + Apollo.io + Snov.io**.

---

## 🚀 Features

- **Full Stack UI**: Modern React + Vite Dashboard for easy interaction.
- **Enrichment Fallback**: Uses **Apollo.io** for primary contact gathering and **Snov.io (V2)** as a fallback.
- **Deep Discovery**:
    - **Web Search**: Analyzes company growth signals and news.
    - **Structure Mapping**: Identifies key decision-makers by department.
    - **Role Discovery**: Finds actual people via LinkedIn search.
- **Long-Running Agent**:
    - **Persistent Memory**: Remembers past analyses and improves over time.
    - **Checkpointing**: Auto-saves progress; resumes from failure.
    - **Learning**: Records successful patterns and insights.

---

## 🛠️ Setup

### 1. Install Dependencies
**Backend:**
```bash
pip install -r requirements.txt
```
**Frontend:**
```bash
cd frontend
npm install
cd ..
```

### 2. Configure Environment
Create a `.env` file in the root directory:
```bash
GROQ_API_KEY=your_key_here
APOLLO_API_KEY=your_key_here
SNOV_CLIENT_ID=your_id_here
SNOV_CLIENT_SECRET=your_secret_here
```

---

## ⚡ Usage

### Option 1: Full Stack App (Recommended)
Run the backend server, which also serves the compiled frontend.
```bash
python server.py
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser.

### Option 2: Developer Mode (Hot Reload)
Run Frontend and Backend separately for development.

**Terminal 1 (Backend):**
```bash
python server.py
```

**Terminal 2 (Frontend):**
```bash
cd frontend
npm run dev
```
Open **[http://localhost:5173](http://localhost:5173)**.

### Option 3: Terminal CLI
Run the agent directly in the terminal without the UI.
```bash
python agent.py
```
*Commands:* `analyze <Company>`, `enrich <Person> at <Company>`, `resume`, `history`, `export`.

---

## 📂 Project Structure

```
├── server.py             # FastAPI Backend & Socket Server
├── agent.py              # CLI Entry Point
├── workflow.py           # Core Agent Orchestrator
├── frontend/             # React + Vite Application
│   ├── src/components/   # UI Components (ResultCard, LogViewer...)
│   └── dist/             # Compiled Static Assets
├── agents/               # AI Agent Modules
│   ├── discovery_agent.py
│   ├── enrichment_agent.py (Apollo + Snov.io)
│   └── ...
├── services/             # API Clients
│   ├── snov_client.py    # Snov.io Integration
│   └── ...
└── outputs/              # Generated Reports & CSV Exports
```
