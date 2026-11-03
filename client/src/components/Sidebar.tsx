import React, { useState } from 'react';
import {
  Plus,
  MessageSquare,
  Trash2,
  PanelLeftClose,
  Search
} from 'lucide-react';
import { Thread } from '../types';

interface SidebarProps {
  threads: Thread[];
  activeThreadId: string;
  onSelectThread: (id: string) => void;
  onNewThread: () => void;
  onDeleteThread: (id: string) => void;
  isOpen: boolean;
  onToggle: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  threads,
  activeThreadId,
  onSelectThread,
  onNewThread,
  onDeleteThread,
  isOpen,
  onToggle,
}) => {
  const [searchTerm, setSearchTerm] = useState('');

  if (!isOpen) return null;

  const filteredThreads = threads.filter(t =>
    t.title.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <aside className="w-[256px] border-r border-white/[0.07] bg-[#090a12] flex flex-col h-full flex-shrink-0 z-20 select-none font-sans text-slate-200">
      <div className="p-3.5 border-b border-white/[0.06] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="font-bold text-xs uppercase tracking-wider text-slate-300">
            Conversations
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

      <div className="p-3 space-y-2">
        <button
          onClick={onNewThread}
          className="w-full py-2 px-3 rounded-xl bg-violet-600/25 hover:bg-violet-600/35 border border-violet-500/40 text-white font-medium text-xs flex items-center justify-center gap-2 transition-all shadow-sm"
        >
          <Plus className="w-4 h-4 text-violet-300" />
          <span>New Conversation</span>
        </button>

        <div className="relative">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2" />
          <input
            type="text"
            placeholder="Filter threads..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-white/[0.03] border border-white/[0.06] rounded-xl pl-8 pr-3 py-1.5 text-xs text-white placeholder-slate-400 focus:outline-none focus:border-violet-500/40"
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-2 pb-3 space-y-1">
        {filteredThreads.map(t => {
          const active = t.id === activeThreadId;
          const lastMsg = t.messages?.[t.messages.length - 1];
          const snippet = lastMsg?.content ? lastMsg.content.slice(0, 44) : 'Empty thread';

          return (
            <div
              key={t.id}
              onClick={() => onSelectThread(t.id)}
              className={`group relative rounded-xl p-2.5 cursor-pointer transition-all border ${
                active
                  ? 'bg-violet-600/15 border-violet-500/35 text-white'
                  : 'border-transparent hover:bg-white/[0.04] text-slate-300'
              }`}
            >
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0">
                  <MessageSquare className={`w-3.5 h-3.5 flex-shrink-0 ${active ? 'text-violet-400' : 'text-slate-500'}`} />
                  <span className="text-xs font-medium truncate">{t.title}</span>
                </div>
                {threads.length > 1 && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteThread(t.id);
                    }}
                    className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-500/20 text-slate-400 hover:text-red-300 transition-all"
                    title="Delete thread"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                )}
              </div>
              <p className="text-[11px] text-slate-400 truncate mt-1 pl-5">{snippet}</p>
            </div>
          );
        })}
      </div>
    </aside>
  );
};
