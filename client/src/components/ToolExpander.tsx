import React, { useState } from 'react';
import { 
  Terminal, 
  ChevronDown, 
  ChevronRight, 
  CheckCircle2, 
  Loader2, 
  Monitor, 
  Play, 
  Camera, 
  Volume2 
} from 'lucide-react';
import { ToolCall } from '../types';

interface ToolExpanderProps {
  toolCall: ToolCall;
}

export const ToolExpander: React.FC<ToolExpanderProps> = ({ toolCall }) => {
  const [isOpen, setIsOpen] = useState(false);

  const getIcon = () => {
    const name = toolCall.tool.toLowerCase();
    if (name.includes('screenshot') || name.includes('vision')) return <Camera className="w-3.5 h-3.5 text-sky-400" />;
    if (name.includes('computer') || name.includes('settings')) return <Monitor className="w-3.5 h-3.5 text-indigo-400" />;
    if (name.includes('audio') || name.includes('volume')) return <Volume2 className="w-3.5 h-3.5 text-pink-400" />;
    if (name.includes('launch') || name.includes('app')) return <Play className="w-3.5 h-3.5 text-emerald-400" />;
    return <Terminal className="w-3.5 h-3.5 text-neutral-400" />;
  };

  const isRunning = toolCall.status === 'running';

  return (
    <div className="my-1.5 w-full max-w-xl text-xs rounded-lg border border-[#262830] bg-[#16171d] overflow-hidden transition-all">
      {/* Header Pill */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-3 py-2 flex items-center justify-between text-left hover:bg-[#1c1e25] transition-colors"
      >
        <div className="flex items-center gap-2 min-w-0">
          {getIcon()}
          <span className="font-mono text-[#c6c9d3] truncate font-medium">
            {toolCall.tool}
          </span>
          {toolCall.params && Object.keys(toolCall.params).length > 0 && !isOpen && (
            <span className="text-[11px] font-mono text-[#787c8a] truncate max-w-[200px]">
              {JSON.stringify(toolCall.params)}
            </span>
          )}
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          {isRunning ? (
            <span className="flex items-center gap-1 text-[11px] text-amber-400 font-mono">
              <Loader2 className="w-3 h-3 animate-spin" />
              <span>running</span>
            </span>
          ) : (
            <span className="flex items-center gap-1 text-[11px] text-emerald-400 font-mono">
              <CheckCircle2 className="w-3 h-3" />
              <span>done</span>
            </span>
          )}
          <span className="text-[#646875]">
            {isOpen ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
          </span>
        </div>
      </button>

      {/* Collapsible Details */}
      {isOpen && (
        <div className="p-3 border-t border-[#262830] bg-[#121318] flex flex-col gap-2 font-mono text-[11px]">
          {toolCall.params && Object.keys(toolCall.params).length > 0 && (
            <div>
              <span className="text-[#646875] text-[10px] uppercase font-semibold block mb-1">Parameters</span>
              <pre className="p-2 rounded bg-[#0a0a0d] border border-[#22242a] text-[#a1a5b4] overflow-x-auto">
                {JSON.stringify(toolCall.params, null, 2)}
              </pre>
            </div>
          )}
          {toolCall.result && (
            <div>
              <span className="text-[#646875] text-[10px] uppercase font-semibold block mb-1">Result</span>
              <pre className="p-2 rounded bg-[#0a0a0d] border border-[#22242a] text-[#86efac] whitespace-pre-wrap overflow-x-auto max-h-60">
                {toolCall.result}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
