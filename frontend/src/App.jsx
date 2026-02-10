
import React, { useState, useEffect, useRef } from 'react';
import { BadgeCheck, Search, Send, Activity, Terminal } from 'lucide-react';
import { ProgressSteps } from './components/ProgressSteps';
import { LogViewer } from './components/LogViewer';
import { ResultCard } from './components/ResultCard';

// Construct WebSocket URL
const getWsUrl = () => {
  // 1. Manual override from env
  const envUrl = import.meta.env.VITE_WS_URL;
  if (envUrl) {
    const baseUrl = envUrl.replace(/\/$/, "");
    return baseUrl.endsWith("/ws") ? baseUrl : `${baseUrl}/ws`;
  }

  // 2. Auto-detect based on current window location
  if (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${window.location.host}/ws`;
  }

  // 3. Fallback to localhost for development
  return "ws://localhost:8000/ws";
};

const WS_URL = getWsUrl();

function App() {
  /* State */
  const [input, setInput] = useState("");
  const [status, setStatus] = useState("idle");
  const [messages, setMessages] = useState([]); // { role: 'user'|'agent'|'system', content: string, data?: any }
  const [activeAnalysisId, setActiveAnalysisId] = useState(null); // ID of company currently being viewed
  const [analysisResults, setAnalysisResults] = useState({}); // Map: companyName -> data
  const [logs, setLogs] = useState([]);

  // Pipeline State for the *currently running* or *selected* analysis
  const [currentStage, setCurrentStage] = useState("");
  const [completedStages, setCompletedStages] = useState([]);
  const [connected, setConnected] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [historyItems, setHistoryItems] = useState([]);

  const ws = useRef(null);
  const messagesEndRef = useRef(null);

  // Auto-scroll chat
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    connectWs();
    return () => { if (ws.current) ws.current.close(); };
  }, []);

  const connectWs = () => {
    setStatus("connecting");
    ws.current = new WebSocket(WS_URL);
    ws.current.onopen = () => {
      setConnected(true);
      setStatus("idle");
      // addSystemMessage("System connected. Ready to find leads.");
    };
    ws.current.onclose = () => {
      setConnected(false);
      setStatus("error");
      setTimeout(connectWs, 3000);
    };
    ws.current.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      handleMessage(msg);
    };
  };

  const addMessage = (role, content, data = null) => {
    setMessages(prev => [...prev, { role, content, data, timestamp: new Date() }]);
  };

  const handleMessage = (msg) => {
    if (msg.type === 'log') {
      // Add to debug logs
      setLogs(prev => [...prev, { type: 'info', message: msg.message }]);

      // If it's a major log, maybe show as system status toast or small text?
      // For now, keep logs separate, but maybe update a "status text"

    } else if (msg.type === 'search_results') {
      const companies = msg.companies;
      addMessage('agent', `I found ${companies.length} potential companies. Starting analysis...`, { type: 'list', items: companies });

    } else if (msg.type === 'progress') {
      const { stage, status, data, company } = msg;

      // If we are currently viewing this company (or if it's the only one), update progress UI
      // For simplicity, we just show progress of the *latest* active one if not specified

      if (status === 'running') {
        setCurrentStage(stage);
      } else if (status === 'completed') {
        setCompletedStages(prev => {
          if (prev.includes(stage)) return prev;
          return [...prev, stage];
        });

        // Update the specific result in our store
        if (company) {
          setAnalysisResults(prev => {
            const existing = prev[company] || { stages: {}, company: { name: company } };
            // Update stage data
            if (data) {
              if (stage === 'discovery') existing.company = data;
              else if (stage === 'structure') existing.structure = data;
              // ... generic merge
            }
            return { ...prev, [company]: existing };
          });
        }
      }

    } else if (msg.type === 'result') {
      const result = msg.data;
      const companyName = result.company?.name || result.input; // Fallback

      setAnalysisResults(prev => ({
        ...prev,
        [companyName]: result
      }));

      // If this is the first result or we are auto-following, switch view
      if (!activeAnalysisId) setActiveAnalysisId(companyName);

      addMessage('agent', `Analysis complete for ${companyName}`, { type: 'result_summary', company: companyName, score: result.confidence_score });

    } else if (msg.type === 'batch_complete') {
      setStatus("idle");
      addMessage('system', `Batch analysis complete. Processed ${msg.completed}/${msg.total} companies.`);
      setCompletedStages([]); // Reset for next run
      setCurrentStage("");
    } else if (msg.type === 'history') {
      setHistoryItems(msg.data);
      setShowHistory(true);
    } else if (msg.type === 'error') {
      addMessage('system', `Error: ${msg.error}`);
      setStatus("idle");
    }
  };

  const handleAnalyze = (e) => {
    e.preventDefault();
    if (!input.trim() || !connected) return;

    // Reset UI state for new run
    setLogs([]);
    setCompletedStages([]);
    setCurrentStage("");
    // We don't clear analysisResults, we append to them? Or clear? 
    // Let's clear to keep it fresh for this demo
    setAnalysisResults({});
    setActiveAnalysisId(null);

    setStatus("analyzing");
    addMessage('user', input);

    ws.current.send(JSON.stringify({
      command: "analyze",
      input: input
    }));
    setInput("");
  };

  const handleStop = (e) => {
    e.preventDefault();
    ws.current.send(JSON.stringify({ command: "stop" }));
  };

  const handleGetHistory = () => {
    ws.current.send(JSON.stringify({ command: "get_history" }));
  };

  const handleResume = (id) => {
    // Send as analyzed command
    ws.current.send(JSON.stringify({ command: "analyze", input: `resume ${id}` }));
    setShowHistory(false);
    setStatus("analyzing");
  };

  // -- Render Helpers --
  const activeResult = activeAnalysisId ? analysisResults[activeAnalysisId] : null;

  return (
    <div className="h-screen bg-background text-foreground flex overflow-hidden font-sans">

      {/* LEFT PANEL: Chat & Navigation (35%) */}
      <div className="w-[400px] flex-shrink-0 flex flex-col border-r border-border bg-muted/5">

        {/* Header */}
        <div className="p-4 border-b border-border bg-background flex items-center justify-between">
          <div className="flex items-center gap-2 font-bold text-lg">
            <Activity className="text-primary w-5 h-5" />
            <span>LeadAgent</span>
          </div>
          <div className="flex gap-2">
            <button onClick={handleGetHistory} className="p-2 hover:bg-muted rounded-md text-muted-foreground" title="History">
              <Activity size={16} />
            </button>
            <div className={`w-2.5 h-2.5 rounded-full ${connected ? 'bg-green-500' : 'bg-destructive'}`} title={connected ? "Online" : "Offline"} />
          </div>
        </div>

        {/* Chat Stream */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 && (
            <div className="text-center text-muted-foreground mt-20">
              <p className="text-sm">Enter a company name or search query to begin.</p>
            </div>
          )}

          {messages.map((m, i) => (
            <div key={i} className={`flex flex-col ${m.role === 'user' ? 'items-end' : 'items-start'}`}>
              <div className={`max-w-[85%] p-3 rounded-lg text-sm ${m.role === 'user' ? 'bg-primary text-primary-foreground rounded-br-none' :
                m.role === 'system' ? 'bg-muted text-muted-foreground text-xs' :
                  'bg-card border border-border rounded-bl-none shadow-sm'
                }`}>
                {m.content}
              </div>

              {/* Rich Data Attachments */}
              {m.data?.type === 'list' && (
                <div className="mt-2 ml-2 space-y-1 w-[85%]">
                  {m.data.items.map((company, idx) => (
                    <button
                      key={idx}
                      onClick={() => setActiveAnalysisId(company.name)}
                      className={`w-full text-left text-xs p-2 rounded border border-border bg-background hover:bg-accent transiton-colors ${activeAnalysisId === company.name ? 'ring-1 ring-primary' : ''}`}
                    >
                      <div className="font-medium">{company.name}</div>
                      <div className="text-muted-foreground line-clamp-1">{company.context}</div>
                    </button>
                  ))}
                </div>
              )}

              {m.data?.type === 'result_summary' && (
                <button
                  onClick={() => setActiveAnalysisId(m.data.company)}
                  className="mt-2 ml-2 text-xs flex items-center gap-2 p-2 bg-green-500/10 text-green-600 rounded border border-green-500/20 hover:bg-green-500/20 transition-colors"
                >
                  <div className="font-bold">{(m.data.score * 100).toFixed(0)}%</div>
                  View Analysis for {m.data.company}
                </button>
              )}
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="p-4 border-t border-border bg-background">
          <form onSubmit={handleAnalyze} className="relative">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Find startups in Boston..."
              className="w-full bg-muted/50 border border-input rounded-xl px-4 py-3 pr-10 focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all"
              disabled={status === 'analyzing1' /* Allow queuing? No, nice to disable for now */}
            />
            <button
              type="submit"
              disabled={!input.trim() || status === 'analyzing'}
              className="absolute right-2 top-2 p-1.5 bg-primary text-primary-foreground rounded-lg disabled:opacity-50 hover:bg-primary/90 transition-colors"
            >
              {status === 'analyzing' ? <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <Send size={16} />}
            </button>
          </form>
          <div className="text-[10px] text-center text-muted-foreground mt-2 flex justify-between px-1">
            <span>SerpApi • Apollo • Snov.io</span>
            {status === 'analyzing' && (
              <button onClick={handleStop} className="text-destructive hover:underline">Stop Generating</button>
            )}
          </div>
        </div>
      </div>

      {/* RIGHT PANEL: Details (65%) */}
      <div className="flex-1 bg-muted/10 flex flex-col h-full overflow-hidden relative">

        {activeAnalysisId ? (
          <div className="flex-1 overflow-y-auto p-6 md:p-10">
            <div className="max-w-3xl mx-auto space-y-6">

              {/* Detailed Result */}
              {activeResult ? (
                <ResultCard data={activeResult} />
              ) : (
                <div className="text-center py-20 text-muted-foreground">
                  <div className="animate-spin w-8 h-8 border-2 border-primary border-t-transparent rounded-full mx-auto mb-4" />
                  <p>Analyzing {activeAnalysisId}...</p>

                  <div className="mt-8 max-w-md mx-auto">
                    <ProgressSteps currentStage={currentStage} completedStages={completedStages} />
                  </div>
                </div>
              )}

              {/* Logs for this company (filtered?) - For now show all logs at bottom of detail view */}
              <div className="mt-12 pt-12 border-t border-border/20">
                <h4 className="text-xs font-semibold uppercase text-muted-foreground mb-4 flex items-center gap-2">
                  <Terminal size={12} /> Execution Logs
                </h4>
                <LogViewer logs={logs} />
              </div>
            </div>
          </div>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground/50 p-6">
            <div className="w-16 h-16 bg-muted/20 rounded-2xl flex items-center justify-center mb-4">
              <Search size={32} />
            </div>
            <h3 className="text-lg font-medium text-foreground/80">Select a company to view details</h3>
            <p className="max-w-md text-center mt-2 text-sm">
              Search results and analysis progress will appear here. Select a company from the chat on the left to inspect deep research data.
            </p>
          </div>
        )}
      </div>

      {/* History Modal (Same as before) */}
      {showHistory && (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-xl shadow-lg max-w-lg w-full max-h-[80vh] flex flex-col">
            <div className="p-4 border-b border-border flex justify-between items-center">
              <h2 className="font-bold text-lg">Resume Session</h2>
              <button onClick={() => setShowHistory(false)} className="text-muted-foreground hover:text-foreground">✕</button>
            </div>
            <div className="overflow-y-auto p-4 space-y-2 flex-1">
              {historyItems.map((item) => (
                <button
                  key={item.id}
                  onClick={() => handleResume(item.id)}
                  className="w-full text-left p-3 hover:bg-muted/50 rounded-lg border border-border/50 transition-colors group"
                >
                  <div className="flex justify-between items-start">
                    <span className="font-medium">{typeof item.input === 'object' ? (item.input.company || "Analysis") : item.input}</span>
                    <span className="text-xs px-2 py-0.5 rounded-full bg-muted text-foreground">{item.status}</span>
                  </div>
                  <div className="text-xs text-muted-foreground mt-1">{new Date(item.updated_at).toLocaleString()}</div>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

    </div>
  );
}

export default App;
