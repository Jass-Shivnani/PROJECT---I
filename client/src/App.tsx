import React, { useState, useEffect, useRef } from 'react';
import { 
  PanelLeft, 
  Monitor, 
  Trash2, 
  RotateCcw, 
  Sparkles,
  Bot
} from 'lucide-react';
import { Thread, Message, ToolCall, ComputerUseState } from './types';
import { Sidebar } from './components/Sidebar';
import { MessageView } from './components/MessageView';
import { Composer } from './components/Composer';
import { ComputerUseDrawer } from './components/ComputerUseDrawer';
import { 
  runAgUiAgentStream, 
  fetchDesktopScreenshot, 
  setDesktopMode 
} from './services/api';

export function App() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // Computer Use state
  const [computerUse, setComputerUse] = useState<ComputerUseState>({
    enabled: true,
    screenshotUrl: null,
    isCapturing: false,
  });

  // Threads
  const [threads, setThreads] = useState<Thread[]>([
    {
      id: 'thread-1',
      title: 'Workspace Session',
      createdAt: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      updatedAt: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      messages: [
        {
          id: 'welcome-msg',
          role: 'assistant',
          content: 'Hello Jass. I am Dione, your autonomous Large Action Model built on the Microsoft Agent Framework.\n\nI have native access to your Windows desktop, filesystem, SQLite databases, web research, Telegram, and Gmail. Computer Use mode is currently active.',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        }
      ],
    }
  ]);
  const [activeThreadId, setActiveThreadId] = useState('thread-1');

  const chatBottomRef = useRef<HTMLDivElement>(null);
  const activeThread = threads.find(t => t.id === activeThreadId) || threads[0];

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [activeThread.messages, isLoading]);

  // Initial desktop perception screenshot
  const handleCaptureScreenshot = async () => {
    setComputerUse(prev => ({ ...prev, isCapturing: true }));
    const imgUrl = await fetchDesktopScreenshot();
    if (imgUrl) {
      setComputerUse(prev => ({
        ...prev,
        screenshotUrl: imgUrl,
        lastCaptureTime: new Date().toLocaleTimeString(),
        isCapturing: false,
      }));
    } else {
      setComputerUse(prev => ({ ...prev, isCapturing: false }));
    }
  };

  useEffect(() => {
    handleCaptureScreenshot();
  }, []);

  const handleToggleComputerUse = async () => {
    const nextState = !computerUse.enabled;
    setComputerUse(prev => ({ ...prev, enabled: nextState }));
    await setDesktopMode(nextState ? 'computer_use' : 'ambient_cowork');
    if (nextState && !computerUse.screenshotUrl) {
      handleCaptureScreenshot();
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

    setThreads(prev => prev.map(t => {
      if (t.id === activeThreadId) {
        return {
          ...t,
          updatedAt: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          messages: [...t.messages, userMsg, initialAssistantMsg],
        };
      }
      return t;
    }));

    setIsLoading(true);
    let accumulatedText = '';

    try {
      await runAgUiAgentStream(text, activeThreadId, {
        onToolStart: ({ toolCallId, toolCallName }) => {
          setThreads(prev => prev.map(t => {
            if (t.id === activeThreadId) {
              return {
                ...t,
                messages: t.messages.map(m => {
                  if (m.id === assistantMsgId) {
                    const calls = m.toolCalls || [];
                    return {
                      ...m,
                      toolCalls: [
                        ...calls,
                        {
                          id: toolCallId,
                          tool: toolCallName,
                          params: {},
                          status: 'running',
                          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                        }
                      ]
                    };
                  }
                  return m;
                })
              };
            }
            return t;
          }));
        },
        onToolArgs: ({ toolCallId, delta }) => {
          try {
            const params = JSON.parse(delta);
            setThreads(prev => prev.map(t => {
              if (t.id === activeThreadId) {
                return {
                  ...t,
                  messages: t.messages.map(m => {
                    if (m.id === assistantMsgId && m.toolCalls) {
                      return {
                        ...m,
                        toolCalls: m.toolCalls.map(tc => tc.id === toolCallId ? { ...tc, params } : tc)
                      };
                    }
                    return m;
                  })
                };
              }
              return t;
            }));
          } catch {}
        },
        onToolResult: ({ toolCallId, content }) => {
          setThreads(prev => prev.map(t => {
            if (t.id === activeThreadId) {
              return {
                ...t,
                messages: t.messages.map(m => {
                  if (m.id === assistantMsgId && m.toolCalls) {
                    return {
                      ...m,
                      toolCalls: m.toolCalls.map(tc => tc.id === toolCallId ? { ...tc, status: 'completed', result: content } : tc)
                    };
                  }
                  return m;
                })
              };
            }
            return t;
          }));
        },
        onToolEnd: ({ toolCallId }) => {
          setThreads(prev => prev.map(t => {
            if (t.id === activeThreadId) {
              return {
                ...t,
                messages: t.messages.map(m => {
                  if (m.id === assistantMsgId && m.toolCalls) {
                    return {
                      ...m,
                      toolCalls: m.toolCalls.map(tc => tc.id === toolCallId ? { ...tc, status: 'completed' } : tc)
                    };
                  }
                  return m;
                })
              };
            }
            return t;
          }));
        },
        onTextDelta: (delta) => {
          accumulatedText += delta;
          setThreads(prev => prev.map(t => {
            if (t.id === activeThreadId) {
              return {
                ...t,
                messages: t.messages.map(m => m.id === assistantMsgId ? { ...m, content: accumulatedText } : m)
              };
            }
            return t;
          }));
        },
        onTextEnd: () => {
          setThreads(prev => prev.map(t => {
            if (t.id === activeThreadId) {
              return {
                ...t,
                messages: t.messages.map(m => m.id === assistantMsgId ? { ...m, isStreaming: false } : m)
              };
            }
            return t;
          }));
        },
        onRunFinished: () => {
          setThreads(prev => prev.map(t => {
            if (t.id === activeThreadId) {
              return {
                ...t,
                messages: t.messages.map(m => m.id === assistantMsgId ? { ...m, isStreaming: false } : m)
              };
            }
            return t;
          }));
          // If a desktop or vision action occurred, refresh screenshot
          if (text.toLowerCase().includes('screen') || text.toLowerCase().includes('open') || text.toLowerCase().includes('app') || text.toLowerCase().includes('click')) {
            setTimeout(handleCaptureScreenshot, 1000);
          }
        },
        onError: (err) => {
          setThreads(prev => prev.map(t => {
            if (t.id === activeThreadId) {
              return {
                ...t,
                messages: t.messages.map(m => m.id === assistantMsgId ? {
                  ...m,
                  content: m.content ? `${m.content}\n\n[Error: ${err}]` : `Error: ${err}`,
                  isStreaming: false
                } : m)
              };
            }
            return t;
          }));
        }
      });
    } catch (err: any) {
      setThreads(prev => prev.map(t => {
        if (t.id === activeThreadId) {
          return {
            ...t,
            messages: t.messages.map(m => m.id === assistantMsgId ? {
              ...m,
              content: `Error executing task: ${err.message}`,
              isStreaming: false
            } : m)
          };
        }
        return t;
      }));
    } finally {
      setIsLoading(false);
    }
  };

  const handleNewThread = () => {
    const newId = `thread-${Date.now()}`;
    const newThread: Thread = {
      id: newId,
      title: 'New Session',
      createdAt: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      updatedAt: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      messages: [],
    };
    setThreads(prev => [newThread, ...prev]);
    setActiveThreadId(newId);
  };

  const handleDeleteThread = (id: string) => {
    if (threads.length <= 1) return;
    const remaining = threads.filter(t => t.id !== id);
    setThreads(remaining);
    if (activeThreadId === id) {
      setActiveThreadId(remaining[0].id);
    }
  };

  const handleClearChat = () => {
    setThreads(prev => prev.map(t => {
      if (t.id === activeThreadId) {
        return { ...t, messages: [] };
      }
      return t;
    }));
  };

  return (
    <div className="flex h-screen w-screen bg-[#111216] text-[#e4e5e9] overflow-hidden font-sans">
      {/* 1. Left Navigation Sidebar */}
      <Sidebar
        threads={threads}
        activeThreadId={activeThreadId}
        onSelectThread={setActiveThreadId}
        onNewThread={handleNewThread}
        onDeleteThread={handleDeleteThread}
        isOpen={isSidebarOpen}
        onToggle={() => setIsSidebarOpen(false)}
      />

      {/* 2. Main Workspace Canvas */}
      <div className="flex-1 flex flex-col h-full overflow-hidden bg-[#14151b]">
        {/* Top Header */}
        <header className="h-12 border-b border-[#22242c] bg-[#121319]/90 backdrop-blur-sm px-4 flex items-center justify-between flex-shrink-0 z-10 select-none">
          <div className="flex items-center gap-2">
            {!isSidebarOpen && (
              <button
                onClick={() => setIsSidebarOpen(true)}
                className="p-1.5 rounded hover:bg-[#1f212a] text-[#717585] hover:text-white transition-colors"
                title="Open sidebar"
              >
                <PanelLeft className="w-4 h-4" />
              </button>
            )}
            <span className="font-semibold text-xs text-[#dcdfe7] truncate max-w-xs">
              {activeThread.title}
            </span>
          </div>

          {/* Right Header Actions */}
          <div className="flex items-center gap-2">
            {/* Computer Use Status Toggle */}
            <button
              onClick={handleToggleComputerUse}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
                computerUse.enabled
                  ? 'bg-indigo-600/20 border border-indigo-500/40 text-indigo-300'
                  : 'text-[#696d7c] hover:bg-[#1c1d25]'
              }`}
              title="Toggle native Windows Computer Use mode"
            >
              <Monitor className="w-3.5 h-3.5 text-indigo-400" />
              <span>Computer Use</span>
              <span className={`w-1.5 h-1.5 rounded-full ${computerUse.enabled ? 'bg-indigo-400 animate-pulse' : 'bg-[#555866]'}`} />
            </button>

            {/* Desktop Vision Drawer Button */}
            <button
              onClick={() => setIsDrawerOpen(!isDrawerOpen)}
              className={`p-1.5 rounded text-xs transition-colors ${
                isDrawerOpen
                  ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30'
                  : 'text-[#717585] hover:text-white hover:bg-[#1f212a]'
              }`}
              title="Toggle Desktop Vision Preview"
            >
              <Monitor className="w-4 h-4" />
            </button>

            {/* Clear Chat */}
            <button
              onClick={handleClearChat}
              className="p-1.5 rounded text-[#717585] hover:text-red-400 hover:bg-[#1f212a] transition-colors"
              title="Clear active conversation"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        </header>

        {/* Center Chat Messages Container */}
        <div className="flex-1 overflow-y-auto px-4 py-6 flex flex-col">
          {activeThread.messages.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center text-center p-8 text-[#5f6374]">
              <div className="w-12 h-12 rounded-2xl bg-indigo-600/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 mb-3 shadow-sm">
                <Bot className="w-6 h-6" />
              </div>
              <h3 className="text-sm font-semibold text-white mb-1">Dione Workspace</h3>
              <p className="text-xs max-w-sm text-[#7d8192]">
                Ready for autonomous coding, system actions, database queries, and live Windows desktop interaction.
              </p>
            </div>
          ) : (
            activeThread.messages.map((msg) => (
              <MessageView key={msg.id} message={msg} />
            ))
          )}
          <div ref={chatBottomRef} />
        </div>

        {/* Bottom Floating Composer */}
        <Composer
          onSend={handleSendMessage}
          isLoading={isLoading}
          computerUseEnabled={computerUse.enabled}
          onToggleComputerUse={handleToggleComputerUse}
        />
      </div>

      {/* 3. Right Desktop Perception Drawer */}
      <ComputerUseDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        screenshotUrl={computerUse.screenshotUrl}
        onRefresh={handleCaptureScreenshot}
        isCapturing={computerUse.isCapturing || false}
        lastCaptureTime={computerUse.lastCaptureTime}
      />
    </div>
  );
}

export default App;
