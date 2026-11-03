import React from 'react';
import { Mic, MicOff, Volume2, Sparkles } from 'lucide-react';

interface NeuralIrisProps {
  isConnected: boolean;
  isListening: boolean;
  isSpeaking: boolean;
  volume: number; // 0.0 to 1.0
  statusText: string;
  onToggle: () => void;
  size?: 'sm' | 'md' | 'lg';
}

export const NeuralIris: React.FC<NeuralIrisProps> = ({
  isConnected,
  isListening,
  isSpeaking,
  volume,
  statusText,
  onToggle,
  size = 'md',
}) => {
  // Scale pulse based on live audio RMS volume
  const scale = isConnected ? 1.0 + Math.min(volume * 0.45, 0.5) : 1.0;
  const glowIntensity = isConnected ? Math.max(0.3, volume * 1.5) : 0.15;

  const sizeClasses = {
    sm: 'w-8 h-8',
    md: 'w-12 h-12',
    lg: 'w-20 h-20',
  }[size];

  return (
    <div className="flex items-center gap-3 select-none">
      <button
        type="button"
        onClick={onToggle}
        className="relative group focus:outline-none"
        title={isConnected ? "Disconnect Neural Voice" : "Connect Full-Duplex Neural Voice (Gemini Live)"}
      >
        {/* Outermost Atmospheric Halo */}
        <div
          className="absolute inset-0 rounded-full transition-all duration-75 blur-xl pointer-events-none"
          style={{
            transform: `scale(${scale * 1.4})`,
            backgroundColor: isSpeaking
              ? `rgba(236, 72, 153, ${glowIntensity * 0.7})`
              : isListening
              ? `rgba(16, 185, 129, ${glowIntensity * 0.7})`
              : isConnected
              ? 'rgba(139, 92, 246, 0.25)'
              : 'rgba(255, 255, 255, 0.04)',
          }}
        />

        {/* Middle Liquid Glass Ring */}
        <div
          className="absolute inset-0 rounded-full transition-all duration-100 blur-md pointer-events-none"
          style={{
            transform: `scale(${scale * 1.15})`,
            backgroundColor: isSpeaking
              ? `rgba(168, 85, 247, ${glowIntensity})`
              : isListening
              ? `rgba(52, 211, 153, ${glowIntensity})`
              : isConnected
              ? 'rgba(99, 102, 241, 0.4)'
              : 'rgba(255, 255, 255, 0.08)',
          }}
        />

        {/* Central VisionOS Iris Sphere */}
        <div
          className={`${sizeClasses} relative rounded-full border border-white/20 backdrop-blur-2xl flex items-center justify-center transition-transform duration-75 shadow-2xl overflow-hidden`}
          style={{
            transform: `scale(${scale})`,
            background: isSpeaking
              ? 'radial-gradient(circle at 35% 35%, rgba(244, 114, 182, 0.95), rgba(168, 85, 247, 0.9), rgba(15, 23, 42, 0.95))'
              : isListening
              ? 'radial-gradient(circle at 35% 35%, rgba(110, 231, 183, 0.95), rgba(16, 185, 129, 0.9), rgba(15, 23, 42, 0.95))'
              : isConnected
              ? 'radial-gradient(circle at 35% 35%, rgba(167, 139, 250, 0.8), rgba(99, 102, 241, 0.75), rgba(15, 23, 42, 0.9))'
              : 'radial-gradient(circle at 35% 35%, rgba(255, 255, 255, 0.12), rgba(255, 255, 255, 0.05), rgba(10, 11, 18, 0.9))',
          }}
        >
          {/* Internal Specular Glass Sheen */}
          <div className="absolute inset-0 bg-gradient-to-tr from-transparent via-white/10 to-white/30 pointer-events-none rounded-full" />

          {/* Center Dynamic Icon */}
          <div className="relative text-white z-10">
            {isSpeaking ? (
              <Volume2 className="w-5 h-5 animate-pulse drop-shadow" />
            ) : isListening ? (
              <Mic className="w-5 h-5 animate-bounce drop-shadow" />
            ) : isConnected ? (
              <Sparkles className="w-5 h-5 animate-spin drop-shadow" style={{ animationDuration: '6s' }} />
            ) : (
              <MicOff className="w-4 h-4 text-slate-400 group-hover:text-white transition-colors" />
            )}
          </div>
        </div>
      </button>

      {/* Live Voice Status Capsule */}
      <div className="hidden sm:flex flex-col">
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-semibold text-white tracking-wide">
            {isConnected ? (isSpeaking ? 'DIONE SPEAKING' : isListening ? 'LISTENING' : 'VOICE CONNECTED') : 'NEURAL VOICE'}
          </span>
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              isConnected
                ? isSpeaking
                  ? 'bg-pink-400 animate-ping'
                  : isListening
                  ? 'bg-emerald-400 animate-ping'
                  : 'bg-violet-400'
                : 'bg-slate-600'
            }`}
          />
        </div>
        <div className="text-[10px] text-slate-400 font-mono truncate max-w-[200px]">
          {statusText}
        </div>
      </div>
    </div>
  );
};
