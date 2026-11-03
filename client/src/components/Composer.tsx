import React, { useState, useRef, useEffect } from 'react';
import {
  ArrowUp,
  Monitor,
  Mic,
  Camera,
  BookOpen,
  Volume2,
  Cpu
} from 'lucide-react';

interface ComposerProps {
  onSend: (text: string) => void;
  isLoading: boolean;
  computerUseEnabled: boolean;
  onToggleComputerUse: () => void;
  isListening?: boolean;
  onToggleMic?: () => void;
}

export const Composer: React.FC<ComposerProps> = ({
  onSend,
  isLoading,
  computerUseEnabled,
  onToggleComputerUse,
  isListening,
  onToggleMic,
}) => {
  const [text, setText] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`;
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

  const handleChipClick = (promptText: string) => {
    onSend(promptText);
  };

  return (
    <div className="w-full max-w-3xl mx-auto px-4 pb-4 pt-1 space-y-2">
      {/* Subtle Jarvis Action Chips */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-0.5 text-[11px] font-sans no-scrollbar">
        <button
          onClick={() => handleChipClick("Take a desktop screenshot and check active windows")}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] text-slate-300 hover:text-white transition-all flex-shrink-0"
        >
          <Camera className="w-3 h-3 text-cyan-400" />
          <span>Screen & Windows</span>
        </button>
        <button
          onClick={() => handleChipClick("Search recent arXiv papers on autonomous agent systems")}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] text-slate-300 hover:text-white transition-all flex-shrink-0"
        >
          <BookOpen className="w-3 h-3 text-pink-400" />
          <span>arXiv Papers</span>
        </button>
        <button
          onClick={() => handleChipClick("Check system hardware telemetry and active audio endpoints")}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] text-slate-300 hover:text-white transition-all flex-shrink-0"
        >
          <Cpu className="w-3 h-3 text-emerald-400" />
          <span>Telemetry & Audio</span>
        </button>
      </div>

      {/* Floating Obsidian Capsule */}
      <div className="relative rounded-2xl border border-white/[0.12] bg-[#10121a]/95 backdrop-blur-xl shadow-2xl transition-all focus-within:border-violet-500/70 focus-within:ring-2 focus-within:ring-violet-500/10">
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask Dione or command workstation actions..."
          disabled={isLoading}
          rows={1}
          className="w-full bg-transparent px-4 pt-3.5 pb-2 text-[13px] text-white placeholder-slate-400 focus:outline-none resize-none leading-relaxed min-h-[44px]"
        />

        <div className="flex items-center justify-between px-3 pb-2.5 pt-1">
          <div className="flex items-center gap-1.5">
            {onToggleMic && (
              <button
                type="button"
                onClick={onToggleMic}
                className={`p-1.5 rounded-lg border transition-all ${
                  isListening
                    ? 'bg-emerald-500/20 border-emerald-500/40 text-emerald-300 animate-pulse'
                    : 'border-transparent text-slate-400 hover:text-white hover:bg-white/[0.05]'
                }`}
                title="Voice Input"
              >
                <Mic className="w-4 h-4" />
              </button>
            )}

            <button
              type="button"
              onClick={onToggleComputerUse}
              className={`p-1.5 rounded-lg border transition-all ${
                computerUseEnabled
                  ? 'bg-cyan-500/15 border-cyan-500/30 text-cyan-300'
                  : 'border-transparent text-slate-400 hover:text-white hover:bg-white/[0.05]'
              }`}
              title={computerUseEnabled ? "Computer Use Active" : "Enable Computer Use"}
            >
              <Monitor className="w-4 h-4" />
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
