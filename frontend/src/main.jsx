import React, { useState, useEffect, useRef } from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '/api';
import {
  MessageSquare,
  Send,
  Menu,
  Plus,
  Search,
  Share2,
  MoreVertical,
  Cpu,
  Network,
  X,
  Database,
  ChevronRight,
  ChevronDown,
  Terminal,
  ArrowRight,
  Zap,
  Layers,
  Activity,
  Trash2
} from 'lucide-react';

/**
 * GLOBAL STYLES
 * Injected via JS to avoid 'Could not resolve ./index.css' errors
 */
const GlobalStyles = () => (
  <style>{`
    @tailwind base;
    @tailwind components;
    @tailwind utilities;
    
    body {
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
        'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
        sans-serif;
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
      background-color: #f0f0f0;
    }
  `}</style>
);

/**
 * MOCK DATA & CONSTANTS
 */
const INITIAL_HISTORY = [];

/**
 * COMPONENT: Grainy Background
 */
const NoiseOverlay = () => (
  <div className="pointer-events-none fixed inset-0 z-0 opacity-[0.03]"
    style={{
      backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)' fill='%2301012b'/%3E%3C/svg%3E")`,
    }}
  />
);

/**
 * COMPONENT: Graph Node Visualization
 */
const GraphVisualizer = ({ nodes }) => {
  if (!nodes || nodes.length === 0) return null;

  return (
    <div className="mt-3 border border-[#01012b]/10 bg-gray-50 p-3 font-mono text-xs">
      <div className="flex items-center gap-2 mb-2 text-gray-500 uppercase tracking-widest font-bold text-[10px]">
        <Network size={12} /> Graph Context Retrieved
      </div>
      <div className="flex flex-wrap gap-2">
        {nodes.map((node, idx) => (
          <span key={idx} className="inline-flex items-center px-2 py-1 bg-white border border-gray-300 shadow-sm rounded-none">
            <span className={`w-2 h-2 rounded-full mr-2 ${node.type === 'Code' ? 'bg-blue-500' : 'bg-red-500'}`}></span>
            {node.label}
          </span>
        ))}
      </div>
    </div>
  );
};

/**
 * COMPONENT: Confirmation Modal
 */
const ConfirmationModal = ({ isOpen, title, message, onConfirm, onCancel }) => {
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#01012b]/20 backdrop-blur-sm p-4">
      <div className="w-full max-w-sm border-2 border-[#01012b] bg-white p-6 shadow-[8px_8px_0px_0px_rgba(1,1,43,1)] animate-in fade-in zoom-in duration-200">
        <h3 className="mb-2 text-xl font-black uppercase tracking-tight text-[#01012b]">{title}</h3>
        <p className="mb-6 text-sm font-medium text-gray-600">{message}</p>
        <div className="flex gap-4">
          <button
            onClick={onConfirm}
            className="flex-1 border-2 border-[#01012b] bg-[#ff4400] py-3 text-sm font-bold text-white shadow-[4px_4px_0px_0px_rgba(1,1,43,1)] hover:translate-x-[1px] hover:translate-y-[1px] hover:shadow-none active:border-[#01012b] transition-all"
          >
            YES
          </button>
          <button
            onClick={onCancel}
            className="flex-1 border-2 border-[#01012b] bg-white py-3 text-sm font-bold text-[#01012b] shadow-[4px_4px_0px_0px_rgba(1,1,43,1)] hover:translate-x-[1px] hover:translate-y-[1px] hover:shadow-none active:bg-gray-50 transition-all"
          >
            NO
          </button>
        </div>
      </div>
    </div>
  );
};

/**
 * COMPONENT: Landing Page
 */
