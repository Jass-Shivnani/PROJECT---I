import React from 'react';
import { 
  Plus, 
  MessageSquare, 
  Send, 
  Mail, 
  ShieldCheck, 
  Cpu, 
  Trash2,
  ChevronLeft
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
  if (!isOpen) return null;

  return (
    <aside className="w-64 border-r border-[#22242c] bg-[#121319] flex flex-col h-full flex-shrink-0 z-10 transition-all select-none">
      {/* Brand Header & New Chat */}
      <div className="p-3 border-b border-[#22242c] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-md bg-indigo-600 flex items-center justify-center text-white font-bold text-xs shadow-sm">
            D
          </div>
          <span className="font-semibold text-sm text-white tracking-tight">Dione Studio</span>
        </div>
        <button
          onClick={onToggle}
          className="p-1 rounded hover:bg-[#1d1f27] text-[#696d7c] hover:text-white transition-colors"
          title="Collapse sidebar"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>
      </div>

      <div className="p-3">
        <button
          onClick={onNewThread}
          className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-lg border border-[#2c2f3b] bg-[#191a22] hover:bg-[#20222d] text-xs font-medium text-white transition-all shadow-sm"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>New Conversation</span>
        </button>
      </div>

      {/* Threads List */}
      <div className="flex-1 overflow-y-auto px-2 space-y-1">
        <span className="text-[10px] font-semibold text-[#545766] uppercase px-2 py-1 block tracking-wider">
          Recent Conversations
        </span>
        {threads.map((t) => {
          const isActive = t.id === activeThreadId;
          return (
            <div
              key={t.id}
              onClick={() => onSelectThread(t.id)}
              className={`group flex items-center justify-between px-2.5 py-2 rounded-lg text-xs cursor-pointer transition-all ${
                isActive
                  ? 'bg-[#1e202b] text-white border border-[#2d303f] font-medium'
                  : 'text-[#8b8f9f] hover:bg-[#181920] hover:text-[#d4d6e0]'
              }`}
            >
              <div className="flex items-center gap-2 min-w-0 flex-1">
                <MessageSquare className={`w-3.5 h-3.5 flex-shrink-0 ${isActive ? 'text-indigo-400' : 'text-[#565967]'}`} />
                <span className="truncate">{t.title}</span>
              </div>
              {threads.length > 1 && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteThread(t.id);
                  }}
                  className="opacity-0 group-hover:opacity-100 p-1 hover:text-red-400 text-[#5f6373] transition-opacity"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              )}
            </div>
          );
        })}
      </div>

      {/* Status Footer */}
      <div className="p-3 border-t border-[#22242c] bg-[#101116] flex flex-col gap-2 text-xs">
        {/* Telegram Integration Indicator */}
        <div className="flex items-center justify-between text-[#8b8f9f]">
          <span className="flex items-center gap-1.5 text-[11px]">
            <Send className="w-3 h-3 text-sky-400" />
            <span>@DioneAiBot</span>
          </span>
          <span className="text-[10px] font-mono text-emerald-400 flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
            online
          </span>
        </div>

        {/* Gmail Integration Indicator */}
        <div className="flex items-center justify-between text-[#8b8f9f]">
          <span className="flex items-center gap-1.5 text-[11px] truncate max-w-[140px]">
            <Mail className="w-3 h-3 text-amber-400 flex-shrink-0" />
            <span className="truncate">jassshivnani11</span>
          </span>
          <span className="text-[10px] font-mono text-emerald-400">ready</span>
        </div>

        {/* Engine Spec */}
        <div className="mt-1 pt-2 border-t border-[#1c1e26] flex items-center justify-between text-[10px] text-[#555866] font-mono">
          <span className="flex items-center gap-1">
            <Cpu className="w-3 h-3 text-indigo-400" />
            <span>MAF 1.20.0</span>
          </span>
          <span>Gemini 3.5</span>
        </div>
      </div>
    </aside>
  );
};
