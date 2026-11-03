import React, { useState } from 'react';
import {
  X,
  Copy,
  Check,
  Download,
  Code2,
  Eye,
  FileText,
  Sparkles
} from 'lucide-react';

export interface ArtifactItem {
  id: string;
  title: string;
  language: string;
  content: string;
  type?: 'code' | 'markdown' | 'html';
}

interface ArtifactDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  artifact: ArtifactItem | null;
}

export const ArtifactDrawer: React.FC<ArtifactDrawerProps> = ({
  isOpen,
  onClose,
  artifact,
}) => {
  const [activeTab, setActiveTab] = useState<'code' | 'preview'>('code');
  const [isCopied, setIsCopied] = useState(false);

  if (!isOpen || !artifact) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(artifact.content);
    setIsCopied(true);
    setTimeout(() => setIsCopied(false), 2000);
  };

  const handleDownload = () => {
    const ext = artifact.language ? `.${artifact.language}` : '.txt';
    const filename = artifact.title.includes('.') ? artifact.title : `${artifact.title}${ext}`;
    const blob = new Blob([artifact.content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const isPreviewable = artifact.language === 'markdown' || artifact.language === 'md' || artifact.language === 'html';

  return (
    <aside className="w-[460px] border-l border-white/[0.08] bg-[#090b12] flex flex-col h-full flex-shrink-0 z-20 font-sans select-text shadow-2xl">
      {/* Header */}
      <div className="p-3.5 border-b border-white/[0.08] flex items-center justify-between bg-black/20">
        <div className="flex items-center gap-2 min-w-0">
          <div className="w-7 h-7 rounded-lg bg-violet-600/20 border border-violet-500/30 flex items-center justify-center text-violet-300 flex-shrink-0">
            <Code2 className="w-4 h-4" />
          </div>
          <div className="min-w-0">
            <div className="font-semibold text-xs text-white truncate">
              {artifact.title}
            </div>
            <div className="text-[10px] font-mono text-slate-400 uppercase">
              {artifact.language || 'Plain Text'} Artifact
            </div>
          </div>
        </div>

        {/* Tab & Close Controls */}
        <div className="flex items-center gap-1.5 flex-shrink-0">
          {isPreviewable && (
            <div className="flex items-center bg-white/[0.04] p-0.5 rounded-lg border border-white/[0.06] text-xs">
              <button
                onClick={() => setActiveTab('code')}
                className={`px-2 py-1 rounded-md transition-all ${
                  activeTab === 'code' ? 'bg-violet-600/30 text-white font-medium' : 'text-slate-400 hover:text-white'
                }`}
              >
                Code
              </button>
              <button
                onClick={() => setActiveTab('preview')}
                className={`px-2 py-1 rounded-md transition-all ${
                  activeTab === 'preview' ? 'bg-violet-600/30 text-white font-medium' : 'text-slate-400 hover:text-white'
                }`}
              >
                Preview
              </button>
            </div>
          )}

          <button
            onClick={handleCopy}
            className="p-1.5 rounded-lg hover:bg-white/[0.06] text-slate-400 hover:text-white transition-colors"
            title="Copy code"
          >
            {isCopied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
          </button>

          <button
            onClick={handleDownload}
            className="p-1.5 rounded-lg hover:bg-white/[0.06] text-slate-400 hover:text-white transition-colors"
            title="Download file"
          >
            <Download className="w-4 h-4" />
          </button>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-white/[0.06] text-slate-400 hover:text-white transition-colors"
            title="Close artifact drawer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === 'code' ? (
          <pre className="text-xs font-mono text-slate-200 bg-[#0d0f18] p-4 rounded-xl border border-white/[0.06] overflow-x-auto leading-relaxed">
            <code>{artifact.content}</code>
          </pre>
        ) : (
          <div className="prose prose-invert prose-sm max-w-none bg-[#0d0f18] p-4 rounded-xl border border-white/[0.06] text-slate-200">
            {artifact.language === 'html' ? (
              <iframe
                title="HTML Preview"
                srcDoc={artifact.content}
                className="w-full h-[600px] border-0 rounded-lg bg-white"
                sandbox="allow-scripts"
              />
            ) : (
              <div className="whitespace-pre-wrap font-sans leading-relaxed text-xs">
                {artifact.content}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer Info */}
      <div className="p-2.5 border-t border-white/[0.06] bg-black/20 flex items-center justify-between text-[11px] font-mono text-slate-400">
        <span>{artifact.content.split('\n').length} lines</span>
        <span>{(new TextEncoder().encode(artifact.content).length / 1024).toFixed(1)} KB</span>
      </div>
    </aside>
  );
};