const LandingPage = ({ onGetStarted }) => {
  return (
    <div className="relative flex flex-col min-h-screen w-full bg-[#f0f0f0] font-sans text-gray-900 selection:bg-[#01012b] selection:text-white overflow-x-hidden">
      <NoiseOverlay />

      {/* Navigation */}
      <nav className="relative z-10 flex h-20 items-center justify-between border-b-2 border-[#01012b] bg-white px-6 md:px-12">
        <div className="flex items-center gap-2 font-black tracking-tighter text-2xl text-[#01012b]">
          <Database className="h-8 w-8" />
          <span>CELERGRAPH</span>
        </div>

        <div className="flex items-center gap-6">
          <span className="hidden md:flex items-center text-base mr-6 font-bold tracking-widest uppercase text-[#01012b]">
            Made with
            <span className="relative flex items-center justify-center mx-3">
              <span className="absolute inline-flex h-full w-full animate-ping opacity-75 text-[#ff4400] text-3xl">♥</span>
              <span className="relative inline-flex text-[#ff4400] text-3xl">♥</span>
            </span>
          </span>
          <button
            onClick={onGetStarted}
            className="flex items-center gap-2 border-2 border-[#01012b] bg-white px-6 py-2 font-bold text-[#01012b] hover:bg-[#01012b] hover:text-white transition-all shadow-[4px_4px_0px_0px_rgba(1,1,43,1)] hover:shadow-none hover:translate-x-[2px] hover:translate-y-[2px]"
          >
            LAUNCH APP
          </button>
        </div>
      </nav>

      {/* Hero Section */}
      <main className="relative z-10 flex flex-1 flex-col items-center justify-center px-4 py-20 text-center">

        <div className="mb-6 inline-flex items-center gap-2 border-2 border-[#01012b] bg-white px-4 py-1 text-xs font-bold uppercase tracking-widest shadow-[4px_4px_0px_0px_rgba(1,1,43,0.2)] text-[#01012b]">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-500 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
          </span>
          we are live!
        </div>

        {/* Updated Heading: Deep Blue-Black Theme */}
        <h1 className="max-w-6xl text-5xl font-black leading-[0.9] tracking-tighter text-[#01012b] sm:text-7xl md:text-8xl lg:text-[7rem]">
          GRAPH <br className="hidden md:block" />
          REASONING
        </h1>

        {/* Subheading */}
        <p className="mt-8 max-w-2xl text-lg font-medium leading-relaxed text-gray-600 md:text-xl">
          We turned the core FastAPI logic into a knowledge graph. Finally, a way to ask more about your codebase without feeling stupid.
        </p>

        {/* Button */}
        <div className="mt-12 flex flex-col items-center sm:flex-row">
          <button
            onClick={onGetStarted}
            className="group relative flex h-16 w-auto px-12 items-center justify-center gap-3 border-2 border-[#01012b] bg-[#ff4400] text-lg font-black text-white shadow-[6px_6px_0px_0px_rgba(1,1,43,1)] transition-all hover:translate-x-[3px] hover:translate-y-[3px] hover:shadow-none active:border-[#01012b]"
          >
            TALK TO OUR AI AGENT
            <ArrowRight className="transition-transform group-hover:translate-x-1" />
          </button>
        </div>

        {/* Feature Grid */}
        <div className="mt-24 grid w-full max-w-6xl grid-cols-1 gap-6 md:grid-cols-3 px-4">
          {[
            { icon: Zap, title: "Repo Traversal", desc: "Navigate import chains and class hierarchies instantly." },
            { icon: Layers, title: "Dependency Graph", desc: "Understand how FastAPI modules interact deeply." },
            { icon: Activity, title: "Live Context", desc: "Answers grounded in the actual GitHub source code." }
          ].map((feature, i) => (
            <div key={i} className="flex flex-col items-start border-2 border-[#01012b] bg-white p-6 shadow-[4px_4px_0px_0px_rgba(1,1,43,1)] text-left hover:-translate-y-1 transition-transform">
              <div className="mb-4 flex h-12 w-12 items-center justify-center border-2 border-[#01012b] bg-[#01012b] text-white">
                <feature.icon size={24} />
              </div>
              <h3 className="mb-2 text-xl font-black uppercase tracking-tight text-[#01012b]">{feature.title}</h3>
              <p className="text-sm text-gray-600 font-medium">{feature.desc}</p>
            </div>
          ))}
        </div>

        {/* Footer Logos */}
        <div className="mt-24 w-full border-t-2 border-[#01012b] bg-white py-12">
          <p className="mb-8 text-xs font-bold uppercase tracking-[0.2em] text-gray-400">Powered by Open Source</p>
          <div className="flex flex-wrap justify-center gap-12 opacity-80 grayscale items-center">
            {/* FastAPI */}
            <img src="https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png" alt="FastAPI" className="h-10 w-auto object-contain" />

            {/* Pydantic - Specific User URL */}
            <img src="https://miro.medium.com/v2/resize:fit:828/format:webp/1*YLYkLm1b72efjOtV-W7gfw.jpeg" alt="Pydantic" className="h-8 w-auto object-contain" />

            {/* Neo4j - Specific User URL */}
            <img src="https://upload.wikimedia.org/wikipedia/commons/e/e5/Neo4j-logo_color.png" alt="Neo4j" className="h-8 w-auto object-contain" />

            {/* LangChain */}
            <div className="flex items-center gap-2">
              <img src="https://avatars.githubusercontent.com/u/126733545?v=4" alt="LangChain" className="h-8 w-8 rounded-full" />
              <span className="text-xl font-bold tracking-tight text-[#01012b]">LangChain</span>
            </div>

            {/* Tree-sitter */}
            <img src="https://tree-sitter.github.io/tree-sitter/assets/images/tree-sitter-small.png" alt="Tree-sitter" className="h-10 w-auto object-contain" />
          </div>

          {/* Copyright Footer */}
          <div className="mt-16 border-t border-[#01012b]/10 pt-8">
            <p className="text-[10px] font-bold uppercase tracking-widest text-[#01012b]">
              Created by Harshini @ 2025 <span className="mx-2 text-[#ff4400]">•</span> All Rights Reserved
            </p>
          </div>
        </div>
      </main>
    </div>
  );
};

