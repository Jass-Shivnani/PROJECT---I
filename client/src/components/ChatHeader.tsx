import React, { useState, useRef, useEffect } from 'react';
import {
  Sparkles,
  Bot,
  ChevronDown,
  Monitor,
  Check,
  Zap,
  Code2,
  Trash2,
  ExternalLink,
  PanelLeft,
  ShieldCheck,
  Radio,
  FileCode,
  Layers
} from 'lucide-react';

interface ChatHeaderProps {
  activeSpecialist?: any;
  onSelectSpecialist?: (specialist: any) => void;
  activeModel: string;
  onSelectModel: (model: string) => void;
  isSidebarOpen: boolean;
  onToggleSidebar: () => void;
  isArtifactDrawerOpen: boolean;
  onToggleArtifactDrawer: () => void;
  hasArtifact: boolean;
  isVisionDrawerOpen: boolean;
  onToggleVisionDrawer: () => void;
  isActivityDrawerOpen?: boolean;
  onToggleActivityDrawer?: () => void;
  activityCount?: number;
  onClearThread: () => void;
  isTurboMode: boolean;
  onToggleTurbo: () => void;
}

export const ChatHeader: React.FC<ChatHeaderProps> = ({
  activeSpecialist,
  onSelectSpecialist,
  activeModel,
  onSelectModel,
  isSidebarOpen,
  onToggleSidebar,
  isArtifactDrawerOpen,
  onToggleArtifactDrawer,
  hasArtifact,
  isVisionDrawerOpen,
  onToggleVisionDrawer,
  isActivityDrawerOpen = false,
  onToggleActivityDrawer,
  activityCount = 0,
  onClearThread,
  isTurboMode,
  onToggleTurbo,
}) => {
  const [isModelMenuOpen, setIsModelMenuOpen] = useState(false);
  const modelMenuRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (modelMenuRef.current && !modelMenuRef.current.contains(e.target as Node)) {
        setIsModelMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const MODELS = [
    { id: 'gemini-3.5-flash-lite', name: 'Gemini 3.5 Flash-Lite', tag: 'Free 500 RPD' },
    { id: 'gemini-3.1-flash-lite', name: 'Gemini 3.1 Flash-Lite', tag: 'Free 500 RPD' },
    { id: 'gemini-2.5-flash-lite', name: 'Gemini 2.5 Flash-Lite', tag: 'Free High-Quota' },
    { id: 'gemini-3.8-flash', name: 'Gemini 3.8 Flash', tag: 'Latest 3.8' },
    { id: 'gemini-2.5-flash', name: 'Gemini 2.5 Flash', tag: 'Balanced' },
    { id: 'gemini-2.5-pro', name: 'Gemini 2.5 Pro', tag: 'AI Pro Trial' },
  ];

  return (
    <header className="h-14 border-b border-white/[0.08] bg-[#090a12]/95 backdrop-blur-xl px-4 flex items-center justify-between flex-shrink-0 z-20 select-none">
      {/* Left: Sidebar Toggle + Active Agent Persona Dropdown */}
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleSidebar}
          className={`p-1.5 rounded-lg transition-all ${
            isSidebarOpen ? 'text-slate-400 hover:text-white hover:bg-white/[0.06]' : 'bg-white/[0.08] text-white'
          }`}
          title={isSidebarOpen ? "Collapse session sidebar" : "Open session sidebar"}
        >
          <PanelLeft className="w-4 h-4" />
        </button>

        {/* Sovereign Dione AI Identity Badge (Zero Selector Policy) */}
        <div className="flex items-center gap-2.5 px-3 py-1.5 rounded-xl bg-white/[0.04] border border-white/[0.08] text-xs font-sans">
          <div className="w-5 h-5 rounded-md bg-gradient-to-tr from-violet-600 to-indigo-500 flex items-center justify-center text-white text-[10px] font-bold shadow-sm shadow-violet-500/20">
            D
          </div>
          <div className="flex items-center gap-2">
            <span className="font-semibold text-white tracking-tight leading-none">
              Dione AI
            </span>
            <span className="text-[9.5px] font-mono px-1.5 py-0.5 rounded bg-violet-500/10 text-violet-300 border border-violet-500/20 uppercase tracking-wider">
              Autonomous
            </span>
          </div>
        </div>

        {/* Model Selector Dropdown */}
        <div className="relative hidden sm:block" ref={modelMenuRef}>
          <button
            onClick={() => setIsModelMenuOpen(!isModelMenuOpen)}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl bg-white/[0.03] hover:bg-white/[0.06] border border-white/[0.06] transition-all text-[11.5px] font-mono text-slate-300 hover:text-white"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            <span>{activeModel.replace('gemini-', '')}</span>
            <ChevronDown className="w-3 h-3 text-slate-400" />
          </button>

          {isModelMenuOpen && (
            <div className="absolute left-0 mt-2 w-56 bg-[#0d0f18] border border-white/[0.1] rounded-2xl shadow-2xl p-1.5 space-y-1 z-50">
              {MODELS.map((m) => (
                <div
                  key={m.id}
                  onClick={() => {
                    onSelectModel(m.id);
                    setIsModelMenuOpen(false);
                  }}
                  className={`px-3 py-2 rounded-xl text-xs font-mono flex items-center justify-between cursor-pointer transition-all ${
                    activeModel === m.id
                      ? 'bg-violet-600/20 text-white border border-violet-500/30'
                      : 'text-slate-300 hover:bg-white/[0.05] hover:text-white'
                  }`}
                >
                  <span>{m.name}</span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/[0.06] text-slate-400">
                    {m.tag}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Right Action Controls */}
      <div className="flex items-center gap-2">
        {/* Turbo Mode Pill */}
        <button
          onClick={onToggleTurbo}
          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-xs font-medium border transition-all ${
            isTurboMode
              ? 'bg-amber-500/20 border-amber-500/40 text-amber-300 shadow-md shadow-amber-500/20'
              : 'bg-white/[0.02] border-white/[0.06] text-slate-400 hover:text-white hover:bg-white/[0.05]'
          }`}
          title="Toggle Turbo Mode (Auto-authorizes low-risk actions)"
        >
          <Zap className={`w-3.5 h-3.5 ${isTurboMode ? 'text-amber-400 fill-amber-400' : ''}`} />
          <span className="hidden md:inline">{isTurboMode ? 'Turbo' : 'Safe'}</span>
        </button>

        {/* Artifacts Drawer Toggle */}
        <button
          onClick={onToggleArtifactDrawer}
          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-xs font-medium border transition-all ${
            isArtifactDrawerOpen
              ? 'bg-violet-600/20 border-violet-500/40 text-violet-200 shadow-md shadow-violet-600/20'
              : 'bg-white/[0.02] border-white/[0.06] text-slate-400 hover:text-white hover:bg-white/[0.05]'
          }`}
          title="Toggle Artifacts Code / Preview Drawer"
        >
          <Code2 className="w-3.5 h-3.5" />
          <span className="hidden md:inline">Artifacts</span>
          {hasArtifact && (
            <span className="w-1.5 h-1.5 rounded-full bg-violet-400" />
          )}
        </button>

        {/* Vision Desk Toggle */}
        <button
          onClick={onToggleVisionDrawer}
          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-xs font-medium border transition-all ${
            isVisionDrawerOpen
              ? 'bg-cyan-500/20 border-cyan-500/40 text-cyan-200 shadow-md shadow-cyan-500/20'
              : 'bg-white/[0.02] border-white/[0.06] text-slate-400 hover:text-white hover:bg-white/[0.05]'
          }`}
          title="Toggle Desktop Vision & Controls"
        >
          <Monitor className="w-3.5 h-3.5" />
          <span className="hidden md:inline">Vision</span>
        </button>

        {/* Workstation Activity Drawer Toggle */}
        {onToggleActivityDrawer && (
          <button
            onClick={onToggleActivityDrawer}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-xs font-medium border transition-all ${
              isActivityDrawerOpen
                ? 'bg-indigo-600/20 border-indigo-500/40 text-indigo-200 shadow-md shadow-indigo-600/20'
                : 'bg-white/[0.02] border-white/[0.06] text-slate-400 hover:text-white hover:bg-white/[0.05]'
            }`}
            title="Toggle Workstation Activity & Execution Ledger"
          >
            <Layers className="w-3.5 h-3.5" />
            <span className="hidden md:inline">Activity</span>
            {activityCount > 0 && (
              <span className="text-[10px] font-mono px-1 rounded-full bg-indigo-500/20 text-indigo-300">
                {activityCount}
              </span>
            )}
          </button>
        )}

        {/* Clear Thread */}
        <button
          onClick={onClearThread}
          className="p-1.5 rounded-xl text-slate-400 hover:text-red-400 hover:bg-red-500/10 transition-colors"
          title="Clear session messages"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
};
