import React, { useState, useRef, useEffect } from 'react';
import { ArrowUp, Monitor, Zap } from 'lucide-react';

interface ComposerProps {
  onSend: (text: string) => void;
  isLoading: boolean;
  computerUseEnabled: boolean;
  onToggleComputerUse: () => void;
}

export const Composer: React.FC<ComposerProps> = ({
  onSend,
  isLoading,
  computerUseEnabled,
  onToggleComputerUse,
}) => {
  const [text, setText] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
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

  return (
    <div className="w-full max-w-3xl mx-auto px-4 pb-4 pt-2">
      <div className="relative rounded-2xl border border-[#2b2d38] bg-[#171820] shadow-2xl transition-all focus-within:border-indigo-500/60 focus-within:ring-1 focus-within:ring-indigo-500/30">
        {/* Text Input Area */}
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            computerUseEnabled
              ? "Computer Use active. Ask Dione to open apps, control settings, or click coordinates..."
              : "Message Dione (Enter to send, Shift+Enter for new line)..."
          }
          rows={1}
          className="w-full pt-3.5 px-4 pb-2 bg-transparent text-[#e4e5e9] placeholder-[#5d6170] text-sm resize-none focus:outline-none min-h-[44px] max-h-[180px] leading-relaxed"
        />

        {/* Bottom Toolbar inside Composer */}
        <div className="px-3 pb-2.5 pt-1 flex items-center justify-between">
          {/* Mode Pill Button (Computer Use) */}
          <button
            type="button"
            onClick={onToggleComputerUse}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
              computerUseEnabled
                ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/40 shadow-sm'
                : 'text-[#6c7080] hover:text-[#c4c7d4] hover:bg-[#20222b]'
            }`}
            title="Toggle autonomous desktop interaction mode"
          >
            <Monitor className="w-3.5 h-3.5 text-indigo-400" />
            <span>Computer Use</span>
            {computerUseEnabled && (
              <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse ml-0.5" />
            )}
          </button>

          {/* Model info & Send Button */}
          <div className="flex items-center gap-3">
            <span className="text-[11px] text-[#555866] font-mono hidden sm:inline">
              MAF 1.20.0 · Gemini 3.5 Flash
            </span>

            <button
              onClick={() => handleSubmit()}
              disabled={!text.trim() || isLoading}
              className={`w-8 h-8 rounded-full flex items-center justify-center transition-all ${
                text.trim() && !isLoading
                  ? 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-md'
                  : 'bg-[#252733] text-[#535665] cursor-not-allowed'
              }`}
            >
              <ArrowUp className="w-4 h-4 stroke-[2.5]" />
            </button>
          </div>
        </div>
      </div>

      <div className="text-[11px] text-[#4d505e] text-center mt-2 flex items-center justify-center gap-2">
        <span>Dione Autonomous Large Action Model</span>
        <span>·</span>
        <span>AG-UI Streaming Protocol</span>
      </div>
    </div>
  );
};