/**
 * COMPONENT: Chat Application (The main interface)
 */
const ChatInterface = ({ onLogout }) => {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [history, setHistory] = useState(INITIAL_HISTORY);
  const [activeMenuId, setActiveMenuId] = useState(null);

  // Modal State
  const [modalConfig, setModalConfig] = useState({
    isOpen: false,
    type: null, // 'single' or 'all'
    itemId: null
  });

  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      role: 'assistant',
      content: "I'm connected to the FastAPI knowledge graph. Ask me anything about the FastAPI codebase.",
      hasGraph: false,
      graphNodes: []
    }
  ]);
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = () => setActiveMenuId(null);
    window.addEventListener('click', handleClickOutside);
    return () => window.removeEventListener('click', handleClickOutside);
  }, []);

  // Open Modal for Single Delete
  const requestDeleteHistoryItem = (e, id) => {
    e.stopPropagation();
    setModalConfig({ isOpen: true, type: 'single', itemId: id });
    setActiveMenuId(null);
  };

  // Open Modal for Clear All
  const requestClearAllHistory = (e) => {
    e.stopPropagation();
    setModalConfig({ isOpen: true, type: 'all', itemId: null });
  };

  // Execute Deletion
  const confirmAction = async () => {
    if (modalConfig.type === 'single') {
      setHistory(prev => prev.filter(item => item.id !== modalConfig.itemId));
    } else if (modalConfig.type === 'all') {
      setHistory([]);
      try { await fetch(`${API_BASE}/cache/clear`, { method: 'POST' }); } catch { }
    }
    closeModal();
  };

  const closeModal = () => {
    setModalConfig({ isOpen: false, type: null, itemId: null });
  };

  /**
   * HANDLE SEND - Now includes Connection Logic
   */
  const handleSend = async () => {
    if (!input.trim()) return;

    // 1. Add user message to UI immediately
    const userMsg = { id: Date.now(), role: 'user', content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsTyping(true);

    try {
      console.log('handleSend: Streaming chat message to backend...');
      const body = JSON.stringify({
        message: userMsg.content,
        bypass_cache: messages.length <= 1,
        max_tokens: 1200,
      });

      const response = await fetch(`${API_BASE}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body
      });

      if (!response.ok || !response.body) {
        console.error('handleSend: /chat/stream failed', response);
        throw new Error('Streaming response was not ok');
      }

      // 3. Stream the GraphRAG response to UI incrementally
      const assistantId = Date.now() + 1;
      setMessages(prev => [...prev, { id: assistantId, role: 'assistant', content: '', hasGraph: false, graphNodes: [] }]);

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let accumulated = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        accumulated += chunk;
        setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, content: accumulated } : m));
      }

      // Try to parse accumulated as JSON
      let answerText = accumulated;
      try {
        const parsed = JSON.parse(accumulated);
        if (parsed && typeof parsed === 'object' && parsed.answer) {
          answerText = parsed.answer;
        }
      } catch { }
      setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, content: answerText } : m));

      // 4. Save history ONLY if Knowledge Graph was used (checked via citations)
      // Note: LLM might use standard brackets [] or unicode brackets 【】
      console.log('DEBUG: Checking citations in answerText:', answerText.substring(0, 200));
      const hasKGCitations =
        answerText.includes('[node:') || answerText.includes('[chunk:') ||
        answerText.includes('【node:') || answerText.includes('【chunk:');

      console.log('DEBUG: hasKGCitations =', hasKGCitations);

      if (hasKGCitations) {
        console.log('DEBUG: Saving history for:', userMsg.content);
        const newHistoryItem = { id: Date.now(), title: userMsg.content, date: 'Today' };
        setHistory(prev => [newHistoryItem, ...prev]);
        try {
          await fetch(`${API_BASE}/history`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(newHistoryItem) });
        } catch (historyError) {
          console.error('handleSend: Error saving history:', historyError);
        }
      } else {
        console.log('handleSend: No KG citations found, skipping history save.');
      }

    } catch (error) {
      console.error("handleSend: Connection failed or other error:", error);
    } finally {
      setIsTyping(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="relative flex h-screen w-full overflow-hidden bg-[#f0f0f0] font-sans text-gray-900 selection:bg-[#01012b] selection:text-white">
      <NoiseOverlay />

      {/* --- SIDEBAR --- */}
      <aside
        className={`
          fixed inset-y-0 left-0 z-20 flex w-72 flex-col border-r-2 border-[#01012b] bg-[#e8e8e8] transition-transform duration-300 ease-in-out
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
          md:relative md:translate-x-0
          ${!sidebarOpen && 'md:hidden'}
        `}
      >
        <div className="flex h-16 items-center justify-between border-b-2 border-[#01012b] px-4 bg-white">
          <div className="flex items-center gap-2 font-black tracking-tight text-xl cursor-pointer text-[#01012b]" onClick={onLogout}>
            <Database className="h-6 w-6" />
            <span>CELERGRAPH</span>
          </div>
          <button onClick={() => setSidebarOpen(false)} className="md:hidden text-[#01012b]">
            <X size={20} />
          </button>
        </div>

        <div className="p-4">
          <button
            onClick={() => setMessages([])}
            className="flex w-full items-center justify-center gap-2 border-2 border-[#01012b] bg-[#ff4400] px-4 py-3 text-sm font-bold text-white shadow-[4px_4px_0px_0px_rgba(1,1,43,1)] transition-all hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none active:border-[#01012b]"
          >
            <Plus size={18} />
            NEW SESSION
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-4 py-2">
          <div className="mb-2 flex items-center justify-between">
            <div className="text-xs font-bold uppercase tracking-widest text-gray-500">Recent Queries</div>
            {history.length > 0 && (
              <button
                onClick={requestClearAllHistory}
                className="flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider text-red-500 hover:text-red-700"
              >
                <Trash2 size={12} /> Clear All
              </button>
            )}
          </div>

          <div className="flex flex-col gap-2 pb-4">
            {history.map((item) => (
              <div key={item.id} className="relative group">
                <button
                  className="flex w-full flex-col items-start border border-transparent p-2 pr-8 text-left text-sm transition-all hover:border-[#01012b] hover:bg-white"
                >
                  <span className="font-medium truncate w-full text-[#01012b]">{item.title}</span>
                  <span className="text-xs text-gray-500">{item.date}</span>
                </button>

                {/* 3-Dot Menu Trigger */}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setActiveMenuId(activeMenuId === item.id ? null : item.id);
                  }}
                  className={`absolute right-2 top-2 p-1 rounded-sm hover:bg-gray-200 text-gray-400 hover:text-[#01012b] transition-opacity ${activeMenuId === item.id ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'}`}
                >
                  <MoreVertical size={16} />
                </button>

                {/* Dropdown Menu */}
                {activeMenuId === item.id && (
                  <div className="absolute right-0 top-8 z-50 w-36 border-2 border-[#01012b] bg-white shadow-[4px_4px_0px_0px_rgba(1,1,43,1)]">
                    <button
                      onClick={(e) => requestDeleteHistoryItem(e, item.id)}
                      className="flex w-full items-center gap-2 px-3 py-2 text-xs font-bold text-red-600 hover:bg-gray-50"
                    >
                      <Trash2 size={14} /> DELETE CHAT
                    </button>
                  </div>
                )}
              </div>
            ))}

            {history.length === 0 && (
              <div className="py-4 text-center text-xs italic text-gray-400">
                No recent history
              </div>
            )}
          </div>
        </div>

        <div className="border-t-2 border-[#01012b] bg-white p-4">
          <p className="text-xs font-bold uppercase tracking-widest text-[#01012b] text-center leading-relaxed">
            "It works on my machine" <br />
            <span className="normal-case opacity-60 text-[10px]">~ someone, probably.</span>
          </p>
        </div>
      </aside>


      {/* --- MAIN CONTENT --- */}
      <main className="relative flex flex-1 flex-col overflow-hidden">

        <header className="flex h-16 items-center justify-between border-b-2 border-[#01012b] bg-white px-4 md:px-6">
          <div className="flex items-center gap-3">
            {!sidebarOpen && (
              <button
                onClick={() => setSidebarOpen(true)}
                className="mr-2 rounded-sm p-1 hover:bg-gray-200 text-[#01012b]"
              >
                <Menu size={24} />
              </button>
            )}
            <h1 className="font-bold text-lg flex items-center gap-2">
              <span className="bg-[#01012b] text-white px-2 py-0.5 text-xs uppercase tracking-wider">Celer</span>
              <span className="text-[#01012b]">Connected</span>
            </h1>
          </div>
          <div className="flex gap-2">
            <button className="border-2 border-[#01012b] p-2 hover:bg-[#01012b] hover:text-white transition-colors text-[#01012b]">
              <Share2 size={18} />
            </button>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto p-4 md:p-8 scroll-smooth">
          <div className="mx-auto max-w-3xl space-y-8">

            {messages.length === 0 && (
              <div className="mt-20 text-center opacity-60">
                <div className="mx-auto mb-4 flex h-20 w-20 items-center justify-center border-4 border-[#01012b] bg-white rounded-full text-[#01012b]">
                  <Database size={40} />
                </div>
                <h2 className="text-3xl font-black uppercase tracking-tight text-[#01012b]">CelerGraph System</h2>
                <p className="mt-2 font-medium text-gray-600">Enter a query to traverse the knowledge graph.</p>
              </div>
            )}

            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {msg.role === 'assistant' && (
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center border-2 border-[#01012b] bg-white font-bold text-[#01012b] shadow-[3px_3px_0px_0px_rgba(1,1,43,1)]">
                    AI
                  </div>
                )}

                <div
                  className={`
                    relative max-w-[85%] border-2 p-5 overflow-hidden
                    ${msg.role === 'user'
                      ? 'border-[#01012b] bg-[#01012b] text-white shadow-[4px_4px_0px_0px_rgba(1,1,43,0.5)]'
                      : 'border-[#01012b] bg-white text-[#01012b] shadow-[4px_4px_0px_0px_rgba(1,1,43,1)]'
                    }
                  `}
                >
                  <p className="whitespace-pre-wrap break-words text-sm md:text-base leading-relaxed font-medium">
                    {msg.content}
                  </p>

                  {msg.role === 'assistant' && msg.hasGraph && (
                    <GraphVisualizer nodes={msg.graphNodes} />
                  )}
                </div>

                {msg.role === 'user' && (
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center border-2 border-[#01012b] bg-[#ff4400] text-white font-bold shadow-[3px_3px_0px_0px_rgba(1,1,43,1)]">
                    U
                  </div>
                )}
              </div>
            ))}

            {isTyping && (
              <div className="flex gap-4 justify-start">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center border-2 border-[#01012b] bg-white text-[#01012b] shadow-[3px_3px_0px_0px_rgba(1,1,43,1)]">
                  AI
                </div>
                <div className="border-2 border-[#01012b] bg-white p-4 shadow-[4px_4px_0px_0px_rgba(1,1,43,1)] flex items-center gap-2">
                  <span className="w-2 h-2 bg-[#01012b] animate-bounce"></span>
                  <span className="w-2 h-2 bg-[#01012b] animate-bounce delay-100"></span>
                  <span className="w-2 h-2 bg-[#01012b] animate-bounce delay-200"></span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>

        <div className="border-t-2 border-[#01012b] bg-white p-4 md:p-6">
          <div className="mx-auto flex max-w-3xl items-end gap-3">
            <div className="relative flex-1">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask something..."
                className="w-full resize-none border-2 border-[#01012b] bg-gray-50 p-4 pr-12 text-sm font-medium focus:outline-none focus:ring-4 focus:ring-[#01012b]/10 shadow-inner"
                rows={1}
                style={{ minHeight: '60px', maxHeight: '200px' }}
              />
              <div className="absolute right-3 bottom-3 text-xs text-gray-400 font-bold uppercase pointer-events-none">
                CMD + Enter
              </div>
            </div>
            <button
              onClick={handleSend}
              disabled={!input.trim()}
              className="group flex h-[60px] w-[60px] items-center justify-center border-2 border-[#01012b] bg-[#01012b] text-white transition-all hover:bg-[#ff4400] hover:-translate-y-1 hover:shadow-[4px_4px_0px_0px_rgba(1,1,43,1)] disabled:opacity-50 disabled:hover:translate-y-0 disabled:hover:shadow-none"
            >
              <Send size={24} className="group-hover:translate-x-1 group-hover:-translate-y-1 transition-transform" />
            </button>
          </div>
          <div className="mx-auto max-w-3xl mt-2 text-center">
            <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">
              AI can make mistakes. Verify CelerGraph connections.
            </span>
          </div>
        </div>

        {/* Confirmation Modal */}
        <ConfirmationModal
          isOpen={modalConfig.isOpen}
          title={modalConfig.type === 'all' ? "CLEAR HISTORY" : "DELETE CHAT"}
          message={modalConfig.type === 'all' ? "Are you sure you want to delete all history?" : "Are you sure you want to delete this?"}
          onConfirm={confirmAction}
          onCancel={closeModal}
        />
      </main>
    </div>
  );
};

/**
 * MAIN APP CONTAINER (Root)
 */
const App = () => {
  const [currentView, setCurrentView] = useState('landing');

  return (
    <>
      <GlobalStyles />
      {currentView === 'landing' ? (
        <LandingPage onGetStarted={() => setCurrentView('chat')} />
      ) : (
        <ChatInterface onLogout={() => setCurrentView('landing')} />
      )}
    </>
  );
};

// RENDER
const container = document.getElementById('root');

// Prevent HMR double-render warning
if (!container._reactRoot) {
  container._reactRoot = createRoot(container);
}

container._reactRoot.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
