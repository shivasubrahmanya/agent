
import React, { useState, useEffect, useRef } from 'react';
import { BadgeCheck, Search, Send, Activity, Terminal } from 'lucide-react';
import { ProgressSteps } from './components/ProgressSteps';
import { LogViewer } from './components/LogViewer';
import { ResultCard } from './components/ResultCard';

const WS_URL = "ws://localhost:8000/ws";

function App() {
  const [input, setInput] = useState("");
  const [status, setStatus] = useState("idle"); // idle, connecting, analyzing, completed, error
  const [logs, setLogs] = useState([]);
  const [currentStage, setCurrentStage] = useState("");
  const [completedStages, setCompletedStages] = useState([]);
  const [leadResult, setLeadResult] = useState(null);
  const [connected, setConnected] = useState(false);

  const ws = useRef(null);

  useEffect(() => {
    connectWs();
    return () => {
      if (ws.current) ws.current.close();
    };
  }, []);

  const connectWs = () => {
    setStatus("connecting");
    ws.current = new WebSocket(WS_URL);

    ws.current.onopen = () => {
      setConnected(true);
      setStatus("idle");
      addLog("system", "Connected to agent backend.");
    };

    ws.current.onclose = () => {
      setConnected(false);
      setStatus("error");
      addLog("error", "Disconnected from server. Retrying...");
      setTimeout(connectWs, 3000);
    };

    ws.current.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      handleMessage(msg);
    };
  };

  // History / Resume Logic
  const [showHistory, setShowHistory] = useState(false);
  const [historyItems, setHistoryItems] = useState([]);

  const handleGetHistory = () => {
    if (!connected) {
      console.log("Cannot get history: Not connected");
      return;
    }
    console.log("Sending get_history command");
    ws.current.send(JSON.stringify({ command: "get_history" }));
  };

  const handleResume = (id) => {
    setInput(`resume ${id}`);
    setShowHistory(false);
    // Optional: Auto-submit
    // setTimeout(() => handleAnalyze({ preventDefault: () => {} }), 100);
  };

  // Update handleMessage to receive history
  const handleMessage = (msg) => {
    console.log("Received message:", msg);
    if (msg.type === 'log') {
      addLog("info", msg.message);
    } else if (msg.type === 'history') {
      console.log("History items received:", msg.data);
      setHistoryItems(msg.data);
      setShowHistory(true);
    } else if (msg.type === 'progress') {
      const { stage, status, data } = msg;

      if (status === 'running') {
        setCurrentStage(stage);
        addLog("info", `Starting stage: ${stage}...`);
      } else if (status === 'completed') {
        setCompletedStages(prev => [...prev, stage]);
        addLog("success", `Completed stage: ${stage}`);
        if (data) {
          addLog("data", `Received data for ${stage}`, data);
          // Optimistically update result if possible
          if (stage === 'discovery') {
            setLeadResult(prev => ({ ...prev, company: data }));
          }
        }
      }
    } else if (msg.type === 'result') {
      setLeadResult(msg.data);
      setStatus("completed");
      setCurrentStage("");
      addLog("success", "Analysis complete!");
    } else if (msg.type === 'error') {
      addLog("error", msg.error);
      setStatus("idle"); // reset to allow retry
    }
  };

  const addLog = (type, message, details = null) => {
    setLogs(prev => [...prev, { type, message, details }]);
  };

  const handleStop = (e) => {
    e.preventDefault();
    if (!connected || status !== 'analyzing') return;

    ws.current.send(JSON.stringify({
      command: "stop"
    }));
    addLog("info", "🛑 Sending stop signal...");
  };

  const handleAnalyze = (e) => {
    e.preventDefault();
    if (!input.trim() || !connected) return;

    setLogs([]); // Clear logs
    setCompletedStages([]);
    setCurrentStage("");
    setLeadResult(null);
    setStatus("analyzing");

    ws.current.send(JSON.stringify({
      command: "analyze",
      input: input
    }));
  };

  return (
    <div className="min-h-screen bg-background text-foreground p-4 md:p-8 font-sans selection:bg-primary/20 relative">
      <div className="max-w-5xl mx-auto space-y-8">

        {/* Header */}
        <div className="flex items-center justify-between border-b border-border pb-6">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-primary/10 rounded-xl">
              <Activity className="text-primary w-8 h-8" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight">B2B Lead Discovery Agent</h1>
              <p className="text-muted-foreground text-sm">Powered by Groq + Apollo.io + Snov.io</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className={`w-2.5 h-2.5 rounded-full ${connected ? 'bg-green-500 animate-pulse' : 'bg-destructive'}`} />
            <span className="text-xs font-medium text-muted-foreground">
              {connected ? 'System Online' : 'Connecting...'}
            </span>
          </div>
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

          {/* Left Column: Input & Logs */}
          <div className="lg:col-span-1 space-y-6">

            {/* Input Card */}
            <div className="bg-card border border-border rounded-xl p-5 shadow-sm">
              <div className="flex justify-between items-center mb-2">
                <label className="text-sm font-medium block">Company & Roles</label>
                <button
                  onClick={handleGetHistory}
                  className="text-xs text-primary hover:underline flex items-center gap-1"
                  type="button"
                >
                  <Activity size={12} /> History / Resume
                </button>
              </div>
              <form onSubmit={handleAnalyze} className="space-y-4">
                <div className="relative">
                  <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="e.g. Acme Corp, Roles: CEO"
                    className="w-full bg-background border border-input rounded-lg px-4 py-3 pr-10 focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all outline-none"
                    disabled={status === 'analyzing'}
                  />
                  <Search className="absolute right-3 top-3.5 text-muted-foreground w-5 h-5" />
                </div>
                <div className="flex gap-2">
                  <button
                    type="submit"
                    disabled={!connected || status === 'analyzing' || !input.trim()}
                    className="flex-1 bg-primary hover:bg-primary/90 text-primary-foreground font-medium py-3 rounded-lg transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {status === 'analyzing' ? (
                      'Analyzing...'
                    ) : (
                      <>
                        <Send size={18} /> Start Analysis
                      </>
                    )}
                  </button>

                  {status === 'analyzing' && (
                    <button
                      type="button"
                      onClick={handleStop}
                      className="bg-destructive hover:bg-destructive/90 text-destructive-foreground font-medium px-4 py-3 rounded-lg transition-all flex items-center justify-center gap-2"
                      title="Stop & Save Progress"
                    >
                      <BadgeCheck size={18} className="rotate-180" /> Stop
                    </button>
                  )}
                </div>
              </form>
            </div>

            {/* Logs Window */}
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground px-1">
                <Terminal size={14} /> Live Logs
              </div>
              <LogViewer logs={logs} />
            </div>

          </div>

          {/* Right Column: Visualization & Results */}
          <div className="lg:col-span-2 space-y-6">

            {/* Progress Bar */}
            <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
              <h3 className="text-sm font-medium text-muted-foreground mb-4">Pipeline Status</h3>
              <ProgressSteps currentStage={currentStage} completedStages={completedStages} />
            </div>

            {/* Dynamic Results Area */}
            {leadResult ? (
              <ResultCard data={leadResult} />
            ) : (
              <div className="h-64 border-2 border-dashed border-border/50 rounded-xl flex flex-col items-center justify-center text-muted-foreground/50">
                <div className="p-4 bg-muted/10 rounded-full mb-4">
                  <BadgeCheck size={40} />
                </div>
                <p className="text-sm">Results will appear here...</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* History Modal */}
      {showHistory && (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-xl shadow-lg max-w-lg w-full max-h-[80vh] flex flex-col">
            <div className="p-4 border-b border-border flex justify-between items-center">
              <h2 className="font-bold text-lg">Resume Session</h2>
              <button onClick={() => setShowHistory(false)} className="text-muted-foreground hover:text-foreground">
                ✕
              </button>
            </div>
            <div className="overflow-y-auto p-4 space-y-2 flex-1">
              {historyItems.length === 0 ? (
                <p className="text-center text-muted-foreground py-8">No resumable sessions found.</p>
              ) : (
                historyItems.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => handleResume(item.id)}
                    className="w-full text-left p-3 hover:bg-muted/50 rounded-lg border border-border/50 transition-colors group"
                  >
                    <div className="flex justify-between items-start">
                      <span className="font-medium">
                        {typeof item.input === 'object'
                          ? (item.input.company || item.input.company_name || "Complex Analysis")
                          : (item.input || "Unknown Analysis")}
                      </span>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${item.status === 'completed' ? 'bg-green-100 text-green-700' :
                        item.status === 'failed' ? 'bg-red-100 text-red-700' :
                          'bg-yellow-100 text-yellow-700'
                        }`}>
                        {item.status}
                      </span>
                    </div>
                    <div className="text-xs text-muted-foreground mt-1 flex justify-between">
                      <span>ID: {item.id.substring(0, 8)}...</span>
                      <span>{new Date(item.updated_at).toLocaleString()}</span>
                    </div>
                  </button>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
