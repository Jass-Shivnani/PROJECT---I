import React from 'react';
import { X, RefreshCw, ShieldCheck, Monitor, ExternalLink } from 'lucide-react';

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
  if (!isOpen) return null;

  return (
    <aside className="w-96 border-l border-[#242630] bg-[#13141a] flex flex-col h-full flex-shrink-0 z-20">
      {/* Header */}
      <div className="p-3.5 border-b border-[#242630] flex items-center justify-between bg-[#161820]">
        <div className="flex items-center gap-2">
          <Monitor className="w-4 h-4 text-indigo-400" />
          <span className="text-xs font-semibold text-white">Desktop Vision & Control</span>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded hover:bg-[#232530] text-[#7d8190] hover:text-white transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Safety Notice */}
      <div className="p-3 bg-amber-500/10 border-b border-amber-500/20 flex items-start gap-2.5 text-xs text-amber-200">
        <ShieldCheck className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
        <div className="leading-snug">
          <span className="font-semibold block text-amber-300">Fail-Safe Active</span>
          Physical mouse movement will instantly halt any automated desktop action.
        </div>
      </div>

      {/* Screenshot Canvas */}
      <div className="flex-1 p-4 flex flex-col gap-3 overflow-y-auto">
        <div className="flex items-center justify-between text-xs text-[#8c90a0]">
          <span>Live Display Perception</span>
          <button
            onClick={onRefresh}
            disabled={isCapturing}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-[#20222c] hover:bg-[#292c39] text-[#cdd0dc] transition-all disabled:opacity-50 text-[11px]"
          >
            <RefreshCw className={`w-3 h-3 ${isCapturing ? 'animate-spin' : ''}`} />
            <span>{isCapturing ? 'Capturing...' : 'Capture Now'}</span>
          </button>
        </div>

        <div className="w-full aspect-video rounded-xl border border-[#262834] bg-[#0c0d12] overflow-hidden flex items-center justify-center relative shadow-inner">
          {screenshotUrl ? (
            <img
              src={screenshotUrl}
              alt="Live Desktop View"
              className="w-full h-full object-contain cursor-zoom-in"
              onClick={() => {
                const w = window.open('');
                w?.document.write(`<img src="${screenshotUrl}" style="max-width:100%"/>`);
              }}
            />
          ) : (
            <div className="flex flex-col items-center gap-2 text-[#5e6271] text-xs">
              <Monitor className="w-8 h-8 opacity-40" />
              <span>No screen capture available yet</span>
            </div>
          )}
        </div>

        {lastCaptureTime && (
          <span className="text-[10px] text-[#5e6271] font-mono text-center">
            Last capture: {lastCaptureTime}
          </span>
        )}

        {/* Available Computer Use Actions */}
        <div className="mt-2 p-3 rounded-lg border border-[#232530] bg-[#161820] text-xs">
          <span className="text-[11px] font-semibold text-[#8c90a0] block mb-2 uppercase tracking-wider">
            Available Computer Use Tools
          </span>
          <ul className="space-y-1.5 text-[11px] font-mono text-[#a5a9b8]">
            <li className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
              <span>launch_app (Spotify, Chrome, VS Code)</span>
            </li>
            <li className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
              <span>open_settings (Sound, Bluetooth, Wifi)</span>
            </li>
            <li className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
              <span>adjust_volume & media_control</span>
            </li>
            <li className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
              <span>click_coords & type_text (Win32)</span>
            </li>
            <li className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
              <span>take_screenshot & vision_inspect</span>
            </li>
          </ul>
        </div>
      </div>
    </aside>
  );
};
