import React, { useState, useEffect } from 'react';
import {
  Monitor,
  RefreshCw,
  Eye,
  Crosshair,
  ShieldAlert,
  Play,
  Terminal,
  MousePointer,
  Keyboard,
  Layers,
  Gamepad2,
  CheckCircle2,
  ExternalLink
} from 'lucide-react';
import { ComputerUseState } from '../types';
import { fetchDesktopScreenshot } from '../services/api';

interface ComputerUseDeskProps {
  computerUse: ComputerUseState;
  onRefreshScreenshot: () => void;
  onToggleGrid: () => void;
  onLaunchGame: (gameName: string) => void;
  isAutonomousActive: boolean;
}

export const ComputerUseDesk: React.FC<ComputerUseDeskProps> = ({
  computerUse,
  onRefreshScreenshot,
  onToggleGrid,
  onLaunchGame,
  isAutonomousActive,
}) => {
  const [selectedApp, setSelectedApp] = useState('browser');
  const [gridVisible, setGridVisible] = useState(false);

  return (
    <div className="flex-1 h-full overflow-y-auto px-6 py-6 bg-[#090a12] text-slate-200 font-sans select-text">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between pb-2 border-b border-white/[0.06]">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-full bg-cyan-500/20 border border-cyan-500/30 text-cyan-300 text-xs font-mono font-semibold flex items-center gap-1.5">
                <Monitor className="w-3.5 h-3.5" />
                <span>Win32 Computer-Use Station</span>
              </span>
              {isAutonomousActive && (
                <span className="px-2 py-0.5 rounded-full bg-red-500/20 border border-red-500/40 text-red-300 text-[10px] font-mono animate-pulse">
                  Autonomous Control Active
                </span>
              )}
            </div>
            <h1 className="text-xl font-bold text-white tracking-tight mt-1">
              Windows 11 Computer-Use & Vision Desk
            </h1>
            <p className="text-xs text-slate-300">
              GDI 64-bit frame capture, Windows UIAutomation element discovery, and percentage grid interaction.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                setGridVisible(!gridVisible);
                onToggleGrid();
              }}
              className={`px-3 py-1.5 rounded-xl text-xs font-medium border flex items-center gap-1.5 transition-all ${
                gridVisible
                  ? 'bg-cyan-500/20 border-cyan-500/40 text-cyan-200 shadow-md shadow-cyan-500/20'
                  : 'bg-white/[0.04] border-white/[0.08] text-slate-300 hover:text-white hover:bg-white/[0.08]'
              }`}
            >
              <Crosshair className="w-3.5 h-3.5" />
              <span>{gridVisible ? 'Grid Overlay (0-100%) [ON]' : 'Toggle Grid'}</span>
            </button>

            <button
              onClick={onRefreshScreenshot}
              className="px-3 py-1.5 rounded-xl bg-violet-600/30 hover:bg-violet-600/50 border border-violet-500/40 text-white text-xs font-medium flex items-center gap-1.5 transition-all"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Capture Screen</span>
            </button>
          </div>
        </div>

        {/* Live Display & Workstation Surface */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Main Monitor Canvas */}
          <div className="lg:col-span-3 space-y-3">
            <div className="relative rounded-2xl overflow-hidden border border-white/[0.1] bg-[#07080f] shadow-2xl aspect-video flex items-center justify-center group">
              {computerUse.screenshotUrl ? (
                <img
                  src={computerUse.screenshotUrl}
                  alt="Live Workstation Desktop"
                  className="w-full h-full object-contain select-none"
                />
              ) : (
                <div className="flex flex-col items-center gap-2 text-slate-400">
                  <Monitor className="w-10 h-10 stroke-[1.5] text-slate-400" />
                  <span className="text-xs font-mono">No frame captured yet. Click Capture Screen.</span>
                </div>
              )}

              {/* Live Overlay Indicator */}
              <div className="absolute top-3 left-3 flex items-center gap-2">
                <span className="px-2.5 py-1 rounded-lg bg-black/70 backdrop-blur-md border border-white/10 text-[10.5px] font-mono text-slate-300 flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-emerald-400" />
                  <span>Primary Display &bull; DPI Aware v2</span>
                </span>
                {computerUse.lastCaptureTime && (
                  <span className="px-2 py-1 rounded-lg bg-black/70 backdrop-blur-md border border-white/10 text-[10px] font-mono text-slate-400">
                    {computerUse.lastCaptureTime}
                  </span>
                )}
              </div>

              {/* Failsafe Notice */}
              {computerUse.failSafeTripped && (
                <div className="absolute inset-0 bg-red-950/80 backdrop-blur-md flex flex-col items-center justify-center p-6 text-center space-y-2 z-20">
                  <ShieldAlert className="w-10 h-10 text-red-400" />
                  <h3 className="text-base font-bold text-white">Fail-Safe Override Tripped</h3>
                  <p className="text-xs text-red-200 max-w-md">
                    Physical mouse movement or keyboard touch detected. Autonomous control suspended instantly.
                  </p>
                </div>
              )}
            </div>

            {/* Quick Automation Strip */}
            <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06] flex items-center justify-between text-xs">
              <div className="flex items-center gap-2 font-mono text-[11px] text-slate-400">
                <Crosshair className="w-3.5 h-3.5 text-cyan-400" />
                <span>Percentage Coordinate Grid: (X: 0% → 100%, Y: 0% → 100%)</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[11px] font-mono text-slate-400">Human-In-The-Loop:</span>
                <span className="text-emerald-400 font-mono text-[11px] flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3" />
                  <span>Physical Mouse Move Aborts AI</span>
                </span>
              </div>
            </div>
          </div>

          {/* Right Rail: Quick Actions & Launcher */}
          <div className="space-y-4">
            {/* Quick App Launcher */}
            <div className="p-4 rounded-2xl bg-white/[0.02] border border-white/[0.06] space-y-3">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-violet-400" />
                <span>Application Launcher</span>
              </span>
              <p className="text-[11.5px] text-slate-400 leading-relaxed">
                Launch apps through prioritized Windows path discovery and alias resolution.
              </p>

              <div className="space-y-1.5 pt-1">
                {[
                  { id: 'browser', name: 'Google Chrome / Edge', icon: <ExternalLink className="w-3.5 h-3.5 text-cyan-400" /> },
                  { id: 'code', name: 'Visual Studio Code', icon: <Terminal className="w-3.5 h-3.5 text-blue-400" /> },
                  { id: 'explorer', name: 'File Explorer', icon: <Layers className="w-3.5 h-3.5 text-amber-400" /> },
                  { id: 'valorant', name: 'Valorant (Fullscreen)', icon: <Gamepad2 className="w-3.5 h-3.5 text-pink-400" /> },
                ].map((app) => (
                  <button
                    key={app.id}
                    onClick={() => {
                      if (app.id === 'valorant') {
                        onLaunchGame('valorant');
                      } else {
                        onLaunchGame(app.id);
                      }
                    }}
                    className="w-full p-2.5 rounded-xl bg-white/[0.03] hover:bg-white/[0.08] border border-white/[0.06] text-xs text-left flex items-center justify-between text-slate-300 hover:text-white transition-all group"
                  >
                    <div className="flex items-center gap-2">
                      {app.icon}
                      <span>{app.name}</span>
                    </div>
                    <Play className="w-3 h-3 text-slate-400 group-hover:text-violet-400 transition-colors" />
                  </button>
                ))}
              </div>
            </div>

            {/* Operating Principles Card */}
            <div className="p-4 rounded-2xl bg-white/[0.02] border border-white/[0.06] space-y-2 text-xs">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                <span>Zero-Guesswork Mandate</span>
              </span>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Dione never assumes window positions or claims tasks are complete without visual inspection of the post-action screen state.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
