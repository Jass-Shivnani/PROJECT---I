import React from 'react';
import {
  MessageSquare,
  Bot,
  Monitor,
  Network,
  Moon,
  Zap,
  Mic,
  Settings2,
  Sparkles
} from 'lucide-react';

export type WorkspaceTab = 'chat' | 'agents' | 'computer-use' | 'knowledge' | 'dream';

interface NavigationRailProps {
  activeTab: WorkspaceTab;
  onSelectTab: (tab: WorkspaceTab) => void;
  isTurboMode: boolean;
  onToggleTurbo: () => void;
  isVoiceActive: boolean;
  onToggleVoice: () => void;
  onOpenSettings: () => void;
  threadCount: number;
  hasDreamBriefing: boolean;
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
  hasDreamBriefing,
  isAutonomousActive,
}) => {
  return (
    <nav className="w-16 bg-[#07080f] border-r border-white/[0.08] flex flex-col items-center justify-between py-3 flex-shrink-0 z-30 select-none">
      {/* Top Brand Logo */}
      <div className="flex flex-col items-center gap-4">
        <button
          onClick={() => onSelectTab('chat')}
          className="relative group p-1 focus:outline-none"
          title="Dione AI Sovereign Intelligence"
          aria-label="Dione AI Home"
        >
          <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-violet-600 via-indigo-600 to-purple-500 flex items-center justify-center text-white font-black text-sm shadow-lg shadow-violet-600/30 group-hover:scale-105 transition-transform duration-200">
            D
          </div>
          {isAutonomousActive && (
            <span className="absolute -top-0.5 -right-0.5 w-3 h-3 rounded-full bg-cyan-400 border-2 border-[#07080f] animate-ping" />
          )}
        </button>

        {/* Primary Workspace Navigation Tabs */}
        <div className="flex flex-col items-center gap-1.5 w-full px-2">
          {/* Chat Sessions */}
          <button
            onClick={() => onSelectTab('chat')}
            className={`relative w-11 h-11 rounded-xl flex items-center justify-center transition-all ${
              activeTab === 'chat'
                ? 'bg-violet-600/25 text-violet-300 border border-violet-500/40 shadow-sm'
                : 'text-slate-400 hover:text-white hover:bg-white/[0.05]'
            }`}
            title="Chat & Sessions"
            aria-label="Chat & Sessions"
          >
            <MessageSquare className="w-5 h-5" />
            {threadCount > 0 && (
              <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-violet-400" />
            )}
          </button>

          {/* Agent Fleet & Marketplace */}
          <button
            onClick={() => onSelectTab('agents')}
            className={`relative w-11 h-11 rounded-xl flex items-center justify-center transition-all ${
              activeTab === 'agents'
                ? 'bg-violet-600/25 text-violet-300 border border-violet-500/40 shadow-sm'
                : 'text-slate-400 hover:text-white hover:bg-white/[0.05]'
            }`}
            title="Agent Fleet & Specialists"
            aria-label="Agent Fleet & Specialists"
          >
            <Bot className="w-5 h-5" />
            <span className="absolute -bottom-0.5 text-[8.5px] font-mono font-bold tracking-tighter text-violet-400">
              6
            </span>
          </button>

          {/* Computer Use Desk */}
          <button
            onClick={() => onSelectTab('computer-use')}
            className={`relative w-11 h-11 rounded-xl flex items-center justify-center transition-all ${
              activeTab === 'computer-use'
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm'
                : 'text-slate-400 hover:text-white hover:bg-white/[0.05]'
            }`}
            title="Computer Use Desk (Windows 11)"
            aria-label="Computer Use Desk"
          >
            <Monitor className="w-5 h-5" />
            {isAutonomousActive && (
              <span className="absolute top-2 right-2 w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
            )}
          </button>

          {/* Memory & Knowledge Graph */}
          <button
            onClick={() => onSelectTab('knowledge')}
            className={`relative w-11 h-11 rounded-xl flex items-center justify-center transition-all ${
              activeTab === 'knowledge'
                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-sm'
                : 'text-slate-400 hover:text-white hover:bg-white/[0.05]'
            }`}
            title="Memory & Knowledge Graph"
            aria-label="Memory & Knowledge Graph"
          >
            <Network className="w-5 h-5" />
          </button>

          {/* Scout & Dream Journal */}
          <button
            onClick={() => onSelectTab('dream')}
            className={`relative w-11 h-11 rounded-xl flex items-center justify-center transition-all ${
              activeTab === 'dream'
                ? 'bg-purple-600/25 text-purple-300 border border-purple-500/40 shadow-sm'
                : 'text-slate-400 hover:text-white hover:bg-white/[0.05]'
            }`}
            title="Scout & Dream Journal"
            aria-label="Scout & Dream Journal"
          >
            <Moon className="w-5 h-5" />
            {hasDreamBriefing && (
              <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-pink-400 animate-pulse" />
            )}
          </button>
        </div>
      </div>

      {/* Bottom Utility Controls */}
      <div className="flex flex-col items-center gap-2 w-full px-2">
        {/* Turbo Mode Toggle */}
        <button
          onClick={onToggleTurbo}
          className={`w-10 h-10 rounded-xl flex items-center justify-center transition-all ${
            isTurboMode
              ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-md shadow-amber-500/20'
              : 'text-slate-400 hover:text-white hover:bg-white/[0.05]'
          }`}
          title={isTurboMode ? "Turbo Mode Active (Auto-confirm low-risk)" : "Enable Turbo Mode"}
          aria-label="Toggle Turbo Mode"
        >
          <Zap className={`w-4 h-4 ${isTurboMode ? 'fill-amber-400' : ''}`} />
        </button>

        {/* Neural Voice Control */}
        <button
          onClick={onToggleVoice}
          className={`w-10 h-10 rounded-xl flex items-center justify-center transition-all ${
            isVoiceActive
              ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 shadow-md shadow-emerald-500/20 animate-pulse'
              : 'text-slate-400 hover:text-white hover:bg-white/[0.05]'
          }`}
          title={isVoiceActive ? "Live Aoede Voice Active" : "Connect Neural Voice"}
          aria-label="Toggle Neural Voice"
        >
          <Mic className="w-4 h-4" />
        </button>

        {/* Settings */}
        <button
          onClick={onOpenSettings}
          className="w-10 h-10 rounded-xl flex items-center justify-center text-slate-400 hover:text-white hover:bg-white/[0.05] transition-all"
          title="Workspace Settings"
          aria-label="Workspace Settings"
        >
          <Settings2 className="w-4 h-4" />
        </button>
      </div>
    </nav>
  );
};
