
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

  const handleMessage = (msg) => {
    if (msg.type === 'log') {
      addLog("info", msg.message);
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
    <div className="min-h-screen bg-background text-foreground p-4 md:p-8 font-sans selection:bg-primary/20">
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
              <label className="text-sm font-medium mb-2 block">Company & Roles</label>
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
    </div>
  );
}

export default App;
