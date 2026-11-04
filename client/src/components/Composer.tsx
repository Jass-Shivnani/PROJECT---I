import React, { useState, useRef, useEffect } from 'react';
import {
  ArrowUp,
  Monitor,
  Mic,
  MicOff,
  ChevronDown,
  Check,
  RefreshCw,
  Radio
} from 'lucide-react';
import { NeuralAudioClient, AudioDeviceOption } from '../services/neuralAudio';

interface ComposerProps {
  onSend: (text: string) => void;
  isLoading: boolean;
  computerUseEnabled: boolean;
  onToggleComputerUse: () => void;
  isListening?: boolean;
  voiceStatusText?: string;
  voiceVolume?: number;
  selectedMicId?: string;
  onSelectMic?: (deviceId: string) => void;
  onToggleMic?: () => void;
}

export const Composer: React.FC<ComposerProps> = ({
  onSend,
  isLoading,
  computerUseEnabled,
  onToggleComputerUse,
  isListening = false,
  voiceStatusText = '',
  voiceVolume = 0,
  selectedMicId = '',
  onSelectMic,
  onToggleMic,
}) => {
  const [text, setText] = useState('');
  const [micDevices, setMicDevices] = useState<AudioDeviceOption[]>([]);
  const [isMicMenuOpen, setIsMicMenuOpen] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const micMenuRef = useRef<HTMLDivElement>(null);

  const loadDevices = async () => {
    const { inputs } = await NeuralAudioClient.getAudioDevices();
    setMicDevices(inputs);
  };

  useEffect(() => {
    loadDevices();
    navigator.mediaDevices?.addEventListener?.('devicechange', loadDevices);
    return () => {
      navigator.mediaDevices?.removeEventListener?.('devicechange', loadDevices);
    };
  }, []);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (micMenuRef.current && !micMenuRef.current.contains(e.target as Node)) {
        setIsMicMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 150)}px`;
    }
  }, [text]);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!text.trim() || isLoading) return;
    onSend(text.trim());
    setText('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const activeMicLabel =
    micDevices.find(d => d.deviceId === selectedMicId)?.label ||
    micDevices[0]?.label ||
    'Default Microphone';

  return (
    <div className="w-full max-w-3xl mx-auto px-4 pb-4 pt-1">
      {/* 1-Click Live Demo Deck Bar */}
      <div className="mb-2 flex items-center gap-1.5 overflow-x-auto pb-1 text-[11px] scrollbar-none select-none">
        <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500 whitespace-nowrap mr-1 flex items-center gap-1">
          <span>⚡</span> Live Demo Deck:
        </span>
        {[
          { label: '🎨 Paint Circle', prompt: 'open paint and draw a circle' },
          { label: '⭐ Star & Heart', prompt: 'open paint and draw a star and a heart' },
          { label: '🏠 Paint House', prompt: 'open paint and draw a house' },
          { label: '📝 Notepad Note', prompt: "open notepad and write 'Dione Autonomous Agent v7.0 Ready'" },
          { label: '🐍 Hermes PTC', prompt: 'use execute_code to list the workspace directory and summarize core modules' },
          { label: '☁️ Drive & Photos', prompt: 'search my Google Drive files and list my recent Google Photos' },
          { label: '▶️ YouTube Lofi', prompt: 'play lofi hip hop radio on youtube in full screen' },
          { label: '🖥️ System Info', prompt: 'check my system hardware and resource usage' },
        ].map((item, idx) => (
          <button
            key={idx}
            type="button"
            disabled={isLoading}
            onClick={() => onSend(item.prompt)}
            className="px-2.5 py-1 rounded-full bg-white/[0.04] hover:bg-white/[0.09] border border-white/[0.08] hover:border-violet-500/40 text-slate-300 hover:text-white whitespace-nowrap transition-all duration-150 flex items-center gap-1 active:scale-95 disabled:opacity-40"
          >
            {item.label}
          </button>
        ))}
      </div>

      {/* Live Voice Status Strip when active */}
      {isListening && (
        <div className="mb-2 px-3.5 py-2 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-between text-xs text-emerald-200">
          <div className="flex items-center gap-2.5 min-w-0">
            <Radio className="w-3.5 h-3.5 text-emerald-400 animate-pulse flex-shrink-0" />
            <span className="font-medium truncate">{voiceStatusText || 'Gemini Live + 3.8 Extended Thinking Active'}</span>
            <span className="text-[10px] font-mono text-emerald-300/80 truncate hidden sm:inline">
              ({activeMicLabel})
            </span>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <div className="w-16 h-1.5 rounded-full bg-black/40 overflow-hidden">
              <div
                className="h-full bg-emerald-400 transition-all duration-75"
                style={{ width: `${Math.min(100, Math.round((voiceVolume || 0) * 100))}%` }}
              />
            </div>
            <button
              onClick={onToggleMic}
              className="px-2 py-0.5 rounded bg-red-500/20 hover:bg-red-500/30 text-red-300 text-[10px] font-mono"
            >
              Stop Voice
            </button>
          </div>
        </div>
      )}

      {/* Main Composer Box */}
      <div className="relative rounded-2xl border border-white/[0.12] bg-[#10121a]/95 backdrop-blur-xl shadow-2xl transition-all focus-within:border-violet-500/70">
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Message Dione or command apps, browser, emails, calendar, or files..."
          disabled={isLoading}
          rows={1}
          className="w-full bg-transparent px-4 pt-3.5 pb-2 text-[13px] text-white placeholder-slate-400 focus:outline-none resize-none leading-relaxed min-h-[42px]"
        />

        <div className="flex items-center justify-between px-3 pb-2.5 pt-1">
          <div className="flex items-center gap-1.5">
            {/* Split Mic Toggle + Hardware Microphone Selector */}
            {onToggleMic && (
              <div className="relative flex items-center rounded-lg border border-white/[0.08] bg-white/[0.02]" ref={micMenuRef}>
                <button
                  type="button"
                  onClick={onToggleMic}
                  className={`px-2 py-1.5 rounded-l-lg flex items-center gap-1.5 text-xs transition-all ${
                    isListening
                      ? 'bg-emerald-500/20 text-emerald-300 font-medium'
                      : 'text-slate-300 hover:text-white hover:bg-white/[0.05]'
                  }`}
                  title={isListening ? 'Disconnect Live Voice' : `Start Live Voice (${activeMicLabel})`}
                >
                  {isListening ? <Mic className="w-3.5 h-3.5 text-emerald-400" /> : <MicOff className="w-3.5 h-3.5 text-slate-400" />}
                  <span className="text-[11px] hidden sm:inline max-w-[140px] truncate">
                    {isListening ? 'Live ON' : activeMicLabel}
                  </span>
                </button>

                <button
                  type="button"
                  onClick={() => {
                    loadDevices();
                    setIsMicMenuOpen(!isMicMenuOpen);
                  }}
                  className="px-1.5 py-1.5 rounded-r-lg border-l border-white/[0.08] text-slate-400 hover:text-white hover:bg-white/[0.06] transition-all"
                  title="Select Microphone Input Device"
                >
                  <ChevronDown className="w-3 h-3" />
                </button>

                {/* Microphone Device Picker Popover */}
                {isMicMenuOpen && (
                  <div className="absolute bottom-full left-0 mb-2 w-72 rounded-xl bg-[#0c0e18] border border-white/[0.12] shadow-2xl p-2 z-50 space-y-1">
                    <div className="flex items-center justify-between px-2 py-1 border-b border-white/[0.06]">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                        Select Microphone Input
                      </span>
                      <button
                        type="button"
                        onClick={loadDevices}
                        className="p-1 rounded hover:bg-white/[0.06] text-slate-400 hover:text-white"
                        title="Refresh Audio Devices"
                      >
                        <RefreshCw className="w-3 h-3" />
                      </button>
                    </div>
                    {micDevices.length === 0 ? (
                      <div className="px-2 py-2 text-[11px] text-slate-400">
                        No microphones found. Click the Mic icon to grant browser permission.
                      </div>
                    ) : (
                      <div className="max-h-48 overflow-y-auto space-y-0.5">
                        {micDevices.map((dev) => {
                          const isSelected = dev.deviceId === selectedMicId || (!selectedMicId && dev === micDevices[0]);
                          return (
                            <button
                              key={dev.deviceId}
                              type="button"
                              onClick={() => {
                                onSelectMic?.(dev.deviceId);
                                setIsMicMenuOpen(false);
                              }}
                              className={`w-full px-2.5 py-1.5 rounded-lg text-left text-xs flex items-center justify-between gap-2 transition-all ${
                                isSelected
                                  ? 'bg-violet-600/20 text-white font-medium border border-violet-500/30'
                                  : 'text-slate-300 hover:bg-white/[0.05] hover:text-white'
                              }`}
                            >
                              <span className="truncate">{dev.label}</span>
                              {isSelected && <Check className="w-3.5 h-3.5 text-violet-400 flex-shrink-0" />}
                            </button>
                          );
                        })}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            <button
              type="button"
              onClick={onToggleComputerUse}
              className={`px-2 py-1.5 rounded-lg border text-[11px] flex items-center gap-1.5 transition-all ${
                computerUseEnabled
                  ? 'bg-cyan-500/15 border-cyan-500/30 text-cyan-300'
                  : 'border-white/[0.08] text-slate-400 hover:text-white hover:bg-white/[0.05]'
              }`}
              title={computerUseEnabled ? 'Desktop Computer-Use Enabled' : 'Desktop Computer-Use Disabled'}
            >
              <Monitor className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Desktop Control</span>
            </button>
          </div>

          <button
            type="button"
            onClick={() => handleSubmit()}
            disabled={!text.trim() || isLoading}
            className={`p-1.5 rounded-xl transition-all flex items-center justify-center ${
              text.trim() && !isLoading
                ? 'bg-violet-600 hover:bg-violet-500 text-white shadow-md shadow-violet-600/30'
                : 'bg-white/[0.05] text-slate-400 cursor-not-allowed'
            }`}
            title="Send (Enter)"
          >
            <ArrowUp className="w-4 h-4 stroke-[2.5]" />
          </button>
        </div>
      </div>
    </div>
  );
};
