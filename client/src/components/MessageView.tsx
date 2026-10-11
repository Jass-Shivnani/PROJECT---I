import React, { useState } from 'react';
import { Copy, Check } from 'lucide-react';
import { Message } from '../types';
import { ToolExpander } from './ToolExpander';

interface MessageViewProps {
  message: Message;
}

export const MessageView: React.FC<MessageViewProps> = ({ message }) => {
  const isUser = message.role === 'user';
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  const handleCopy = (code: string, idx: number) => {
    navigator.clipboard.writeText(code);
    setCopiedIndex(idx);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const formatContent = (content: string) => {
    if (!content) return null;

    // Split code blocks
    const parts = content.split(/(```[\s\S]*?```)/g);

    return parts.map((part, index) => {
      if (part.startsWith('```') && part.endsWith('```')) {
        const lines = part.slice(3, -3).trim().split('\n');
        const lang = lines[0].match(/^[a-zA-Z0-9_-]+$/) ? lines[0] : '';
        const code = lang ? lines.slice(1).join('\n') : lines.join('\n');

        return (
          <div key={index} className="my-3 rounded-lg overflow-hidden border border-[#2b2d36] bg-[#0c0d11]">
            <div className="px-3 py-1.5 bg-[#17181f] border-b border-[#2b2d36] flex items-center justify-between text-[11px] font-mono text-[#8b90a0]">
              <span>{lang || 'code'}</span>
              <button
                onClick={() => handleCopy(code, index)}
                className="flex items-center gap-1 hover:text-white transition-colors"
              >
                {copiedIndex === index ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                    <span className="text-emerald-400">Copied</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5" />
                    <span>Copy</span>
                  </>
                )}
              </button>
            </div>
            <pre className="p-3 text-[12px] font-mono text-[#dcdfe7] overflow-x-auto leading-relaxed">
              <code>{code}</code>
            </pre>
          </div>
        );
      }

      // Format text lines
      const lines = part.split('\n');
      return (
        <div key={index} className="space-y-1">
          {lines.map((line, lIdx) => {
            if (line.trim().startsWith('- ') || line.trim().startsWith('* ')) {
              return (
                <li key={lIdx} className="ml-4 list-disc text-[#d2d5df] my-0.5">
                  {formatInline(line.trim().substring(2))}
                </li>
              );
            }
            if (line.trim().startsWith('### ')) {
              return (
                <h4 key={lIdx} className="text-sm font-semibold text-white mt-3 mb-1">
                  {formatInline(line.trim().substring(4))}
                </h4>
              );
            }
            if (line.trim().startsWith('## ')) {
              return (
                <h3 key={lIdx} className="text-base font-semibold text-white mt-4 mb-1">
                  {formatInline(line.trim().substring(3))}
                </h3>
              );
            }
            return (
              <p key={lIdx} className="min-h-[1.2em] leading-relaxed text-[#dcdfe7]">
                {formatInline(line)}
              </p>
            );
          })}
        </div>
      );
    });
  };

  const formatInline = (text: string) => {
    const tokens = text.split(/(`[^`]+`|\*\*[^*]+\*\*)/g);
    return tokens.map((tok, tIdx) => {
      if (tok.startsWith('`') && tok.endsWith('`')) {
        return (
          <code key={tIdx} className="px-1.5 py-0.5 mx-0.5 rounded bg-[#1f2029] text-[#e0a8ff] font-mono text-[11px] border border-[#2e303d]">
            {tok.slice(1, -1)}
          </code>
        );
      }
      if (tok.startsWith('**') && tok.endsWith('**')) {
        return <strong key={tIdx} className="text-white font-semibold">{tok.slice(2, -2)}</strong>;
      }
      return tok;
    });
  };

  return (
    <div className={`py-4 px-2 w-full flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
      <div className={`max-w-3xl w-full flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
        {/* Role Header */}
        <span className="text-[11px] font-medium text-[#717584] mb-1.5 px-1 uppercase tracking-wider">
          {isUser ? 'You' : 'Dione'}
        </span>

        {/* Message Bubble / Body */}
        <div
          className={`text-[13px] leading-relaxed select-text ${
            isUser
              ? 'p-3.5 rounded-2xl bg-[#21232d] border border-[#2f3240] text-[#f1f2f6] max-w-xl'
              : 'w-full text-[#dcdfe7]'
          }`}
        >
          {message.content ? (
            <>
              {formatContent(message.content)}
              {message.isStreaming && (
                <span className="inline-block w-1.5 h-3.5 ml-1 bg-indigo-400 animate-pulse align-middle" />
              )}
            </>
          ) : (
            <span className="flex items-center gap-2 text-indigo-400 text-xs font-mono py-1 animate-pulse">
              <span className="w-2 h-2 rounded-full bg-indigo-400 animate-ping"></span>
              <span>Reasoning via Microsoft Agent Framework...</span>
            </span>
          )}
        </div>

        {/* Discrete Tool Execution Expander */}
        {message.toolCalls && message.toolCalls.length > 0 && (
          <div className="w-full mt-2 flex flex-col gap-1">
            {message.toolCalls.map((tc) => (
              <ToolExpander key={tc.id} toolCall={tc} />
            ))}
          </div>
        )}

        {/* Timestamp */}
        <span className="text-[10px] text-[#555865] font-mono mt-1 px-1">
          {message.timestamp}
        </span>
      </div>
    </div>
  );
};
