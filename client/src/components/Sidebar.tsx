import React, { useState } from 'react';
import {
  Plus,
  MessageSquare,
  ShieldCheck,
  Cpu,
  Moon,
  Sparkles,
  Trash2,
  PanelLeftClose,
  Zap,
  Search,
  Bot
} from 'lucide-react';
import { Thread } from '../types';
import { triggerDreamCycle } from '../services/api';

interface SidebarProps {
  threads: Thread[];
  activeThreadId: string;
  onSelectThread: (id: string) => void;
  onNewThread: () => void;
  onDeleteThread: (id: string) => void;
  isOpen: boolean;
  onToggle: () => void;
  onDreamTriggered?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  threads,
  activeThreadId,
  onSelectThread,
  onNewThread,
  onDeleteThread,
  isOpen,
  onToggle,
  onDreamTriggered,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [isDreaming, setIsDreaming] = useState(false);
  const [dreamStatus, setDreamStatus] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleForceDream = async () => {
    setIsDreaming(true);
    setDreamStatus('Scouting web & arXiv...');
    try {
      const res = await triggerDreamCycle();
      if (res.success) {
        setDreamStatus('Cycle complete · Briefing ready');
        onDreamTriggered?.();
      } else {
        setDreamStatus('Dream engine idle');
      }
    } catch {
      setDreamStatus('Dream cycle error');
    } finally {
      setIsDreaming(false);
      setTimeout(() => setDreamStatus(null), 3500);
    }
  };

  const filteredThreads = threads.filter(t =>
    t.title.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <aside className="w-[270px] border-r border-white/[0.08] bg-[#090a12] flex flex-col h-full flex-shrink-0 z-20 select-none font-sans text-slate-200">
      {/* Brand Header */}
      <div className="p-3.5 border-b border-white/[0.06] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="font-bold text-xs uppercase tracking-wider text-slate-300">
            Sessions
          </span>
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-white/[0.06] text-slate-400">
            {threads.length}
          </span>
        </div>
        <button
          onClick={onToggle}
          className="p-1 rounded-md hover:bg-white/5 text-slate-400 hover:text-white transition-colors"
          title="Collapse sidebar"
        >
          <PanelLeftClose className="w-4 h-4" />
        </button>
      </div>

      {/* New Session Button */}
      <div className="p-3 space-y-2">
        <button
          onClick={onNewThread}
          className="w-full py-2 px-3 rounded-xl bg-violet-600/25 hover:bg-violet-600/35 border border-violet-500/40 text-white font-medium text-xs flex items-center justify-center gap-2 transition-all hover:scale-[1.01] shadow-sm shadow-violet-600/20"
        >
          <Plus className="w-4 h-4 text-violet-300" />
          <span>New Session</span>
        </button>

        {/* Search Bar */}
        <div className="relative">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2" />
          <input
            type="text"
            placeholder="Search conversations..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-white/[0.03] border border-white/[0.06] rounded-xl pl-8 pr-3 py-1.5 text-xs text-white placeholder-slate-400 focus:outline-none focus:border-violet-500/40"
          />
        </div>
      </div>

      {/* Conversations List */}
      <div className="flex-1 overflow-y-auto px-2 space-y-1">
        <div className="text-[10px] font-mono uppercase tracking-wider text-slate-400 px-2 py-1">
          Recent Sessions
        </div>
        {filteredThreads.map(t => {
          const active = t.id === activeThreadId;
          const lastMsg = t.messages?.[t.messages.length - 1];
          const snippet = lastMsg?.content ? lastMsg.content.slice(0, 48) : '';

          return (
            <div
              key={t.id}
              onClick={() => onSelectThread(t.id)}
              className={`group px-3 py-2.5 rounded-xl text-xs flex flex-col gap-1 cursor-pointer transition-all ${
                active
                  ? 'bg-violet-600/20 text-white font-medium border border-violet-500/30 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 truncate min-w-0">
                  <MessageSquare className={`w-3.5 h-3.5 flex-shrink-0 ${active ? 'text-violet-400' : 'text-slate-400'}`} />
                  <span className="truncate text-xs font-semibold">{t.title}</span>
                </div>
                {threads.length > 1 && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteThread(t.id);
                    }}
                    className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-500/20 text-slate-400 hover:text-red-400 transition-all flex-shrink-0"
                    title="Delete session"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                )}
              </div>

              {snippet && (
                <div className="text-[10.5px] text-slate-400 truncate pl-5">
                  {snippet}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Bottom Ambient Dream Card */}
      <div className="p-3 border-t border-white/[0.06] space-y-2">
        <div className="p-2.5 rounded-xl bg-white/[0.02] border border-white/[0.06] space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-slate-300 flex items-center gap-1.5">
              <Moon className="w-3 h-3 text-purple-400" />
              <span>Dream & Scout</span>
            </span>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" title="Autonomous Idle Monitor Active" />
          </div>
          <p className="text-[10px] text-slate-400 leading-tight">
            Autonomously scouts arXiv & web when your workstation is inactive.
          </p>
          {dreamStatus && (
            <div className="text-[10px] font-mono text-emerald-300 bg-emerald-950/40 p-1 rounded border border-emerald-500/30">
              {dreamStatus}
            </div>
          )}
          <button
            onClick={handleForceDream}
            disabled={isDreaming}
            className="w-full py-1 px-2 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] text-[10.5px] font-mono text-slate-300 flex items-center justify-center gap-1.5 transition-all"
          >
            <Sparkles className="w-3 h-3 text-purple-400" />
            <span>{isDreaming ? 'Scouting...' : 'Trigger Cycle Now'}</span>
          </button>
        </div>
      </div>
    </aside>
  );
};
