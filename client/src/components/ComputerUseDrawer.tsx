import React, { useState, useRef } from 'react';
import {
  X,
  RefreshCw,
  ShieldCheck,
  Monitor,
  MousePointer,
  Volume2,
  VolumeX,
  Play,
  Terminal,
  Calculator,
  FileText,
  Sliders,
  CheckCircle2,
  Sparkles
} from 'lucide-react';
import { executeComputerAction } from '../services/api';

interface ComputerUseDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  screenshotUrl: string | null;
  onRefresh: () => void;
  isCapturing: boolean;
  lastCaptureTime?: string;
}

export const ComputerUseDrawer: React.FC<ComputerUseDrawerProps> = ({
  isOpen,
  onClose,
  screenshotUrl,
  onRefresh,
  isCapturing,
  lastCaptureTime,
}) => {
  const [clickStatus, setClickStatus] = useState<string | null>(null);
  const [audioStatus, setAudioStatus] = useState<string | null>(null);
  const imgRef = useRef<HTMLImageElement>(null);

  if (!isOpen) return null;

  const handleCanvasClick = async (e: React.MouseEvent<HTMLDivElement>) => {
    if (!imgRef.current) return;
    const rect = imgRef.current.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;

    // Scale to standard display resolution (assume 1920x1080 display)
    const scaleX = 1920 / rect.width;
    const scaleY = 1080 / rect.height;
    const physicalX = Math.round(clickX * scaleX);
    const physicalY = Math.round(clickY * scaleY);
    const pctX = ((clickX / rect.width) * 100).toFixed(1);
    const pctY = ((clickY / rect.height) * 100).toFixed(1);

    setClickStatus(`Dispatched Win32 Click at (${pctX}%, ${pctY}%) [pixels: ${physicalX}, ${physicalY}]...`);
    try {
      const res = await executeComputerAction({
        action: 'click_coords',
        x: physicalX,
        y: physicalY,
        button: 'left',
      });
      if (res.success) {
        setClickStatus(`Clicked at (${pctX}%, ${pctY}%) [pixels: ${physicalX}, ${physicalY}] with Mouse Fail-Safe.`);
      } else {
        setClickStatus(`Click error: ${res.error}`);
      }
    } catch (err: any) {
      setClickStatus(`Error: ${err.message}`);
    } finally {
      setTimeout(() => setClickStatus(null), 3500);
    }
  };

  const handleLaunchApp = async (appName: string) => {
    setClickStatus(`Launching ${appName}...`);
    try {
      const res = await executeComputerAction({ action: 'launch_app', app_name: appName });
      setClickStatus(res.result || `Launched ${appName}`);
    } catch (err: any) {
      setClickStatus(`Launch error: ${err.message}`);
    } finally {
      setTimeout(() => setClickStatus(null), 3000);
      onRefresh();
    }
  };

  const handleAdjustVolume = async (action: 'up' | 'down' | 'mute') => {
    try {
      const res = await executeComputerAction({ action: 'volume', text: action });
      setAudioStatus(res.result || `Volume ${action}`);
    } catch {
      setAudioStatus('Failed to adjust volume');
    } finally {
      setTimeout(() => setAudioStatus(null), 3000);
    }
  };

  const handleSwitchAudio = async (devName: string, dir: string) => {
    setAudioStatus(`Switching default ${dir} to ${devName}...`);
    try {
      const res = await executeComputerAction({
        action: 'switch_audio',
        device_name: devName,
        direction: dir,
      });
      setAudioStatus(res.result || `Switched to ${devName}`);
    } catch {
      setAudioStatus('Failed to switch audio endpoint');
    } finally {
      setTimeout(() => setAudioStatus(null), 3500);
    }
  };

  return (
    <aside className="w-[420px] border-l border-white/10 bg-[#080a11] flex flex-col h-full flex-shrink-0 z-20 text-slate-200 font-sans">
      {/* Header */}
      <div className="p-4 border-b border-white/10 flex items-center justify-between bg-[#0a0d17]/80 backdrop-blur-md">
        <div className="flex items-center gap-2">
          <Monitor className="w-4 h-4 text-cyan-400" />
          <span className="text-xs font-bold uppercase tracking-wider text-white">
            Computer-Use & Vision Grounding
          </span>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded-lg hover:bg-white/10 text-slate-400 hover:text-white transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Safety Notice */}
      <div className="px-4 py-2 bg-emerald-500/10 border-b border-emerald-500/20 flex items-center justify-between text-xs text-emerald-300">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <span className="font-medium text-[11px]">Hardware Mouse Fail-Safe Armed</span>
        </div>
        <span className="text-[10px] font-mono bg-emerald-500/20 px-1.5 py-0.5 rounded border border-emerald-500/30">
          PROTECTED
        </span>
      </div>

      {/* Main Content */}
      <div className="flex-1 p-4 flex flex-col gap-4 overflow-y-auto">
        {/* Screenshot Viewport */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span className="font-semibold text-[11px] uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
              <MousePointer className="w-3.5 h-3.5 text-cyan-400" />
              <span>Interactive Desktop Canvas</span>
            </span>
            <button
              onClick={onRefresh}
              disabled={isCapturing}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-slate-200 transition-all disabled:opacity-50 text-[11px]"
            >
              <RefreshCw className={`w-3 h-3 ${isCapturing ? 'animate-spin' : ''}`} />
              <span>{isCapturing ? 'GDI Capturing...' : 'Capture Display'}</span>
            </button>
          </div>

          <div
            onClick={handleCanvasClick}
            className="w-full aspect-video rounded-xl border border-white/10 bg-[#030408] overflow-hidden flex items-center justify-center relative shadow-2xl cursor-crosshair group"
            title="Click anywhere to ground coordinates and dispatch real Win32 click"
          >
            {screenshotUrl ? (
              <>
                <img
                  ref={imgRef}
                  src={screenshotUrl}
                  alt="Live Desktop View"
                  className="w-full h-full object-contain pointer-events-none select-none"
                />
                <div className="absolute inset-0 bg-cyan-500/0 group-hover:bg-cyan-500/5 transition-all flex items-end justify-center p-2">
                  <span className="opacity-0 group-hover:opacity-100 text-[10px] font-mono bg-black/80 text-cyan-300 px-2 py-0.5 rounded border border-cyan-500/40 backdrop-blur-sm transition-opacity">
                    Click to dispatch hardware mouse click
                  </span>
                </div>
              </>
            ) : (
              <div className="flex flex-col items-center gap-2 text-slate-500 text-xs">
                <Monitor className="w-8 h-8 opacity-40" />
                <span>No live display capture yet. Click Capture.</span>
              </div>
            )}
          </div>

          {clickStatus && (
            <div className="text-[11px] font-mono text-cyan-300 bg-cyan-950/40 p-2 rounded-lg border border-cyan-500/30 flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400" />
              <span>{clickStatus}</span>
            </div>
          )}

          {lastCaptureTime && (
            <div className="text-[10px] text-slate-500 font-mono text-right">
              Perception Grounding: {lastCaptureTime}
            </div>
          )}
        </div>

        {/* Real Audio Endpoint Control */}
        <div className="p-3 rounded-xl border border-white/10 bg-[#0d101d] space-y-2.5">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
              <Volume2 className="w-3.5 h-3.5 text-pink-400" />
              <span>Windows Audio Endpoints</span>
            </span>
            <div className="flex items-center gap-1">
              <button
                onClick={() => handleAdjustVolume('up')}
                className="px-2 py-0.5 rounded bg-white/5 hover:bg-white/10 border border-white/10 text-[10px] font-mono text-slate-300"
              >
                Vol +
              </button>
              <button
                onClick={() => handleAdjustVolume('down')}
                className="px-2 py-0.5 rounded bg-white/5 hover:bg-white/10 border border-white/10 text-[10px] font-mono text-slate-300"
              >
                Vol -
              </button>
              <button
                onClick={() => handleAdjustVolume('mute')}
                className="p-1 rounded bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300"
                title="Mute/Unmute"
              >
                <VolumeX className="w-3 h-3 text-red-400" />
              </button>
            </div>
          </div>

          {audioStatus && (
            <div className="text-[10px] font-mono text-pink-300 bg-pink-950/30 p-1.5 rounded border border-pink-500/30">
              {audioStatus}
            </div>
          )}

          <div className="space-y-1">
            <button
              onClick={() => handleSwitchAudio('Speakers (Realtek(R) Audio)', 'output')}
              className="w-full text-left p-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-[11px] font-mono flex items-center justify-between"
            >
              <span>🔊 Speakers (Realtek(R) Audio)</span>
              <span className="text-[9px] text-emerald-400">Default Output</span>
            </button>
            <button
              onClick={() => handleSwitchAudio('Microphone (Maono AI Microphone)', 'input')}
              className="w-full text-left p-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-[11px] font-mono flex items-center justify-between"
            >
              <span>🎙️ Maono AI Microphone</span>
              <span className="text-[9px] text-cyan-400">Input</span>
            </button>
          </div>
        </div>

        {/* Quick App Launchers */}
        <div className="p-3 rounded-xl border border-white/10 bg-[#0d101d] space-y-2">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
            <Play className="w-3.5 h-3.5 text-emerald-400" />
            <span>Autonomous App Launch</span>
          </span>
          <div className="grid grid-cols-2 gap-1.5">
            <button
              onClick={() => handleLaunchApp('notepad')}
              className="p-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-[11px] font-mono flex items-center gap-1.5"
            >
              <FileText className="w-3.5 h-3.5 text-blue-400" />
              <span>Notepad</span>
            </button>
            <button
              onClick={() => handleLaunchApp('calculator')}
              className="p-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-[11px] font-mono flex items-center gap-1.5"
            >
              <Calculator className="w-3.5 h-3.5 text-amber-400" />
              <span>Calculator</span>
            </button>
            <button
              onClick={() => handleLaunchApp('terminal')}
              className="p-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-[11px] font-mono flex items-center gap-1.5"
            >
              <Terminal className="w-3.5 h-3.5 text-emerald-400" />
              <span>Terminal</span>
            </button>
            <button
              onClick={() => handleLaunchApp('code')}
              className="p-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-[11px] font-mono flex items-center gap-1.5"
            >
              <Sparkles className="w-3.5 h-3.5 text-violet-400" />
              <span>VS Code</span>
            </button>
          </div>
        </div>
      </div>
    </aside>
  );
};
