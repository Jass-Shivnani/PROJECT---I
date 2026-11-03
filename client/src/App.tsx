import React, { useState, useEffect, useRef } from 'react';
import {
  Thread,
  Message,
  ComputerUseState,
  VoiceTalkState,
  SafetyApprovalRequest
} from './types';
import { NavigationRail, WorkspaceTab } from './components/NavigationRail';
import { Sidebar } from './components/Sidebar';
import { ChatHeader } from './components/ChatHeader';
import { MessageView } from './components/MessageView';
import { Composer } from './components/Composer';
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
  submitActionApproval
} from './services/api';

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

  const [activeArtifact, setActiveArtifact] = useState<ArtifactItem | null>(null);
  const [isAutonomousControlActive, setIsAutonomousControlActive] = useState(false);
  const [activeToolName, setActiveToolName] = useState<string>('');

  const [selectedMicId, setSelectedMicId] = useState<string>(
    () => localStorage.getItem('dione_selected_mic_device_id_v1') || ''
  );
  const [selectedSpeakerId, setSelectedSpeakerId] = useState<string>(
    () => localStorage.getItem('dione_selected_speaker_device_id_v1') || ''
  );

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
    statusText: 'Live Voice + Gemini 3.8 Thinking Ready',
  });

  const getGreeting = () => {
    const hr = new Date().getHours();
    const salutation = hr < 12 ? 'Good morning' : hr < 17 ? 'Good afternoon' : 'Good evening';
    return `${salutation}. I am **Dione**, connected to your Windows 11 desktop, knowledge graph, and external services (Gmail, Calendar, Drive, Photos, WhatsApp, Telegram, Slack, Instagram). How can I help?`;
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
    } catch {}
    return [
      {
        id: 'thread-1',
        title: 'Main Session',
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
      return localStorage.getItem(STORAGE_KEY_ACTIVE_THREAD) || 'thread-1';
    } catch {
      return 'thread-1';
    }
  });

  const [hasHydrated, setHasHydrated] = useState(false);

  useEffect(() => {
    if (!hasHydrated) return;
    try {
      localStorage.setItem(STORAGE_KEY_THREADS, JSON.stringify(threads));
      fetch('/api/chat/threads', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ threads }),
      }).catch(() => {});
    } catch {}
  }, [threads, hasHydrated]);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY_ACTIVE_THREAD, activeThreadId);
    } catch {}
  }, [activeThreadId]);

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
      } catch {} finally {
        setHasHydrated(true);
      }
    };
    hydrateFromServer();
  }, []);

  const chatBottomRef = useRef<HTMLDivElement>(null);
  const audioClientRef = useRef<NeuralAudioClient | null>(null);
  const activeThread = threads.find(t => t.id === activeThreadId) || threads[0] || {
    id: 'thread-1',
    title: 'Main Session',
    createdAt: 'Now',
    updatedAt: 'Now',
    messages: []
  };

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [activeThread.messages, isLoading]);

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
            title: `snippet.${lang}`,
            language: lang,
            content: code,
            type: lang === 'html' ? 'html' : (lang === 'md' || lang === 'markdown' ? 'markdown' : 'code'),
          });
          break;
        }
      }
    }
  }, [activeThread.messages]);

  // Initialize Neural Audio Client with hardware device support & Gemini 3.8 Extended Thinking callbacks
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
        if (state.selectedMicId) {
          setSelectedMicId(state.selectedMicId);
        }
      },
      onTranscript: (text, isUser) => {
        if (!text.trim()) return;
        const msg: Message = {
          id: `voice-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
          role: isUser ? 'user' : 'assistant',
          content: text.trim(),
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        };
        setThreads(prev => prev.map(t => (
          t.id === activeThreadId ? { ...t, messages: [...t.messages, msg] } : t
        )));
      },
      onThought: (thoughtText, model) => {
        if (!thoughtText.trim()) return;
        const msg: Message = {
          id: `thought-${Date.now()}`,
          role: 'assistant',
          content: `> **[${model} Extended Thinking]**\n> ${thoughtText.trim().replace(/\n/g, '\n> ')}`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        };
        setThreads(prev => prev.map(t => (
          t.id === activeThreadId ? { ...t, messages: [...t.messages, msg] } : t
        )));
      },
      onError: (err) => {
        console.warn('[NeuralVoice] Error:', err);
      }
    });

    return () => {
      audioClientRef.current?.disconnect();
    };
  }, [activeThreadId]);

  const toggleNeuralVoice = async () => {
    if (!audioClientRef.current) return;
    if (voiceState.isConnected) {
      audioClientRef.current.disconnect();
    } else {
      await audioClientRef.current.connect(selectedMicId);
    }
  };

  const handleSelectMic = async (deviceId: string) => {
    setSelectedMicId(deviceId);
    await audioClientRef.current?.setMicDevice(deviceId);
  };

  const handleSelectSpeaker = async (deviceId: string) => {
    setSelectedSpeakerId(deviceId);
    await audioClientRef.current?.setSpeakerDevice(deviceId);
  };

  const handleEmergencyAbort = async () => {
    try {
      await fetch('/api/desktop/abort', { method: 'POST' });
      setIsAutonomousControlActive(false);
      setActiveToolName('');
    } catch {}
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

  useEffect(() => {
    handleCaptureScreenshot();
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
    } catch {}
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
      .slice(-8)
      .map(m => ({ role: m.role, content: m.content.slice(0, 1200) }));

    setThreads(prev => prev.map(t => {
      if (t.id === activeThreadId) {
        const isDefault = t.title === 'Main Session' || t.title === 'Executive AI Session' || t.title === 'New Session';
        const smartTitle = isDefault ? (text.length > 34 ? text.slice(0, 34) + '…' : text) : t.title;
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
          }
        },
        onToolStart: ({ toolCallId, toolCallName }) => {
          const isClickTool =
            toolCallName === 'computer_locate_and_click' ||
            toolCallName === 'computer_click';
          if (isClickTool) {
            setIsAutonomousControlActive(true);
            setActiveToolName(toolCallName);
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
          const isFailed = success === false || Boolean(error) || content?.toLowerCase().startsWith('error:');
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
      }, undefined, recentHistory, activeModel);
    } catch (err: any) {
      setThreads(prev => prev.map(t => (
        t.id === activeThreadId
          ? {
              ...t,
              messages: t.messages.map(m => m.id === assistantMsgId ? {
                ...m,
                content: accumulatedText || `Connection interrupted: ${err?.message || err}`,
                isStreaming: false
              } : m)
            }
          : t
      )));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-screen w-screen bg-[#06070d] text-slate-100 overflow-hidden font-sans antialiased relative">
      {/* Compact Non-Blocking Top-Right Autonomous Action Pill */}
      {isAutonomousControlActive && (
        <div className="fixed top-3 right-4 z-50 flex items-center gap-3 px-4 py-2 rounded-xl bg-[#0c0f1d]/95 border border-cyan-500/50 shadow-xl backdrop-blur-xl">
          <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
          <span className="text-xs font-mono text-cyan-200">
            Desktop Action: <strong>{activeToolName}</strong>
          </span>
          <button
            onClick={handleEmergencyAbort}
            className="px-2 py-0.5 rounded bg-red-500/20 hover:bg-red-500/30 border border-red-500/40 text-red-300 text-[10px] font-bold uppercase"
          >
            Abort (Esc)
          </button>
        </div>
      )}

      {/* 1. Leftmost Navigation Rail (3 Focused Workspaces) */}
      <NavigationRail
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        isTurboMode={isTurboMode}
        onToggleTurbo={() => setIsTurboMode(!isTurboMode)}
        isVoiceActive={voiceState.isConnected}
        onToggleVoice={toggleNeuralVoice}
        onOpenSettings={() => setIsSettingsOpen(true)}
        threadCount={threads.length}
        isAutonomousActive={isAutonomousControlActive}
      />

      {/* 2. Primary Workspace Body */}
      <div className="flex-1 flex h-full overflow-hidden">
        {activeTab === 'chat' && (
          <div className="flex-1 flex h-full overflow-hidden">
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
            />

            <div className="flex-1 flex flex-col h-full overflow-hidden bg-[#07080f]/95 relative">
              <ChatHeader
                activeModel={activeModel}
                onSelectModel={setActiveModel}
                isSidebarOpen={isSidebarOpen}
                onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
                isArtifactDrawerOpen={isArtifactDrawerOpen}
                onToggleArtifactDrawer={() => setActiveDrawer(prev => prev === 'artifact' ? 'none' : 'artifact')}
                hasArtifact={!!activeArtifact}
                isVisionDrawerOpen={isVisionDrawerOpen}
                onToggleVisionDrawer={() => {
                  handleCaptureScreenshot();
                  setActiveDrawer(prev => prev === 'vision' ? 'none' : 'vision');
                }}
                isActivityDrawerOpen={isActivityDrawerOpen}
                onToggleActivityDrawer={() => setActiveDrawer(prev => prev === 'activity' ? 'none' : 'activity')}
                activityCount={activeThread?.messages?.reduce((acc, m) => acc + (m.toolCalls?.length || 0), 0) || 0}
                onClearThread={() => {
                  setThreads(prev => prev.map(t => t.id === activeThreadId ? { ...t, messages: [] } : t));
                }}
                isTurboMode={isTurboMode}
                onToggleTurbo={() => setIsTurboMode(!isTurboMode)}
              />

              <div className="flex-1 overflow-y-auto px-4 py-6 space-y-5 max-w-4xl w-full mx-auto">
                {activeThread.messages.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-full text-center py-20 space-y-3">
                    <div className="w-11 h-11 rounded-2xl bg-gradient-to-tr from-violet-600 to-indigo-500 flex items-center justify-center text-white font-bold text-base shadow-lg">
                      D
                    </div>
                    <h2 className="text-base font-bold text-white">Dione Sovereign Assistant</h2>
                    <p className="text-xs text-slate-400 max-w-md">
                      Ask anything, control Windows 11 apps, or manage Gmail, Calendar, Drive, WhatsApp, Telegram, and Slack.
                    </p>
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

              <Composer
                onSend={handleSendMessage}
                isLoading={isLoading}
                computerUseEnabled={computerUse.enabled}
                onToggleComputerUse={handleToggleComputerUse}
                isListening={voiceState.isConnected}
                voiceStatusText={voiceState.statusText}
                voiceVolume={voiceState.volume}
                selectedMicId={selectedMicId}
                onSelectMic={handleSelectMic}
                onToggleMic={toggleNeuralVoice}
              />
            </div>

            <ArtifactDrawer
              isOpen={isArtifactDrawerOpen}
              onClose={() => setActiveDrawer('none')}
              artifact={activeArtifact}
            />

            <ComputerUseDrawer
              isOpen={isVisionDrawerOpen}
              onClose={() => setActiveDrawer('none')}
              screenshotUrl={computerUse.screenshotUrl}
              onRefresh={handleCaptureScreenshot}
              isCapturing={computerUse.isCapturing || false}
              lastCaptureTime={computerUse.lastCaptureTime}
            />

            <ActivityDrawer
              isOpen={isActivityDrawerOpen}
              onClose={() => setActiveDrawer('none')}
              thread={activeThread}
              targetMessageId={activeActivityMessageId}
            />
          </div>
        )}

        {activeTab === 'computer-use' && (
          <ComputerUseDesk
            computerUse={computerUse}
            onRefreshScreenshot={handleCaptureScreenshot}
            onToggleGrid={() => {}}
            onLaunchApp={(app) => {
              handleSendMessage(`Launch or focus ${app}`);
              setActiveTab('chat');
            }}
            isAutonomousActive={isAutonomousControlActive}
          />
        )}

        {activeTab === 'knowledge' && (
          <KnowledgeGraphView onTriggerDream={() => {}} />
        )}
      </div>

      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        activeModel={activeModel}
        onSelectModel={setActiveModel}
        isTurboMode={isTurboMode}
        onToggleTurbo={() => setIsTurboMode(!isTurboMode)}
        selectedMicId={selectedMicId}
        onSelectMic={handleSelectMic}
        selectedSpeakerId={selectedSpeakerId}
        onSelectSpeaker={handleSelectSpeaker}
        onClearAllThreads={() => {
          setThreads([
            {
              id: 'thread-1',
              title: 'Main Session',
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
