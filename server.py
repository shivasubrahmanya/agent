
import os
import json
import asyncio
import threading
import sys
from typing import List
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

# Ensure the parent directory is in path or we are running from root
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from workflow import LongRunningWorkflow, WorkflowProgress
from agents import lead_finder_agent

# Load environment variables
load_dotenv()

# Global main event loop reference
main_loop = None

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global main_loop
    try:
        main_loop = asyncio.get_running_loop()
    except RuntimeError:
        main_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(main_loop)
    
    yield
    # Shutdown logic (if needed)

app = FastAPI(lifespan=lifespan)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AgentRequest(BaseModel):
    input: str

def run_workflow_thread(user_input: str, websocket: WebSocket, loop, stop_event=None):
    """Execution thread for the agent with Discovery support"""
    
    # Helper to send WS messages safely
    def send_ws_message(msg_type: str, content: dict):
        msg = {"type": msg_type, **content}
        try:
            future = asyncio.run_coroutine_threadsafe(
                websocket.send_text(json.dumps(msg)), 
                loop
            )
            future.result()
        except Exception as e:
            print(f"Error sending ws update: {e}")

    # Progress callback
    def callback(stage: str, status: str, data: dict = None):
        send_ws_message("progress", {
            "stage": stage,
            "status": status,
            "data": data
        })

    progress = WorkflowProgress(callback)
    
    try:
        # 1. Run Lead Finder to check if this is a search query
        send_ws_message("log", {"message": "Analyzing request..."})
        
        # We pass stop_event to lead_finder
        search_result = lead_finder_agent.run(user_input, stop_event=stop_event)
        
        if stop_event and stop_event.is_set():
            return

        companies_to_analyze = []
        
        if search_result.get("is_search"):
            # It's a search query!
            found = search_result.get("companies", [])
            msg = search_result.get("message", "Search complete.")
            send_ws_message("log", {"message": f"🔎 {msg}"})
            
            # Send the list of found companies to frontend
            send_ws_message("search_results", {"companies": found})
            
            # Process all found companies
            companies_to_analyze = found
            
            if not companies_to_analyze:
                 send_ws_message("log", {"message": "No suitable companies found to analyze."})
                 send_ws_message("result", {"data": {"status": "completed", "note": "No companies found"}})
                 return
                 
            send_ws_message("log", {"message": f"🚀 Starting deep analysis for top {len(companies_to_analyze)} companies..."})
        else:
            # Direct single company analysis
            companies_to_analyze = [{"name": user_input, "context": "Direct analysis"}]

        # 2. Run Workflow for each company
        results = []
        for i, company_info in enumerate(companies_to_analyze):
            if stop_event and stop_event.is_set():
                break
                
            company_name = company_info["name"]
            context = company_info.get("context", "")
            
            send_ws_message("log", {"message": f"▶️ Analyzing [{i+1}/{len(companies_to_analyze)}]: {company_name}..."})
            
            # Create a prefixed progress callback for clarity in batch mode
            def batch_progress_callback(stage, status, data=None):
                 # We can modify 'stage' to include company name or just let existing UI handle it
                 # For now, let's just pass it through, but observing the log flow
                 send_ws_message("progress", {
                    "stage": stage,
                    "status": status,
                    "data": data,
                    "company": company_name # Add company tag
                 })
            
            batch_progress = WorkflowProgress(batch_progress_callback)
            
            # Run the workflow
            workflow = LongRunningWorkflow(progress=batch_progress, stop_event=stop_event)
            
            # If we have context, we might want to inject it, but existing workflow takes string input
            # We construct a simulated input: "Company Name"
            # If original input had Roles, we might want to preserve them? 
            # For search queries ("find product managers..."), we should extract roles from original query 
            # But for now let's just stick to Company Name and let generic role search happen.
            
            # TODO: Pass specific extracted roles if possible.
            
            lead_result = workflow.run_pipeline(company_name)
            results.append(lead_result)
            
            # Send individual result
            send_ws_message("result", {"data": lead_result, "is_batch": True})
            
            # Small pause between batches
            if i < len(companies_to_analyze) - 1:
                import time
                time.sleep(1)

        # 3. Final Summary
        send_ws_message("batch_complete", {
            "total": len(companies_to_analyze),
            "completed": len(results)
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        send_ws_message("error", {"error": str(e)})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    
    # Store stop event for the current session
    current_stop_event = None
    
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                command = message.get("command")
                
                if command == "analyze":
                    # If there's an existing running task, we should probably stop it or warn
                    # For now, let's create a new event
                    current_stop_event = threading.Event()
                    
                    user_input = message.get("input", "")
                    await manager.send_personal_message(json.dumps({
                        "type": "log", 
                        "message": f"Starting analysis for: {user_input}"
                    }), websocket)
                    
                    # Run workflow in a separate thread
                    thread = threading.Thread(
                        target=run_workflow_thread,
                        args=(user_input, websocket, main_loop, current_stop_event)
                    )
                    thread.start()
                
                elif command == "stop":
                    if current_stop_event:
                        current_stop_event.set()
                        await manager.send_personal_message(json.dumps({
                            "type": "log",
                            "message": "🛑 Stopping analysis... Saving progress..."
                        }), websocket)
                    else:
                        await manager.send_personal_message(json.dumps({
                            "type": "log",
                            "message": "No active analysis to stop."
                        }), websocket)
                
                elif command == "get_history":
                    # Fetch resumable executions
                    try:
                        print("DEBUG: Received get_history command")
                        from memory.state_manager import StateManager
                        state_manager = StateManager()
                        resumables = state_manager.get_resumable_executions()
                        print(f"DEBUG: Found {len(resumables)} resumable executions")
                        
                        # Sort by updated_at (newest first)
                        resumables.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
                        
                        # Send back to frontend
                        await manager.send_personal_message(json.dumps({
                            "type": "history",
                            "data": resumables
                        }), websocket)
                        print("DEBUG: Sent history to frontend")
                    except Exception as e:
                        print(f"DEBUG: Error in get_history: {e}")
                        import traceback
                        traceback.print_exc()
                        await manager.send_personal_message(json.dumps({
                            "type": "error",
                            "message": f"Failed to fetch history: {str(e)}"
                        }), websocket)
                    
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        if current_stop_event:
            current_stop_event.set()
        manager.disconnect(websocket)

@app.websocket("/")
async def websocket_endpoint_root(websocket: WebSocket):
    """Fallback handler for clients connecting to root"""
    await websocket_endpoint(websocket)

# Mount static files (Frontend)
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend", "dist")

if os.path.exists(static_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(static_dir, "assets")), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        if full_path.startswith("api") or full_path == "ws":
            return {"error": "Not Found"}
        
        file_path = os.path.join(static_dir, full_path)
        if os.path.isfile(file_path):
             from fastapi.responses import FileResponse
             return FileResponse(file_path)
             
        from fastapi.responses import FileResponse
        return FileResponse(os.path.join(static_dir, "index.html"))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    # Production uvicorn setup
    uvicorn.run("server:app", host="0.0.0.0", port=port, proxy_headers=True, forwarded_allow_ips="*")
