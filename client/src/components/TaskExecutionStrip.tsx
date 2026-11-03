import React, { useState } from 'react';
import {
  Terminal,
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  Loader2,
  AlertCircle,
  Monitor,
  Play,
  Camera,
  Volume2,
  Zap,
  ArrowRight
} from 'lucide-react';
import { ToolCall } from '../types';

interface TaskExecutionStripProps {
  toolCalls: ToolCall[];
}

export const TaskExecutionStrip: React.FC<TaskExecutionStripProps> = ({ toolCalls }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [expandedStepId, setExpandedStepId] = useState<string | null>(null);

  if (!toolCalls || toolCalls.length === 0) return null;

  const hasRunning = toolCalls.some(t => t.status === 'running');
  const hasError = toolCalls.some(t => t.status === 'error');

  const getToolIcon = (toolName: string) => {
    const name = toolName.toLowerCase();
    if (name.includes('vision') || name.includes('screenshot')) return <Camera className="w-3 h-3 text-sky-400" />;
    if (name.includes('computer') || name.includes('settings')) return <Monitor className="w-3 h-3 text-indigo-400" />;
    if (name.includes('audio') || name.includes('volume')) return <Volume2 className="w-3 h-3 text-pink-400" />;
    if (name.includes('launch') || name.includes('play') || name.includes('game')) return <Play className="w-3 h-3 text-emerald-400" />;
    return <Terminal className="w-3 h-3 text-slate-400" />;
  };

  const getParamSummary = (params: Record<string, any>) => {
    if (!params || Object.keys(params).length === 0) return '';
    const firstVal = Object.values(params)[0];
    if (typeof firstVal === 'string') return firstVal.length > 25 ? firstVal.slice(0, 25) + '…' : firstVal;
    if (typeof firstVal === 'number') return `${Object.keys(params)[0]}: ${firstVal}`;
    return Object.keys(params).join(', ');
  };

  // Single Tool Compact View
  if (toolCalls.length === 1) {
    const single = toolCalls[0];
    const isRunning = single.status === 'running';
    const isErr = single.status === 'error';
    const paramPreview = getParamSummary(single.params);

    return (
      <div className="w-full my-1 rounded-xl border border-white/[0.08] bg-[#11131f]/90 overflow-hidden text-xs transition-all shadow-sm">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="w-full px-3 py-1.5 flex items-center justify-between hover:bg-white/[0.04] transition-colors"
        >
          <div className="flex items-center gap-2 min-w-0">
            {getToolIcon(single.tool)}
            <span className="font-mono text-slate-200 font-medium truncate text-[11px]">
              {single.tool}
            </span>
            {paramPreview && (
              <span className="text-[10px] font-mono text-slate-400 bg-white/[0.05] px-1.5 py-0.5 rounded border border-white/[0.05] truncate max-w-[180px]">
                {paramPreview}
              </span>
            )}
          </div>

          <div className="flex items-center gap-2 flex-shrink-0">
            {isRunning ? (
              <span className="flex items-center gap-1 text-[10px] text-amber-400 font-mono">
                <Loader2 className="w-3 h-3 animate-spin" />
                <span>running</span>
              </span>
            ) : isErr ? (
              <span className="flex items-center gap-1 text-[10px] text-red-400 font-mono">
                <AlertCircle className="w-3 h-3" />
                <span>error</span>
              </span>
            ) : (
              <span className="flex items-center gap-1 text-[10px] text-emerald-400 font-mono">
                <CheckCircle2 className="w-3 h-3" />
                <span>done</span>
              </span>
            )}
            <span className="text-slate-400">
              {isExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
            </span>
          </div>
        </button>

        {isExpanded && (
          <div className="p-2.5 border-t border-white/[0.06] bg-[#090b14] space-y-2 font-mono text-[11px]">
            {single.params && Object.keys(single.params).length > 0 && (
              <div>
                <span className="text-slate-400 text-[10px] uppercase font-semibold block mb-0.5">Parameters</span>
                <pre className="p-2 rounded-lg bg-black/40 border border-white/[0.06] text-slate-300 overflow-x-auto text-[10px]">
                  {JSON.stringify(single.params, null, 2)}
                </pre>
              </div>
            )}
            {single.result && (
              <div>
                <span className="text-slate-400 text-[10px] uppercase font-semibold block mb-0.5">Result</span>
                <pre className="p-2 rounded-lg bg-black/40 border border-white/[0.06] text-emerald-300 whitespace-pre-wrap overflow-x-auto max-h-48 text-[10px] leading-relaxed">
                  {single.result}
                </pre>
              </div>
            )}
          </div>
        )}
      </div>
    );
  }

  // Multi-Tool Consolidated High-Density Strip
  return (
    <div className="w-full my-1 rounded-xl border border-white/[0.08] bg-[#11131f]/90 overflow-hidden text-xs transition-all shadow-sm">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-3 py-1.5 flex items-center justify-between hover:bg-white/[0.04] transition-colors gap-2"
      >
        <div className="flex items-center gap-2 min-w-0 overflow-hidden">
          <div className="p-1 rounded-md bg-violet-600/20 text-violet-400 border border-violet-500/30 flex-shrink-0">
            <Zap className="w-3 h-3" />
          </div>

          <span className="font-semibold text-white text-[11px] whitespace-nowrap">
            {hasRunning ? 'Executing Pipeline' : `${toolCalls.length} Steps Completed`}
          </span>

          {/* Inline pipeline breadcrumb chips */}
          <div className="hidden sm:flex items-center gap-1 overflow-hidden truncate">
            {toolCalls.map((tc, idx) => (
              <React.Fragment key={tc.id || idx}>
                {idx > 0 && <ArrowRight className="w-2.5 h-2.5 text-slate-500 flex-shrink-0" />}
                <span className="text-[10px] font-mono text-slate-300 bg-white/[0.05] px-1.5 py-0.5 rounded border border-white/[0.05] truncate">
                  {tc.tool}
                </span>
              </React.Fragment>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          {hasRunning ? (
            <span className="flex items-center gap-1 text-[10px] text-amber-400 font-mono">
              <Loader2 className="w-3 h-3 animate-spin" />
              <span>in progress</span>
            </span>
          ) : hasError ? (
            <span className="flex items-center gap-1 text-[10px] text-red-400 font-mono">
              <AlertCircle className="w-3 h-3" />
              <span>warning</span>
            </span>
          ) : (
            <span className="flex items-center gap-1 text-[10px] text-emerald-400 font-mono">
              <CheckCircle2 className="w-3 h-3" />
              <span>done</span>
            </span>
          )}
          <span className="text-[11px] font-medium text-slate-400 hover:text-white flex items-center gap-0.5">
            <span>{isExpanded ? 'Hide' : 'Details'}</span>
            {isExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
          </span>
        </div>
      </button>

      {/* High-Density Nested Step Drawer */}
      {isExpanded && (
        <div className="p-2 border-t border-white/[0.06] bg-[#090b14] space-y-1 font-mono text-[11px]">
          {toolCalls.map((tc, idx) => {
            const isStepExpanded = expandedStepId === tc.id;
            const isStepRunning = tc.status === 'running';
            const paramPreview = getParamSummary(tc.params);

            return (
              <div key={tc.id || idx} className="rounded-lg border border-white/[0.05] bg-white/[0.02] overflow-hidden">
                <button
                  onClick={() => setExpandedStepId(isStepExpanded ? null : tc.id)}
                  className="w-full px-2.5 py-1.5 flex items-center justify-between text-left hover:bg-white/[0.03] transition-colors"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="text-[10px] font-mono text-slate-500 w-4">{idx + 1}.</span>
                    {getToolIcon(tc.tool)}
                    <span className="text-[11px] font-mono font-medium text-slate-200 truncate">
                      {tc.tool}
                    </span>
                    {paramPreview && (
                      <span className="text-[10px] font-mono text-slate-400 bg-white/[0.04] px-1.5 py-0.2 rounded truncate max-w-[200px]">
                        {paramPreview}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-2 flex-shrink-0">
                    {isStepRunning ? (
                      <Loader2 className="w-3 h-3 text-amber-400 animate-spin" />
                    ) : tc.status === 'error' ? (
                      <AlertCircle className="w-3 h-3 text-red-400" />
                    ) : (
                      <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                    )}
                    <span className="text-slate-500">
                      {isStepExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                    </span>
                  </div>
                </button>

                {isStepExpanded && (
                  <div className="p-2.5 border-t border-white/[0.04] bg-black/40 space-y-1.5 text-[10px]">
                    {tc.params && Object.keys(tc.params).length > 0 && (
                      <div>
                        <span className="text-slate-500 uppercase font-semibold block mb-0.5">Parameters</span>
                        <pre className="p-1.5 rounded bg-black/60 border border-white/[0.05] text-slate-300 overflow-x-auto">
                          {JSON.stringify(tc.params, null, 2)}
                        </pre>
                      </div>
                    )}
                    {tc.result && (
                      <div>
                        <span className="text-slate-500 uppercase font-semibold block mb-0.5">Output</span>
                        <pre className="p-1.5 rounded bg-black/60 border border-white/[0.05] text-emerald-300 whitespace-pre-wrap overflow-x-auto max-h-40 leading-relaxed">
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
      )}
    </div>
  );
};
