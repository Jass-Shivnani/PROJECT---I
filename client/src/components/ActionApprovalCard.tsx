import React, { useState } from 'react';
import { ShieldAlert, CheckCircle, XCircle, Terminal, FileCode, AlertTriangle } from 'lucide-react';
import { SafetyApprovalRequest } from '../types';

interface ActionApprovalCardProps {
  request: SafetyApprovalRequest;
  onDecide: (confirmationId: string, approved: boolean) => Promise<void>;
  status?: 'pending' | 'approved' | 'denied';
}

export const ActionApprovalCard: React.FC<ActionApprovalCardProps> = ({
  request,
  onDecide,
  status = 'pending',
}) => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [currentStatus, setCurrentStatus] = useState<'pending' | 'approved' | 'denied'>(status);

  const handleAction = async (approved: boolean) => {
    setIsSubmitting(true);
    try {
      await onDecide(request.confirmation_id, approved);
      setCurrentStatus(approved ? 'approved' : 'denied');
    } catch (e) {
      console.error('Failed to submit approval decision:', e);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="my-3 rounded-2xl border border-amber-500/40 bg-gradient-to-br from-[#161208]/95 to-[#1c160b]/95 backdrop-blur-2xl p-4 shadow-2xl shadow-amber-950/20 text-slate-200 font-sans">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-amber-500/20 pb-3">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-amber-500/20 border border-amber-500/30 flex items-center justify-center text-amber-400">
            <ShieldAlert className="w-4 h-4" />
          </div>
          <div>
            <div className="text-xs font-bold text-amber-300 tracking-wide uppercase flex items-center gap-2">
              <span>Executive Authorization Required</span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 font-mono">
                Tier 4 Privileged
              </span>
            </div>
            <div className="text-[11px] text-amber-200/70">
              Dione requires your explicit consent before executing this mutating operation.
            </div>
          </div>
        </div>

        {currentStatus !== 'pending' && (
          <span
            className={`text-xs font-medium px-2.5 py-1 rounded-full border flex items-center gap-1.5 ${
              currentStatus === 'approved'
                ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                : 'bg-rose-500/20 text-rose-300 border-rose-500/40'
            }`}
          >
            {currentStatus === 'approved' ? (
              <>
                <CheckCircle className="w-3.5 h-3.5" /> Approved
              </>
            ) : (
              <>
                <XCircle className="w-3.5 h-3.5" /> Denied
              </>
            )}
          </span>
        )}
      </div>

      {/* Thought / Rationale */}
      {request.thought && (
        <div className="mt-3 text-xs text-slate-300 italic bg-white/[0.03] p-2.5 rounded-xl border border-white/5">
          "{request.thought}"
        </div>
      )}

      {/* Action Target Details */}
      <div className="mt-3 space-y-2">
        <div className="flex items-center justify-between text-xs font-mono text-slate-400">
          <span className="flex items-center gap-1.5 text-amber-300/90 font-semibold">
            <Terminal className="w-3.5 h-3.5" /> Tool: {request.tool}
          </span>
          <span className="text-[10px]">ID: {request.confirmation_id}</span>
        </div>

        <pre className="p-3 rounded-xl bg-[#090b10] border border-white/10 text-[11px] font-mono text-amber-100 overflow-x-auto leading-relaxed">
          {JSON.stringify(request.params, null, 2)}
        </pre>
      </div>

      {/* Decision Buttons */}
      {currentStatus === 'pending' && (
        <div className="mt-4 flex items-center justify-end gap-2.5 pt-2 border-t border-amber-500/20">
          <button
            onClick={() => handleAction(false)}
            disabled={isSubmitting}
            className="px-3.5 py-1.5 rounded-xl border border-white/10 hover:border-white/20 bg-white/[0.04] hover:bg-white/[0.08] text-xs font-medium text-slate-300 hover:text-white transition-all disabled:opacity-50"
          >
            Deny & Halt
          </button>
          <button
            onClick={() => handleAction(true)}
            disabled={isSubmitting}
            className="px-4 py-1.5 rounded-xl bg-gradient-to-r from-amber-600 to-amber-500 hover:from-amber-500 hover:to-amber-400 text-white text-xs font-semibold shadow-lg shadow-amber-600/30 transition-all disabled:opacity-50 flex items-center gap-1.5"
          >
            <CheckCircle className="w-3.5 h-3.5" />
            <span>Authorize & Execute</span>
          </button>
        </div>
      )}
    </div>
  );
};
