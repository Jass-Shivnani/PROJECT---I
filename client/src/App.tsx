import React, { useState, useEffect, useRef } from 'react';
import {
  Thread,
  Message,
  ComputerUseState,
  VoiceTalkState,
  OrchestrationNode,
  AgentHandoff,
  SafetyApprovalRequest
} from './types';
import { NavigationRail, WorkspaceTab } from './components/NavigationRail';
import { Sidebar } from './components/Sidebar';
import { ChatHeader } from './components/ChatHeader';
import { MessageView } from './components/MessageView';
import { Composer } from './components/Composer';
import { AgentMarketplace, SPECIALIST_AGENTS, AgentSpecialist } from './components/AgentMarketplace';
import { ComputerUseDesk } from './components/ComputerUseDesk';
import { KnowledgeGraphView } from './components/KnowledgeGraphView';
import { ArtifactDrawer, ArtifactItem } from './components/ArtifactDrawer';
import { ComputerUseDrawer } from './components/ComputerUseDrawer';
import { ActivityDrawer } from './components/ActivityDrawer';
import { SettingsModal } from './components/SettingsModal';
import { NeuralAudioClient } from './services/neuralAudio';
import {
  runAgUiAgentStream,
  fetchDesktopScreenshot,
  setDesktopMode,
  fetchWakeupBriefing,
  submitActionApproval
} from './services/api';
import {
  Sparkles,
  Moon,
  CheckCircle2,
  X,
  Network,
  Clock,
  ChevronDown,
  ChevronRight
} from 'lucide-react';

