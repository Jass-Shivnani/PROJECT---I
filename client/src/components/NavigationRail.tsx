import React from 'react';
import {
  MessageSquare,
  Monitor,
  Network,
  Zap,
  Mic,
  Settings2
} from 'lucide-react';

export type WorkspaceTab = 'chat' | 'computer-use' | 'knowledge';

interface NavigationRailProps {
  activeTab: WorkspaceTab;
  onSelectTab: (tab: WorkspaceTab) => void;
  isTurboMode: boolean;
  onToggleTurbo: () => void;
  isVoiceActive: boolean;
  onToggleVoice: () => void;
  onOpenSettings: () => void;
  threadCount: number;
  isAutonomousActive: boolean;
}

export const NavigationRail: React.FC<NavigationRailProps> = ({
  activeTab,
  onSelectTab,
  isTurboMode,
  onToggleTurbo,
  isVoiceActive,
  onToggleVoice,
  onOpenSettings,
  threadCount,
  isAutonomousActive,
}) => {
  return (
    <nav className="w-14 bg-[#07080f] border-r border-white/[0.07] flex flex-col items-center justify-between py-3 flex-shrink-0 z-30 select-none">
      {/* Top Brand + Core Workspaces */}
      <div className="flex flex-col items-center gap-4">
        <button
          onClick={() => onSelectTab('chat')}
          className="relative group p-1 focus:outline-none"
          title="Dione AI"
        >
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-violet-600 to-indigo-500 flex items-center justify-center text-white font-black text-xs shadow-md shadow-violet-600/20">
            D
          </div>
          {isAutonomousActive && (
            <span className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-cyan-400 border-2 border-[#07080f] animate-ping" />
          )}
        </button>

        <div className="flex flex-col items-center gap-1.5 w-full px-1.5">
          {/* 1. Chat & Voice Studio */}
          <button
            onClick={() => onSelectTab('chat')}
            className={`relative w-10 h-10 rounded-xl flex items-center justify-center transition-all ${
              activeTab === 'chat'
                ? 'bg-violet-600/25 text-violet-300 border border-violet-500/40'
                : 'text-slate-400 hover:text-white hover:bg-white/[0.05]'
            }`}
            title="Chat & Voice Studio"
          >
            <MessageSquare className="w-4 h-4" />
            {threadCount > 0 && (
              <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full bg-violet-400" />
            )}
          </button>

          {/* 2. Live Desktop Vision & Control */}
          <button
            onClick={() => onSelectTab('computer-use')}
            className={`relative w-10 h-10 rounded-xl flex items-center justify-center transition-all ${
              activeTab === 'computer-use'
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                : 'text-slate-400 hover:text-white hover:bg-white/[0.05]'
            }`}
            title="Live Desktop Vision & Control"
          >
            <Monitor className="w-4 h-4" />
            {isAutonomousActive && (
              <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
            )}
          </button>

          {/* 3. Personal Knowledge Graph & Contacts */}
          <button
            onClick={() => onSelectTab('knowledge')}
            className={`relative w-10 h-10 rounded-xl flex items-center justify-center transition-all ${
              activeTab === 'knowledge'
                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                : 'text-slate-400 hover:text-white hover:bg-white/[0.05]'
            }`}
            title="Knowledge Graph & Contacts"
          >
            <Network className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Bottom Controls */}
      <div className="flex flex-col items-center gap-2 w-full px-1.5">
        <button
          onClick={onToggleTurbo}
          className={`w-9 h-9 rounded-xl flex items-center justify-center transition-all ${
            isTurboMode
              ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
              : 'text-slate-400 hover:text-white hover:bg-white/[0.05]'
          }`}
          title={isTurboMode ? "Turbo Mode ON (Auto-approve Tier 4)" : "Standard Intent Safety Gate"}
        >
          <Zap className={`w-4 h-4 ${isTurboMode ? 'fill-amber-400' : ''}`} />
        </button>

        <button
          onClick={onToggleVoice}
          className={`w-9 h-9 rounded-xl flex items-center justify-center transition-all ${
            isVoiceActive
              ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 animate-pulse'
              : 'text-slate-400 hover:text-white hover:bg-white/[0.05]'
          }`}
          title={isVoiceActive ? "Live Voice Active (Click to disconnect)" : "Start Live Voice (Gemini Live + 3.8 Thinking)"}
        >
          <Mic className="w-4 h-4" />
        </button>

        <button
          onClick={onOpenSettings}
          className="w-9 h-9 rounded-xl flex items-center justify-center text-slate-400 hover:text-white hover:bg-white/[0.05] transition-all"
          title="Settings, Audio Devices & Integrations"
        >
          <Settings2 className="w-4 h-4" />
        </button>
      </div>
    </nav>
  );
};
