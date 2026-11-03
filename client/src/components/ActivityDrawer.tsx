import React, { useState, useEffect, useRef } from 'react';
import {
  X,
  Layers,
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  Loader2,
  AlertCircle,
  Clock,
  Terminal,
  Search,
  Sparkles,
  ArrowRight
} from 'lucide-react';
import { Thread, ToolCall, Message } from '../types';
import { resolveToolAction, ResolvedAction } from '../services/toolActionResolver';

interface ActivityDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  thread: Thread | null;
  targetMessageId?: string | null;
}

interface PromptGroup {
  id: string;
  promptText: string;
  promptTime: string;
  assistantMessageId: string;
  toolCalls: ToolCall[];
}

export const ActivityDrawer: React.FC<ActivityDrawerProps> = ({
  isOpen,
  onClose,
  thread,
  targetMessageId,
}) => {
  const [expandedStepId, setExpandedStepId] = useState<string | null>(null);
  const [filterQuery, setFilterQuery] = useState('');
  const targetRef = useRef<HTMLDivElement | null>(null);

  // Group toolcalls by user prompt in execution order
  const promptGroups: PromptGroup[] = [];

  if (thread && thread.messages) {
    let currentPromptText = 'Initial Setup / Ambient Action';
    let currentPromptTime = '';

    thread.messages.forEach((msg, idx) => {
      if (msg.role === 'user') {
        currentPromptText = msg.content;
        currentPromptTime = msg.timestamp;
      } else if (msg.role === 'assistant' && msg.toolCalls && msg.toolCalls.length > 0) {
        promptGroups.push({
          id: `group-${msg.id || idx}`,
          promptText: currentPromptText,
          promptTime: currentPromptTime || msg.timestamp,
          assistantMessageId: msg.id,
          toolCalls: msg.toolCalls,
        });
      }
    });
  }

  // Auto-scroll to target group if opened via a specific message badge
  useEffect(() => {
    if (isOpen && targetMessageId && targetRef.current) {
      setTimeout(() => {
        targetRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }, 150);
    }
  }, [isOpen, targetMessageId]);

  if (!isOpen) return null;

  const totalActions = promptGroups.reduce((acc, g) => acc + g.toolCalls.length, 0);

  // Filter groups
  const filteredGroups = promptGroups.filter((g) => {
    if (!filterQuery.trim()) return true;
    const q = filterQuery.toLowerCase();
    return (
      g.promptText.toLowerCase().includes(q) ||
      g.toolCalls.some(
        (tc) =>
          tc.tool.toLowerCase().includes(q) ||
          (tc.params && JSON.stringify(tc.params).toLowerCase().includes(q))
      )
    );
  });

  return (
    <aside className="w-[480px] max-w-full border-l border-white/[0.08] bg-[#090b14]/95 backdrop-blur-2xl flex flex-col h-full z-30 shadow-2xl animate-in slide-in-from-right duration-200 select-none">
      {/* Header */}
      <div className="h-14 border-b border-white/[0.08] px-4 flex items-center justify-between flex-shrink-0 bg-white/[0.02]">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
            <Layers className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-semibold text-white tracking-tight">Workstation Activity</h2>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-full bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                {totalActions} actions
              </span>
            </div>
            <p className="text-[10px] text-slate-400">Grouped by prompt in execution order</p>
          </div>
        </div>

        <button
          onClick={onClose}
          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/[0.06] transition-colors"
          title="Close activity drawer"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Filter Bar */}
      <div className="p-3 border-b border-white/[0.06] bg-[#0a0c16]">
        <div className="relative">
          <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-2.5" />
          <input
            type="text"
            value={filterQuery}
            onChange={(e) => setFilterQuery(e.target.value)}
            placeholder="Filter actions by keyword or prompt..."
            className="w-full pl-8 pr-3 py-1.5 rounded-xl bg-white/[0.03] border border-white/[0.08] focus:border-indigo-500/40 text-xs text-white placeholder-slate-500 outline-none transition-all"
          />
        </div>
      </div>

      {/* Prompt Groups Ledger */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {filteredGroups.length === 0 ? (
          <div className="text-center py-12 text-slate-500 text-xs">
            <Layers className="w-8 h-8 mx-auto mb-2 opacity-30 text-slate-400" />
            <p className="font-medium text-slate-400">No activity recorded</p>
            <p className="text-[11px] text-slate-600 mt-1">Actions executed by Dione will appear here.</p>
          </div>
        ) : (
          filteredGroups.map((group, gIdx) => {
            const isTarget = group.assistantMessageId === targetMessageId;

            return (
              <div
                key={group.id}
                ref={isTarget ? targetRef : undefined}
                className={`rounded-2xl border transition-all ${
                  isTarget
                    ? 'border-indigo-500/50 bg-[#121526] shadow-lg shadow-indigo-500/10'
                    : 'border-white/[0.08] bg-[#0d0f1b]/90 hover:border-white/[0.12]'
                } overflow-hidden`}
              >
                {/* Prompt Header */}
                <div className="px-3.5 py-2.5 bg-white/[0.03] border-b border-white/[0.06] flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5 text-[10px] font-mono text-slate-400 mb-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-violet-400" />
                      <span className="font-semibold text-slate-300">Prompt #{gIdx + 1}</span>
                      <span>•</span>
                      <span>{group.promptTime}</span>
                    </div>
                    <p className="text-[12px] font-medium text-slate-200 line-clamp-2 leading-snug">
                      "{group.promptText}"
                    </p>
                  </div>

                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-white/[0.05] border border-white/[0.08] text-slate-300 flex-shrink-0">
                    {group.toolCalls.length} {group.toolCalls.length === 1 ? 'step' : 'steps'}
                  </span>
                </div>

                {/* Steps in Execution Order */}
                <div className="p-2.5 space-y-2">
                  {group.toolCalls.map((tc, stepIdx) => {
                    const resolved: ResolvedAction = resolveToolAction(tc);
                    const isStepExpanded = expandedStepId === tc.id;
                    const isRunning = tc.status === 'running';
                    const isErr = tc.status === 'error';

                    return (
                      <div
                        key={tc.id || stepIdx}
                        className="rounded-xl border border-white/[0.06] bg-[#080911] overflow-hidden transition-all hover:border-white/[0.1]"
                      >
                        {/* Step Item Row */}
                        <button
                          onClick={() => setExpandedStepId(isStepExpanded ? null : tc.id)}
                          className="w-full p-2.5 flex items-center justify-between text-left hover:bg-white/[0.02] transition-colors gap-3"
                        >
                          <div className="flex items-center gap-2.5 min-w-0 flex-1">
                            {/* Execution Order Number */}
                            <span className="text-[10px] font-mono text-slate-500 font-bold flex-shrink-0 w-4">
                              {String(stepIdx + 1).padStart(2, '0')}
                            </span>

                            {/* Semantic Category Icon (NOT PowerShell icon) */}
                            <div
                              className={`w-7 h-7 rounded-lg flex items-center justify-center border flex-shrink-0 ${resolved.badgeBg} ${resolved.badgeBorder} ${resolved.badgeText}`}
                            >
                              {resolved.icon}
                            </div>

                            {/* Friendly Semantic Label */}
                            <div className="min-w-0 flex-1">
                              <span className="font-sans text-[12px] font-medium text-white block truncate leading-tight">
                                {resolved.title}
                              </span>
                              <div className="flex items-center gap-2 mt-0.5">
                                <span className="text-[9.5px] font-mono text-slate-400">
                                  {resolved.isPowerShellOrCli
                                    ? 'CLI execution'
                                    : tc.tool}
                                </span>
                                {tc.timestamp && (
                                  <>
                                    <span className="text-slate-600 text-[9px]">•</span>
                                    <span className="text-[9.5px] font-mono text-slate-500">
                                      {tc.timestamp}
                                    </span>
                                  </>
                                )}
                              </div>
                            </div>
                          </div>

                          {/* Status Badge */}
                          <div className="flex items-center gap-2 flex-shrink-0">
                            {isRunning ? (
                              <span className="flex items-center gap-1 text-[10px] font-mono text-amber-400">
                                <Loader2 className="w-3 h-3 animate-spin" />
                                <span>running</span>
                              </span>
                            ) : isErr ? (
                              <span className="flex items-center gap-1 text-[10px] font-mono text-rose-400">
                                <AlertCircle className="w-3 h-3" />
                                <span>error</span>
                              </span>
                            ) : (
                              <span className="flex items-center gap-1 text-[10px] font-mono text-emerald-400">
                                <CheckCircle2 className="w-3 h-3" />
                                <span>done</span>
                              </span>
                            )}

                            <span className="text-slate-500 hover:text-white">
                              {isStepExpanded ? (
                                <ChevronDown className="w-3.5 h-3.5" />
                              ) : (
                                <ChevronRight className="w-3.5 h-3.5" />
                              )}
                            </span>
                          </div>
                        </button>

                        {/* Accordion: Raw Parameters & Execution Result */}
                        {isStepExpanded && (
                          <div className="p-3 border-t border-white/[0.06] bg-black/40 space-y-2.5 font-mono text-[10px] select-text">
                            {/* Parameters */}
                            {tc.params && Object.keys(tc.params).length > 0 && (
                              <div>
                                <span className="text-slate-500 uppercase font-semibold text-[9px] tracking-wider block mb-1">
                                  Parameters
                                </span>
                                <pre className="p-2 rounded-lg bg-black/60 border border-white/[0.06] text-slate-300 overflow-x-auto leading-relaxed">
                                  {JSON.stringify(tc.params, null, 2)}
                                </pre>
                              </div>
                            )}

                            {/* Execution Output / Result */}
                            {tc.result && (
                              <div>
                                <span className="text-slate-500 uppercase font-semibold text-[9px] tracking-wider block mb-1">
                                  Execution Result
                                </span>
                                <pre className="p-2 rounded-lg bg-black/60 border border-white/[0.06] text-emerald-300 whitespace-pre-wrap overflow-x-auto max-h-44 leading-relaxed">
                                  {tc.result}
                                </pre>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })
        )}
      </div>
    </aside>
  );
};