export function App() {
  const [activeTab, setActiveTab] = useState<WorkspaceTab>('chat');
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  type ActiveDrawer = 'none' | 'artifact' | 'vision' | 'activity';
  const [activeDrawer, setActiveDrawer] = useState<ActiveDrawer>('none');
  const isArtifactDrawerOpen = activeDrawer === 'artifact';
  const isVisionDrawerOpen = activeDrawer === 'vision';
  const isActivityDrawerOpen = activeDrawer === 'activity';
  const [activeActivityMessageId, setActiveActivityMessageId] = useState<string | null>(null);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isTurboMode, setIsTurboMode] = useState(false);
  const [activeModel, setActiveModel] = useState('gemini-3.5-flash-lite');
  const [activeSpecialist, setActiveSpecialist] = useState<AgentSpecialist>(SPECIALIST_AGENTS[0]);

  const [activeArtifact, setActiveArtifact] = useState<ArtifactItem | null>(null);
  const [wakeupBriefing, setWakeupBriefing] = useState<any | null>(null);
  const [isBriefingExpanded, setIsBriefingExpanded] = useState(false);
  const [isAutonomousControlActive, setIsAutonomousControlActive] = useState(false);
  const [activeToolName, setActiveToolName] = useState<string>('');

  const [computerUse, setComputerUse] = useState<ComputerUseState>({
    enabled: true,
    screenshotUrl: null,
    isCapturing: false,
    uiaBoxesVisible: true,
    failSafeTripped: false,
  });

  const [voiceState, setVoiceState] = useState<VoiceTalkState>({
    enabled: true,
    isConnected: false,
    isListening: false,
    isSpeaking: false,
    volume: 0,
    statusText: 'Neural Voice Ready (Aoede 24kHz)',
  });

  const [latestDag, setLatestDag] = useState<OrchestrationNode[]>([]);
  const [latestHandoffs, setLatestHandoffs] = useState<AgentHandoff[]>([]);
  const [expandedDagNodeId, setExpandedDagNodeId] = useState<string | null>(null);

  const getGreeting = () => {
    const hr = new Date().getHours();
    const salutation = hr < 12 ? 'Good morning' : hr < 17 ? 'Good afternoon' : 'Good evening';
    return `${salutation}, sir. I am **Dione**, your sovereign executive AI.\n\nAll six specialized sub-agent kernels, local Win32 computer-use hooks, and full-duplex neural voice channels are online. How may I be of service?`;
  };

  const STORAGE_KEY_THREADS = 'dione_threads_store_v1';
  const STORAGE_KEY_ACTIVE_THREAD = 'dione_active_thread_id_v1';

  const [threads, setThreads] = useState<Thread[]>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY_THREADS);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) {
          return parsed.map((t: Thread) => ({
            ...t,
            messages: (t.messages || [])
              .filter(m => !(m.role === 'assistant' && !m.content && m.isStreaming))
              .map(m => ({ ...m, isStreaming: false }))
          }));
        }
      }
    } catch (e) {
      console.warn('Failed to load threads from localStorage:', e);
    }
    return [
      {
        id: 'thread-1',
        title: 'Executive AI Session',
        createdAt: 'Now',
        updatedAt: 'Now',
        messages: [
          {
            id: 'welcome-msg',
            role: 'assistant',
            content: getGreeting(),
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          }
        ],
      }
    ];
  });

  const [activeThreadId, setActiveThreadId] = useState<string>(() => {
    try {
      const savedId = localStorage.getItem(STORAGE_KEY_ACTIVE_THREAD);
      if (savedId) return savedId;
    } catch (e) {}
    return 'thread-1';
  });

  const [hasHydrated, setHasHydrated] = useState(false);

  // Sync threads to localStorage and background file storage ONLY AFTER hydration
  useEffect(() => {
    if (!hasHydrated) return;
    try {
      localStorage.setItem(STORAGE_KEY_THREADS, JSON.stringify(threads));
      fetch('/api/chat/threads', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ threads }),
      }).catch(() => {});
    } catch (e) {
      console.warn('Failed to persist threads:', e);
    }
  }, [threads, hasHydrated]);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY_ACTIVE_THREAD, activeThreadId);
    } catch (e) {}
  }, [activeThreadId]);

  // Try hydrating from server if localStorage only had 1 thread with default message
  useEffect(() => {
    const hydrateFromServer = async () => {
      try {
        const res = await fetch('/api/chat/threads');
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data.threads) && data.threads.length > 0) {
            const sanitized = data.threads.map((t: Thread) => ({
              ...t,
              messages: (t.messages || [])
                .filter(m => !(m.role === 'assistant' && !m.content && m.isStreaming))
                .map(m => ({ ...m, isStreaming: false }))
            }));
            setThreads(prev => {
              if (prev.length <= 1 && (prev[0]?.messages?.length || 0) <= 1) {
                return sanitized;
              }
              return prev;
            });
          }
        }
      } catch (err) {
        console.warn('Background thread sync note:', err);
      } finally {
        setHasHydrated(true);
      }
    };
    hydrateFromServer();
  }, []);

  const chatBottomRef = useRef<HTMLDivElement>(null);
  const audioClientRef = useRef<NeuralAudioClient | null>(null);
  const activeThread = threads.find(t => t.id === activeThreadId) || threads[0] || {
    id: 'thread-1',
    title: 'Executive AI Session',
    createdAt: 'Now',
    updatedAt: 'Now',
    messages: []
  };

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [activeThread.messages, isLoading]);

  // Extract artifact from the latest assistant message if present
  useEffect(() => {
    const msgs = activeThread.messages;
    for (let i = msgs.length - 1; i >= 0; i--) {
      const m = msgs[i];
      if (m.role === 'assistant' && m.content) {
        const match = m.content.match(/```([a-zA-Z0-9_-]+)?\n([\s\S]*?)```/);
        if (match) {
          const lang = match[1] || 'txt';
          const code = match[2];
          setActiveArtifact({
            id: `artifact-${m.id}`,
            title: `generated_${lang}_script.${lang}`,
            language: lang,
            content: code,
            type: lang === 'html' ? 'html' : (lang === 'md' || lang === 'markdown' ? 'markdown' : 'code'),
          });
          break;
        }
      }
    }
  }, [activeThread.messages]);

  // Initialize Neural Audio Client
  useEffect(() => {
    audioClientRef.current = new NeuralAudioClient({
      onStateChange: (state) => {
        setVoiceState(prev => ({
          ...prev,
          isConnected: state.isConnected,
          isListening: state.isListening,
          isSpeaking: state.isSpeaking,
          volume: state.volume,
          statusText: state.statusText,
        }));
      },
      onTranscript: (text, isUser) => {
        if (isUser && text.trim()) {
          handleSendMessage(text);
        }
      },
      onError: (err) => {
        console.warn('[NeuralVoice] Error:', err);
      }
    });

    return () => {
      audioClientRef.current?.disconnect();
    };
  }, []);

  const toggleNeuralVoice = async () => {
    if (!audioClientRef.current) return;
    if (voiceState.isConnected) {
      audioClientRef.current.disconnect();
    } else {
      await audioClientRef.current.connect();
    }
  };

  const handleEmergencyAbort = async () => {
    try {
      await fetch('/api/desktop/abort', { method: 'POST' });
      setIsAutonomousControlActive(false);
      setActiveToolName('');
    } catch (err) {
      console.warn('Failed to dispatch abort:', err);
    }
  };

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isAutonomousControlActive) {
        handleEmergencyAbort();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isAutonomousControlActive]);

  const handleCaptureScreenshot = async () => {
    setComputerUse(prev => ({ ...prev, isCapturing: true }));
    const imgUrl = await fetchDesktopScreenshot();
    setComputerUse(prev => ({
      ...prev,
      screenshotUrl: imgUrl || prev.screenshotUrl,
      lastCaptureTime: new Date().toLocaleTimeString(),
      isCapturing: false,
    }));
  };

  const checkBriefing = async () => {
    const data = await fetchWakeupBriefing();
    if (data.available && data.briefing) {
      setWakeupBriefing(data.briefing);
    }
  };

  useEffect(() => {
    handleCaptureScreenshot();
    checkBriefing();
  }, []);

  const handleToggleComputerUse = async () => {
    const nextState = !computerUse.enabled;
    setComputerUse(prev => ({ ...prev, enabled: nextState }));
    await setDesktopMode(nextState ? 'computer_use' : 'ambient_cowork');
  };

  const handleDecideApproval = async (confirmationId: string, approved: boolean) => {
    try {
      await submitActionApproval(confirmationId, approved);
      setThreads(prev => prev.map(t => (
        t.id === activeThreadId
          ? {
              ...t,
              messages: t.messages.map(m =>
                m.approvalRequest?.confirmation_id === confirmationId
                  ? { ...m, approvalStatus: approved ? 'approved' : 'denied' }
                  : m
              )
            }
          : t
      )));
    } catch (err) {
      console.error('Error submitting approval:', err);
    }
  };

  const handleSendMessage = async (text: string) => {
    if (!text.trim() || isLoading) return;

    const userMsg: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    const assistantMsgId = `asst-${Date.now()}`;
    const initialAssistantMsg: Message = {
      id: assistantMsgId,
      role: 'assistant',
      content: '',
      isStreaming: true,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      toolCalls: [],
    };

    const activeThreadObj = threads.find(t => t.id === activeThreadId);
    const recentHistory = (activeThreadObj?.messages || [])
      .filter(m => m.role === 'user' || m.role === 'assistant')
      .slice(-12)
      .map(m => ({ role: m.role, content: m.content }));

    setThreads(prev => prev.map(t => {
      if (t.id === activeThreadId) {
        const isDefault = t.title === 'Executive AI Session' || t.title === 'New Session';
        const smartTitle = isDefault ? (text.length > 32 ? text.slice(0, 32) + '…' : text) : t.title;
        return {
          ...t,
          title: smartTitle,
          updatedAt: userMsg.timestamp,
          messages: [...t.messages, userMsg, initialAssistantMsg]
        };
      }
      return t;
    }));

    setIsLoading(true);
    let accumulatedText = '';

    try {
      await runAgUiAgentStream(text, activeThreadId, {
        onCustom: async ({ name, value }) => {
          if (name === 'safety_confirmation_required' && value) {
            const req = value as SafetyApprovalRequest;
            if (isTurboMode) {
              await submitActionApproval(req.confirmation_id, true);
            } else {
              setThreads(prev => prev.map(t => (
                t.id === activeThreadId
                  ? {
                      ...t,
                      messages: t.messages.map(m => (
                        m.id === assistantMsgId
                          ? { ...m, approvalRequest: req, approvalStatus: 'pending' }
                          : m
                      ))
                    }
                  : t
              )));
            }
          } else if (name === 'dione_orchestration_session' && value?.nodes) {
            setLatestDag(value.nodes.map((n: any) => ({
              id: n.id,
              badge: n.agent_badge || 'ORCH',
              agentName: n.agent_name || n.agent_role,
              title: n.title,
              tool: n.tool,
              status: n.status,
              latency: n.latency_ms || 0,
              tier: n.safety_tier || 'Tier 0',
              output: n.output || '',
            })));
            if (value.handoffs) {
              setLatestHandoffs(value.handoffs.map((h: any) => ({
                from: h.from_badge || h.from_agent,
                to: h.to_badge || h.to_agent,
                msg: h.message,
                time: h.timestamp,
              })));
            }
          }
        },
        onToolStart: ({ toolCallId, toolCallName }) => {
          const isComputerTool = toolCallName.toLowerCase().includes('computer') ||
            toolCallName.toLowerCase().includes('mouse') ||
            toolCallName.toLowerCase().includes('keyboard') ||
            toolCallName.toLowerCase().includes('screen') ||
            toolCallName.toLowerCase().includes('launch') ||
            toolCallName.toLowerCase().includes('click');
          if (isComputerTool) {
            setIsAutonomousControlActive(true);
            setActiveToolName(toolCallName);
            // Non-intrusive Autonomous Execution: Auto-minimize Dione window immediately
            if (typeof (window as any).electronAPI?.minimize === 'function') {
              (window as any).electronAPI.minimize();
            }
          }
          setThreads(prev => prev.map(t => (
            t.id === activeThreadId
              ? {
                  ...t,
                  messages: t.messages.map(m => (
                    m.id === assistantMsgId
                      ? {
                          ...m,
                          toolCalls: [
                            ...(m.toolCalls || []),
                            {
                              id: toolCallId,
                              tool: toolCallName,
                              params: {},
                              status: 'running',
                              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                            }
                          ]
                        }
                      : m
                  ))
                }
              : t
          )));
        },
        onToolArgs: ({ toolCallId, delta }) => {
          try {
            const params = JSON.parse(delta);
            setThreads(prev => prev.map(t => (
              t.id === activeThreadId
                ? {
                    ...t,
                    messages: t.messages.map(m => (
                      m.id === assistantMsgId && m.toolCalls
                        ? { ...m, toolCalls: m.toolCalls.map(tc => tc.id === toolCallId ? { ...tc, params } : tc) }
                        : m
                    ))
                  }
                : t
            )));
          } catch {}
        },
        onToolResult: ({ toolCallId, content, success, error }) => {
          const isFailed = success === false || Boolean(error) ||
            content?.toLowerCase().includes('command failed to execute') ||
            content?.toLowerCase().includes('exit code: 1') ||
            content?.toLowerCase().startsWith('error:') ||
            content?.toLowerCase().includes('safety rejected:');
          const status = isFailed ? 'error' : 'completed';

          setThreads(prev => prev.map(t => (
            t.id === activeThreadId
              ? {
                  ...t,
                  messages: t.messages.map(m => (
                    m.id === assistantMsgId && m.toolCalls
                      ? { ...m, toolCalls: m.toolCalls.map(tc => tc.id === toolCallId ? { ...tc, status, result: content } : tc) }
                      : m
                    ))
                }
              : t
          )));
        },
        onToolEnd: ({ toolCallId }) => {
          setIsAutonomousControlActive(false);
          setActiveToolName('');
          setThreads(prev => prev.map(t => (
            t.id === activeThreadId
              ? {
                  ...t,
                  messages: t.messages.map(m => (
                    m.id === assistantMsgId && m.toolCalls
                      ? { ...m, toolCalls: m.toolCalls.map(tc => tc.id === toolCallId ? { ...tc, status: tc.status === 'error' ? 'error' : 'completed' } : tc) }
                      : m
                  ))
                }
              : t
          )));
        },
        onTextDelta: (delta) => {
          accumulatedText += delta;
          setThreads(prev => prev.map(t => (
            t.id === activeThreadId
              ? { ...t, messages: t.messages.map(m => m.id === assistantMsgId ? { ...m, content: accumulatedText } : m) }
              : t
          )));
        },
        onTextEnd: () => {
          setThreads(prev => prev.map(t => (
            t.id === activeThreadId
              ? { ...t, messages: t.messages.map(m => m.id === assistantMsgId ? { ...m, isStreaming: false } : m) }
              : t
          )));
        },
        onRunFinished: () => {
          setIsAutonomousControlActive(false);
          setActiveToolName('');
          setThreads(prev => prev.map(t => (
            t.id === activeThreadId
              ? { ...t, messages: t.messages.map(m => m.id === assistantMsgId ? { ...m, isStreaming: false } : m) }
              : t
          )));
          handleCaptureScreenshot();
        },
        onError: (err) => {
          setIsAutonomousControlActive(false);
          setActiveToolName('');
          setThreads(prev => prev.map(t => (
            t.id === activeThreadId
              ? {
                  ...t,
                  messages: t.messages.map(m => m.id === assistantMsgId ? { ...m, content: `Error: ${err}`, isStreaming: false } : m)
                }
              : t
          )));
        }
      }, undefined, recentHistory);
    } catch (err: any) {
      console.error('Agent stream failed:', err);
      setThreads(prev => prev.map(t => (
        t.id === activeThreadId
          ? {
              ...t,
              messages: t.messages.map(m => m.id === assistantMsgId ? {
                ...m,
                content: accumulatedText || `Connection interrupted: ${err?.message || err}. Please try again.`,
                isStreaming: false
              } : m)
            }
          : t
      )));
    } finally {
      setIsLoading(false);
    }
  };

  const handleStartSpecialistSession = (specialist: AgentSpecialist, prompt?: string) => {
    setActiveSpecialist(specialist);
    const id = `thread-${Date.now()}`;
    const newThread: Thread = {
      id,
      title: `${specialist.name} Session`,
      createdAt: 'Now',
      updatedAt: 'Now',
      messages: [
        {
          id: `spec-welcome-${Date.now()}`,
          role: 'assistant',
          content: `**${specialist.name}** online.\n\n${specialist.tagline}\n\n${specialist.description}\n\nHow can I assist you with ${specialist.role.toLowerCase()}?`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        }
      ]
    };
    setThreads(prev => [newThread, ...prev]);
    setActiveThreadId(id);
    setActiveTab('chat');

    if (prompt) {
      setTimeout(() => {
        handleSendMessage(prompt);
      }, 300);
    }
  };

  return (
    <div className="flex h-screen w-screen bg-[#06070d] text-slate-100 overflow-hidden font-sans antialiased relative">
      {/* Floating Top-Center Autonomous Computer Control HUD */}
      {isAutonomousControlActive && (
        <div className="fixed top-4 left-1/2 -translate-x-1/2 z-50 flex items-center gap-4 px-6 py-2.5 rounded-full bg-[#0a0d1a]/95 border border-purple-500/60 shadow-[0_0_35px_rgba(168,85,247,0.5)] backdrop-blur-2xl transition-all duration-300">
          <div className="relative flex h-3.5 w-3.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-purple-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3.5 w-3.5 bg-purple-500"></span>
          </div>
          <div className="flex flex-col">
            <span className="text-[11px] font-black uppercase tracking-wider text-white flex items-center gap-2">
              <span>Dione Autonomous Control Active</span>
              <span className="px-1.5 py-0.5 rounded bg-red-500/20 border border-red-500/40 text-red-400 text-[9px]">
                Lock Engaged
              </span>
            </span>
            <span className="text-[10px] text-slate-300">
              Action: <span className="font-mono text-purple-300 font-semibold">{activeToolName || 'Computer Action'}</span> &bull; Hands off mouse & keyboard
            </span>
          </div>
          <button
            onClick={handleEmergencyAbort}
            className="ml-2 px-3 py-1 rounded-lg bg-red-500/20 hover:bg-red-500/30 border border-red-500/50 text-red-300 text-[10px] font-bold uppercase tracking-wider transition-all"
            title="Abort autonomous control (Esc)"
          >
            Abort (Esc)
          </button>
        </div>
      )}

      {/* Input shield when autonomous control is active */}
      {isAutonomousControlActive && (
        <div className="fixed inset-0 z-40 bg-black/30 backdrop-blur-[1px] cursor-not-allowed pointer-events-auto" />
      )}

      {/* 1. Leftmost Sovereign Activity Navigation Rail */}
      <NavigationRail
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        isTurboMode={isTurboMode}
        onToggleTurbo={() => setIsTurboMode(!isTurboMode)}
        isVoiceActive={voiceState.isConnected}
        onToggleVoice={toggleNeuralVoice}
        onOpenSettings={() => setIsSettingsOpen(true)}
        threadCount={threads.length}
        hasDreamBriefing={!!wakeupBriefing}
        isAutonomousActive={isAutonomousControlActive}
      />

      {/* 2. Primary Workspace Body */}
      <div className="flex-1 flex h-full overflow-hidden">
        {/* TAB 1: Chat Studio */}
        {activeTab === 'chat' && (
          <div className="flex-1 flex h-full overflow-hidden">
            {/* Session Sidebar Drawer */}
            <Sidebar
              threads={threads}
              activeThreadId={activeThreadId}
              onSelectThread={setActiveThreadId}
              onNewThread={() => {
                const id = `thread-${Date.now()}`;
                setThreads(p => [{ id, title: 'New Session', createdAt: 'Now', updatedAt: 'Now', messages: [] }, ...p]);
                setActiveThreadId(id);
              }}
              onDeleteThread={(id) => {
                if (threads.length <= 1) return;
                setThreads(p => p.filter(t => t.id !== id));
              }}
              isOpen={isSidebarOpen}
              onToggle={() => setIsSidebarOpen(false)}
              onDreamTriggered={() => checkBriefing()}
            />

            {/* Central Chat Stream */}
            <div className="flex-1 flex flex-col h-full overflow-hidden bg-[#07080f]/95 relative">
              <ChatHeader
                activeSpecialist={activeSpecialist}
                onSelectSpecialist={setActiveSpecialist}
                activeModel={activeModel}
                onSelectModel={setActiveModel}
                isSidebarOpen={isSidebarOpen}
                onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
                isArtifactDrawerOpen={isArtifactDrawerOpen}
                onToggleArtifactDrawer={() => setActiveDrawer(prev => prev === 'artifact' ? 'none' : 'artifact')}
                hasArtifact={!!activeArtifact}
                isVisionDrawerOpen={isVisionDrawerOpen}
                onToggleVisionDrawer={() => setActiveDrawer(prev => prev === 'vision' ? 'none' : 'vision')}
                isActivityDrawerOpen={isActivityDrawerOpen}
                onToggleActivityDrawer={() => setActiveDrawer(prev => prev === 'activity' ? 'none' : 'activity')}
                activityCount={activeThread?.messages?.reduce((acc, m) => acc + (m.toolCalls?.length || 0), 0) || 0}
                onClearThread={() => {
                  setThreads(prev => prev.map(t => t.id === activeThreadId ? { ...t, messages: [] } : t));
                }}
                isTurboMode={isTurboMode}
                onToggleTurbo={() => setIsTurboMode(!isTurboMode)}
              />

              {/* Chat Messages */}
              <div className="flex-1 overflow-y-auto px-4 py-6 space-y-6 max-w-4xl w-full mx-auto">
                {activeThread.messages.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-full text-center py-24 space-y-3">
                    <div className={`w-12 h-12 rounded-2xl bg-gradient-to-tr ${activeSpecialist.gradient} flex items-center justify-center text-white font-bold text-base shadow-xl`}>
                      {activeSpecialist.badge}
                    </div>
                    <h2 className="text-base font-bold text-white">
                      {activeSpecialist.name}
                    </h2>
                    <p className="text-xs text-slate-400 max-w-md leading-relaxed">
                      {activeSpecialist.tagline}
                    </p>
                    <div className="flex flex-wrap justify-center gap-2 pt-2 max-w-lg">
                      {activeSpecialist.suggestedPrompts.map((p, idx) => (
                        <button
                          key={idx}
                          onClick={() => handleSendMessage(p)}
                          className="px-3 py-1.5 rounded-xl bg-white/[0.03] hover:bg-white/[0.08] border border-white/[0.06] text-xs text-slate-300 hover:text-white transition-all text-left"
                        >
                          {p}
                        </button>
                      ))}
                    </div>
                  </div>
                ) : (
                  activeThread.messages.map(message => (
                    <MessageView
                      key={message.id}
                      message={message}
                      onDecideApproval={handleDecideApproval}
                      onOpenActivity={(msgId) => {
                        setActiveActivityMessageId(msgId);
                        setActiveDrawer('activity');
                      }}
                    />
                  ))
                )}
                <div ref={chatBottomRef} />
              </div>

              {/* Composer */}
              <Composer
                onSend={handleSendMessage}
                isLoading={isLoading}
                computerUseEnabled={computerUse.enabled}
                onToggleComputerUse={handleToggleComputerUse}
                isListening={voiceState.isListening}
                onToggleMic={toggleNeuralVoice}
              />
            </div>

            {/* Artifact Drawer (Slides in on right) */}
            <ArtifactDrawer
              isOpen={isArtifactDrawerOpen}
              onClose={() => setActiveDrawer('none')}
              artifact={activeArtifact}
            />

            {/* Vision Controls Drawer (Slides in on right) */}
            <ComputerUseDrawer
              isOpen={isVisionDrawerOpen}
              onClose={() => setActiveDrawer('none')}
              screenshotUrl={computerUse.screenshotUrl}
              onRefresh={handleCaptureScreenshot}
              isCapturing={computerUse.isCapturing || false}
              lastCaptureTime={computerUse.lastCaptureTime}
            />

            {/* Workstation Activity Drawer (Grouped by Prompt in Execution Order) */}
            <ActivityDrawer
              isOpen={isActivityDrawerOpen}
              onClose={() => setActiveDrawer('none')}
              thread={activeThread}
              targetMessageId={activeActivityMessageId}
            />
          </div>
        )}

        {/* TAB 2: Agent Fleet & Marketplace */}
        {activeTab === 'agents' && (
          <AgentMarketplace onSelectSpecialist={handleStartSpecialistSession} />
        )}

        {/* TAB 3: Dedicated Computer Use Desk */}
        {activeTab === 'computer-use' && (
          <ComputerUseDesk
            computerUse={computerUse}
            onRefreshScreenshot={handleCaptureScreenshot}
            onToggleGrid={() => {}}
            onLaunchGame={(game) => {
              handleSendMessage(`Launch ${game} and inspect the workstation display.`);
              setActiveTab('chat');
            }}
            isAutonomousActive={isAutonomousControlActive}
          />
        )}

        {/* TAB 4: Memory & Knowledge Graph */}
        {activeTab === 'knowledge' && (
          <KnowledgeGraphView onTriggerDream={checkBriefing} />
        )}

        {/* TAB 5: Scout & Dream Journal */}
        {activeTab === 'dream' && (
          <div className="flex-1 overflow-y-auto p-8 space-y-6 max-w-5xl w-full mx-auto bg-[#090a12] text-slate-200">
            <div className="flex items-center justify-between pb-2 border-b border-white/[0.06]">
              <div>
                <span className="px-2.5 py-0.5 rounded-full bg-purple-500/20 border border-purple-500/30 text-purple-300 text-xs font-mono font-semibold flex items-center gap-1.5 inline-flex mb-2">
                  <Moon className="w-3.5 h-3.5" />
                  <span>Autonomous Inactivity Monitor</span>
                </span>
                <h1 className="text-xl font-bold text-white tracking-tight">
                  Scout Journal & While-You-Were-Away Briefings
                </h1>
                <p className="text-xs text-slate-300">
                  Dione continuously grounds un-grounded concepts in arXiv and DuckDuckGo when your workstation is idle.
                </p>
              </div>
            </div>

            {wakeupBriefing ? (
              <div className="p-6 rounded-2xl border border-violet-500/30 bg-white/[0.02] backdrop-blur-xl space-y-4 shadow-2xl">
                <div className="flex items-center justify-between">
                  <span className="text-base font-bold text-white flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-violet-400" />
                    {wakeupBriefing.title}
                  </span>
                  <span className="text-xs font-mono text-slate-400">{wakeupBriefing.timestamp}</span>
                </div>
                <p className="text-xs text-slate-200 leading-relaxed bg-[#060810] p-4 rounded-xl border border-white/5">
                  {wakeupBriefing.summary}
                </p>
                {wakeupBriefing.topics_researched && (
                  <div className="space-y-2">
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                      Scouted Concepts:
                    </span>
                    <div className="flex flex-wrap gap-2">
                      {wakeupBriefing.topics_researched.map((t: string) => (
                        <span key={t} className="px-3 py-1 rounded-lg bg-pink-500/10 border border-pink-500/30 text-pink-300 text-xs font-mono">
                          {t}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="p-12 rounded-2xl border border-white/[0.06] bg-white/[0.01] text-center text-slate-400 text-xs space-y-2">
                <Moon className="w-8 h-8 mx-auto text-purple-400/50" />
                <p>No new idle briefing. The scout engine triggers automatically after 5 minutes of workstation inactivity.</p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Settings Modal */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        activeModel={activeModel}
        onSelectModel={setActiveModel}
        isTurboMode={isTurboMode}
        onToggleTurbo={() => setIsTurboMode(!isTurboMode)}
        onClearAllThreads={() => {
          setThreads([
            {
              id: 'thread-1',
              title: 'Executive AI Session',
              createdAt: 'Now',
              updatedAt: 'Now',
              messages: [{ id: 'welcome-msg', role: 'assistant', content: getGreeting(), timestamp: 'Now' }],
            }
          ]);
          setActiveThreadId('thread-1');
          setIsSettingsOpen(false);
        }}
        threadCount={threads.length}
      />
    </div>
  );
}

export default App;
