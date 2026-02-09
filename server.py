
import os
import json
import asyncio
import threading
from typing import List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Import existing agent workflow
# Ensure the parent directory is in path or we are running from root
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from workflow import LongRunningWorkflow, WorkflowProgress

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

def run_agent_workflow(user_input: str, websocket: WebSocket):
    """
    Run the synchronous agent workflow and push updates to the websocket.
    This runs in a separate thread.
    """
    
    # Define a sync callback that puts messages into the event loop
    def progress_callback(stage: str, status: str, data: dict = None):
        message = {
            "type": "progress",
            "stage": stage,
            "status": status,
            "data": data
        }
        # We need to send this to the specific websocket
        # Since we are in a thread, we need to run_coroutine_threadsafe if we had the loop
        # But we can just use a simple asyncio.run or similar if we weren't in a sticky spot
        # Better approach: The callback just calls the async send method via a helper or 
        # we assume simple fire-and-forget for now, but fastapi websockets are async.
        
        # Proper way: Use the loop from the main thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(manager.send_personal_message(json.dumps(message), websocket))
        loop.close()

    # Wait, creating a new loop in a thread is fine, but the websocket object is bound to the main event loop.
    # We should use asyncio.run_coroutine_threadsafe with the MAIN loop.
    pass

# We need the main event loop to send messages back
main_loop = None

@app.on_event("startup")
async def startup_event():
    global main_loop
    main_loop = asyncio.get_running_loop()

class AgentRequest(BaseModel):
    input: str

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

def run_workflow_thread(user_input: str, websocket: WebSocket, loop, stop_event=None):
    """Execution thread for the agent"""
    
    def callback(stage: str, status: str, data: dict = None):
        msg = {
            "type": "progress",
            "stage": stage,
            "status": status,
            "data": data
        }
        try:
            future = asyncio.run_coroutine_threadsafe(
                websocket.send_text(json.dumps(msg)), 
                loop
            )
            future.result() # Wait for it to be sent
        except Exception as e:
            print(f"Error sending ws update: {e}")

    progress = WorkflowProgress(callback)
    
    try:
        workflow = LongRunningWorkflow(progress=progress, stop_event=stop_event)
        result = workflow.run_pipeline(user_input)
        
        # Send final result
        final_msg = {
            "type": "result",
            "data": result
        }
        asyncio.run_coroutine_threadsafe(
            websocket.send_text(json.dumps(final_msg)),
            loop
        )
    except Exception as e:
        error_msg = {
            "type": "error",
            "error": str(e)
        }
        asyncio.run_coroutine_threadsafe(
            websocket.send_text(json.dumps(error_msg)),
            loop
        )

# Mount static files (Frontend)
# We will mount it at the root BUT we need to make sure API routes take precedence
# Or we usually mount it at / and rely on index.html fallback for SPA
# ideally: mount static at /static, and have a catch-all route for index.html
# For simplicity, let's assume we serve 'frontend/dist' at root.
if os.path.exists("frontend/dist"):
    app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    # Look for the port in the environment or default to 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)
