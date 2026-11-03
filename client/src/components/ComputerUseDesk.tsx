import React, { useState } from 'react';
import {
  Monitor,
  RefreshCw,
  Crosshair,
  ShieldAlert,
  Play,
  Terminal,
  Layers,
  ExternalLink,
  MousePointer
} from 'lucide-react';
import { ComputerUseState } from '../types';
import { executeComputerAction } from '../services/api';

interface ComputerUseDeskProps {
  computerUse: ComputerUseState;
  onRefreshScreenshot: () => void;
  onToggleGrid: () => void;
  onLaunchApp: (appName: string) => void;
  isAutonomousActive: boolean;
}

export const ComputerUseDesk: React.FC<ComputerUseDeskProps> = ({
  computerUse,
  onRefreshScreenshot,
  onToggleGrid,
  onLaunchApp,
  isAutonomousActive,
}) => {
  const [gridVisible, setGridVisible] = useState(false);
  const [lastClickedCoord, setLastClickedCoord] = useState<string>('');

  const handleImageClick = async (e: React.MouseEvent<HTMLImageElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const relX = (e.clientX - rect.left) / rect.width;
    const relY = (e.clientY - rect.top) / rect.height;
    const px = Math.round(relX * 1920);
    const py = Math.round(relY * 1080);
    setLastClickedCoord(`Clicked (${px}, ${py}) [${Math.round(relX * 100)}%, ${Math.round(relY * 100)}%]`);
    await executeComputerAction({ action: 'click_coords', x: px, y: py, button: 'left' });
    setTimeout(onRefreshScreenshot, 350);
  };

  return (
    <div className="flex-1 h-full overflow-y-auto px-6 py-6 bg-[#090a12] text-slate-200 font-sans select-text">
      <div className="max-w-6xl mx-auto space-y-5">
        <div className="flex items-center justify-between pb-3 border-b border-white/[0.07]">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-full bg-cyan-500/20 border border-cyan-500/30 text-cyan-300 text-xs font-mono font-semibold flex items-center gap-1.5">
                <Monitor className="w-3.5 h-3.5" />
                <span>Windows 11 Live Vision & Control</span>
              </span>
              {isAutonomousActive && (
                <span className="px-2 py-0.5 rounded-full bg-violet-500/20 border border-violet-500/40 text-violet-300 text-[10px] font-mono animate-pulse">
                  Agent Acting on Desktop
                </span>
              )}
            </div>
            <h1 className="text-lg font-bold text-white tracking-tight mt-1">
              Interactive Desktop View (Click Anywhere on Screen to Send Mouse Click)
            </h1>
          </div>

          <div className="flex items-center gap-2">
            {lastClickedCoord && (
              <span className="px-2.5 py-1 rounded-lg bg-white/[0.04] border border-white/[0.08] text-[11px] font-mono text-cyan-300">
                {lastClickedCoord}
              </span>
            )}
            <button
              onClick={() => {
                setGridVisible(!gridVisible);
                onToggleGrid();
              }}
              className={`px-3 py-1.5 rounded-xl text-xs font-medium border flex items-center gap-1.5 transition-all ${
                gridVisible
                  ? 'bg-cyan-500/20 border-cyan-500/40 text-cyan-200'
                  : 'bg-white/[0.04] border-white/[0.08] text-slate-300 hover:text-white'
              }`}
            >
              <Crosshair className="w-3.5 h-3.5" />
              <span>{gridVisible ? 'Grid ON' : 'Coordinate Grid'}</span>
            </button>

            <button
              onClick={onRefreshScreenshot}
              className="px-3 py-1.5 rounded-xl bg-violet-600 hover:bg-violet-500 text-white text-xs font-semibold flex items-center gap-1.5 transition-all"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Refresh Screen</span>
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-5">
          <div className="lg:col-span-3 space-y-2">
            <div className="relative rounded-2xl overflow-hidden border border-white/[0.1] bg-[#06070c] shadow-2xl aspect-video flex items-center justify-center">
              {computerUse.screenshotUrl ? (
                <img
                  src={computerUse.screenshotUrl}
                  alt="Live Workstation Desktop"
                  onClick={handleImageClick}
                  className="w-full h-full object-contain select-none cursor-crosshair"
                  title="Click anywhere on the image to send a physical mouse click to that coordinate"
                />
              ) : (
                <div className="flex flex-col items-center gap-2 text-slate-400">
                  <Monitor className="w-9 h-9 stroke-[1.5]" />
                  <span className="text-xs font-mono">Click Refresh Screen to capture live desktop</span>
                </div>
              )}

              {computerUse.failSafeTripped && (
                <div className="absolute inset-0 bg-red-950/80 backdrop-blur-md flex flex-col items-center justify-center p-6 text-center space-y-2 z-20">
                  <ShieldAlert className="w-10 h-10 text-red-400" />
                  <h3 className="text-base font-bold text-white">Fail-Safe Override Active</h3>
                  <p className="text-xs text-red-200 max-w-md">
                    Physical mouse takeover detected.
                  </p>
                </div>
              )}
            </div>
          </div>

          <div className="space-y-4">
            <div className="p-4 rounded-2xl bg-white/[0.02] border border-white/[0.07] space-y-2.5">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-violet-400" />
                <span>Quick Focus / Launch</span>
              </span>
              <div className="space-y-1.5">
                {[
                  { id: 'chrome', name: 'Google Chrome', icon: <ExternalLink className="w-3.5 h-3.5 text-cyan-400" /> },
                  { id: 'edge', name: 'Microsoft Edge', icon: <ExternalLink className="w-3.5 h-3.5 text-blue-400" /> },
                  { id: 'code', name: 'VS Code', icon: <Terminal className="w-3.5 h-3.5 text-violet-400" /> },
                  { id: 'explorer', name: 'File Explorer', icon: <Layers className="w-3.5 h-3.5 text-amber-400" /> },
                  { id: 'spotify', name: 'Spotify', icon: <Play className="w-3.5 h-3.5 text-emerald-400" /> },
                ].map((app) => (
                  <button
                    key={app.id}
                    onClick={() => onLaunchApp(app.id)}
                    className="w-full p-2.5 rounded-xl bg-white/[0.03] hover:bg-white/[0.08] border border-white/[0.06] text-xs text-left flex items-center justify-between text-slate-300 hover:text-white transition-all"
                  >
                    <div className="flex items-center gap-2">
                      {app.icon}
                      <span>{app.name}</span>
                    </div>
                    <MousePointer className="w-3 h-3 text-slate-400" />
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
