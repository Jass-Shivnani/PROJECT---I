import React from 'react';
import { ChevronRight, CheckCircle2, Loader2, AlertCircle } from 'lucide-react';
import { ToolCall } from '../types';
import { resolveToolAction } from '../services/toolActionResolver';

interface StackedToolCallsProps {
  toolCalls: ToolCall[];
  onOpenActivity?: () => void;
}

export const StackedToolCalls: React.FC<StackedToolCallsProps> = ({
  toolCalls,
  onOpenActivity,
}) => {
  if (!toolCalls || toolCalls.length === 0) return null;

  const resolved = toolCalls.map(tc => resolveToolAction(tc));
  const hasRunning = toolCalls.some(t => t.status === 'running');
  const hasError = toolCalls.some(t => t.status === 'error');

  // Display up to 4 circular stacked icons
  const MAX_DISPLAY = 4;
  const displayItems = resolved.slice(0, MAX_DISPLAY);
  const overflowCount = resolved.length - MAX_DISPLAY;

  // Single action label vs multi-action label
  const labelText =
    resolved.length === 1
      ? resolved[0].title
      : `${resolved.length} actions executed`;

  return (
    <div className="w-full my-1.5 flex items-center">
      <button
        onClick={onOpenActivity}
        type="button"
        className="group inline-flex items-center gap-2.5 px-3 py-1.5 rounded-full bg-[#111320]/90 hover:bg-[#181a2c] border border-white/[0.08] hover:border-violet-500/40 transition-all text-xs cursor-pointer shadow-sm shadow-black/40 select-none max-w-full"
        title="Click to view detailed execution ledger in Workstation Activity drawer"
      >
        {/* Stacked Circular Badges (Overlapping Left-to-Right) */}
        <div className="flex items-center -space-x-2 flex-shrink-0">
          {displayItems.map((item, idx) => (
            <div
              key={idx}
              className={`w-6 h-6 rounded-full flex items-center justify-center border-2 border-[#0c0e18] shadow-sm transition-transform group-hover:scale-105 ${item.badgeBg} ${item.badgeBorder} ${item.badgeText}`}
              title={item.title}
              style={{ zIndex: displayItems.length - idx }}
            >
              <span className="scale-[0.85]">{item.icon}</span>
            </div>
          ))}

          {overflowCount > 0 && (
            <div
              className="w-6 h-6 rounded-full flex items-center justify-center border-2 border-[#0c0e18] bg-slate-800 text-[10px] font-mono text-slate-300 font-bold shadow-sm"
              style={{ zIndex: 0 }}
            >
              +{overflowCount}
            </div>
          )}
        </div>

        {/* Small Line of What It Did */}
        <div className="min-w-0 flex-1 text-left">
          <span className="font-sans text-[11.5px] font-medium text-slate-200 group-hover:text-white truncate block max-w-[260px] sm:max-w-[420px]">
            {labelText}
          </span>
        </div>

        {/* Execution Status Badge & Chevron */}
        <div className="flex items-center gap-1.5 flex-shrink-0 text-slate-400 pl-1">
          {hasRunning ? (
            <span className="flex items-center gap-1 text-[10px] font-mono text-amber-400">
              <Loader2 className="w-3 h-3 animate-spin" />
              <span className="hidden sm:inline">running</span>
            </span>
          ) : hasError ? (
            <span className="flex items-center gap-1 text-[10px] font-mono text-rose-400">
              <AlertCircle className="w-3 h-3" />
              <span className="hidden sm:inline">error</span>
            </span>
          ) : (
            <span className="flex items-center gap-1 text-[10px] font-mono text-emerald-400">
              <CheckCircle2 className="w-3 h-3" />
              <span className="hidden sm:inline">done</span>
            </span>
          )}

          <ChevronRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-violet-400 group-hover:translate-x-0.5 transition-all" />
        </div>
      </button>
    </div>
  );
};
