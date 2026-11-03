import React, { useState, useEffect } from 'react';
import {
  X,
  Cpu,
  ShieldCheck,
  Mic,
  Database,
  Trash2,
  Download,
  Check,
  Sparkles,
  Link2,
  RefreshCw,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';
import {
  fetchIntegrations,
  connectUnifiedGoogle,
  connectIntegration,
  disconnectIntegration,
  syncIntegration,
  fetchWhatsAppQr
} from '../services/api';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  activeModel: string;
  onSelectModel: (model: string) => void;
  isTurboMode: boolean;
  onToggleTurbo: () => void;
  onClearAllThreads: () => void;
  threadCount: number;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  activeModel,
  onSelectModel,
  isTurboMode,
  onToggleTurbo,
  onClearAllThreads,
  threadCount,
}) => {
  const [activeTab, setActiveTab] = useState<'models' | 'integrations' | 'safety' | 'voice' | 'storage'>('models');
  const [integrationsData, setIntegrationsData] = useState<any>({ total: 8, connected: 0, integrations: [] });
  const [statusMessage, setStatusMessage] = useState<string>('');
  const [busyService, setBusyService] = useState<string>('');

  // Unified Google OAuth2 / App Password form states
  const [googleClientSecretPath, setGoogleClientSecretPath] = useState('data/credentials/client_secret.json');
  const [googleAccessToken, setGoogleAccessToken] = useState('');
  const [gmailEmail, setGmailEmail] = useState('');
  const [gmailAppPassword, setGmailAppPassword] = useState('');

  // Messaging & Social tokens
  const [telegramToken, setTelegramToken] = useState('');
  const [telegramChatId, setTelegramChatId] = useState('');
  const [slackToken, setSlackToken] = useState('');
  const [slackWebhook, setSlackWebhook] = useState('');
  const [instagramToken, setInstagramToken] = useState('');
  const [whatsappQr, setWhatsappQr] = useState<string | null>(null);

  const refreshIntegrations = async () => {
    const data = await fetchIntegrations();
    setIntegrationsData(data);
  };

  useEffect(() => {
    if (isOpen && activeTab === 'integrations') {
      refreshIntegrations();
    }
  }, [isOpen, activeTab]);

  if (!isOpen) return null;

  const MODELS = [
    {
      id: 'gemini-3.5-flash-lite',
      name: 'Gemini 3.5 Flash-Lite (Primary Free Tier)',
      desc: 'Highest Google AI Studio Free Tier quota (15 RPM / 500 RPD), ultra-low latency (~200ms) for tool & OS loops',
      recommended: true,
    },
    {
      id: 'gemini-3.1-flash-lite',
      name: 'Gemini 3.1 Flash-Lite (High-Quota Failover)',
      desc: 'Generous Free Tier allowance (15 RPM / 500 RPD), automatic failover sibling when 3.5 hits RPM limits',
      recommended: false,
    },
    {
      id: 'gemini-2.5-flash-lite',
      name: 'Gemini 2.5 Flash-Lite (High-Volume Free Tier)',
      desc: '10M batch token capacity and stable free-tier multimodal execution',
      recommended: false,
    },
    {
      id: 'gemini-3.8-flash',
      name: 'Gemini 3.8 Flash (Latest Flagship Flash)',
      desc: 'High-precision reasoning & multi-service synthesis (Free Tier: 5 RPM / 20 RPD; higher on AI Pro Trial)',
      recommended: false,
    },
    {
      id: 'gemini-2.5-flash',
      name: 'Gemini 2.5 Flash (Balanced Multimodal)',
      desc: 'Strong multimodal vision grounding and fast function calling',
      recommended: false,
    },
    {
      id: 'gemini-2.5-pro',
      name: 'Gemini 2.5 Pro (AI Pro Trial Deep Reasoning)',
      desc: 'Deep task decomposition, complex coding, and architectural analysis on AI Studio Pro trial',
      recommended: false,
    },
    {
      id: 'ollama:llama3',
      name: 'Local Ollama (Llama 3)',
      desc: '100% offline local inference via http://127.0.0.1:11434',
      recommended: false,
    },
  ];

  const handleUnifiedGoogleConnect = async () => {
    setBusyService('google_unified');
    setStatusMessage('Initiating Unified Google OAuth2 across Gmail, Calendar, Drive & Photos...');
    const res = await connectUnifiedGoogle({
      client_secret_path: googleClientSecretPath,
      access_token: googleAccessToken || undefined,
    });
    if (res.success) {
      setStatusMessage(`Connected Google Workspace SSO (${(res.connected_services || []).join(', ')})`);
    } else {
      setStatusMessage(res.error || 'Unified Google OAuth2 failed.');
    }
    await refreshIntegrations();
    setBusyService('');
  };

  const handleServiceConnect = async (id: string, params: Record<string, any>) => {
    setBusyService(id);
    setStatusMessage(`Connecting ${id}...`);
    const res = await connectIntegration(id, params);
    if (res.success) {
      setStatusMessage(`Connected ${id} (${res.status})`);
      if (id === 'whatsapp') {
        const qrRes = await fetchWhatsAppQr();
        if (qrRes?.data?.qr_data_url) {
          setWhatsappQr(qrRes.data.qr_data_url);
        }
      }
    } else {
      setStatusMessage(res.error || `Failed to connect ${id}`);
    }
    await refreshIntegrations();
    setBusyService('');
  };

  const handleServiceDisconnect = async (id: string) => {
    setBusyService(id);
    await disconnectIntegration(id);
    setStatusMessage(`Disconnected ${id}`);
    await refreshIntegrations();
    setBusyService('');
  };

  const handleServiceSync = async (id: string) => {
    setBusyService(id);
    const res = await syncIntegration(id);
    if (res.success) {
      setStatusMessage(`Synced ${id}: ${JSON.stringify(res.result).slice(0, 90)}`);
    } else {
      setStatusMessage(res.error || `Sync failed for ${id}`);
    }
    await refreshIntegrations();
    setBusyService('');
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-md font-sans select-text p-4">
      <div className="w-full max-w-3xl bg-[#0c0d16] border border-white/[0.1] rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[88vh]">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-white/[0.08] flex items-center justify-between bg-black/20">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-violet-600/20 border border-violet-500/30 flex items-center justify-center text-violet-300">
              <Cpu className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-white tracking-wide">
                Dione Sovereign AI Settings
              </h2>
              <p className="text-[11px] text-slate-400 font-mono">
                AI Studio Free-Tier Failover, Unified Google OAuth2, 8 Service Integrations & Safety Lattice
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/[0.06] transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 flex overflow-hidden">
          {/* Settings Tabs Sidebar */}
          <div className="w-52 border-r border-white/[0.06] bg-black/10 p-3 space-y-1">
            <button
              onClick={() => setActiveTab('models')}
              className={`w-full px-3 py-2 rounded-xl text-xs font-medium flex items-center gap-2 transition-all ${
                activeTab === 'models' ? 'bg-violet-600/20 text-white font-semibold border border-violet-500/30' : 'text-slate-400 hover:text-white hover:bg-white/[0.04]'
              }`}
            >
              <Cpu className="w-3.5 h-3.5" />
              <span>Models & Failover</span>
            </button>
            <button
              onClick={() => setActiveTab('integrations')}
              className={`w-full px-3 py-2 rounded-xl text-xs font-medium flex items-center gap-2 transition-all ${
                activeTab === 'integrations' ? 'bg-violet-600/20 text-white font-semibold border border-violet-500/30' : 'text-slate-400 hover:text-white hover:bg-white/[0.04]'
              }`}
            >
              <Link2 className="w-3.5 h-3.5" />
              <span>Integrations (8)</span>
            </button>
            <button
              onClick={() => setActiveTab('safety')}
              className={`w-full px-3 py-2 rounded-xl text-xs font-medium flex items-center gap-2 transition-all ${
                activeTab === 'safety' ? 'bg-violet-600/20 text-white font-semibold border border-violet-500/30' : 'text-slate-400 hover:text-white hover:bg-white/[0.04]'
              }`}
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Intent Safety Lattice</span>
            </button>
            <button
              onClick={() => setActiveTab('voice')}
              className={`w-full px-3 py-2 rounded-xl text-xs font-medium flex items-center gap-2 transition-all ${
                activeTab === 'voice' ? 'bg-violet-600/20 text-white font-semibold border border-violet-500/30' : 'text-slate-400 hover:text-white hover:bg-white/[0.04]'
              }`}
            >
              <Mic className="w-3.5 h-3.5" />
              <span>Neural Voice (Aoede)</span>
            </button>
            <button
              onClick={() => setActiveTab('storage')}
              className={`w-full px-3 py-2 rounded-xl text-xs font-medium flex items-center gap-2 transition-all ${
                activeTab === 'storage' ? 'bg-violet-600/20 text-white font-semibold border border-violet-500/30' : 'text-slate-400 hover:text-white hover:bg-white/[0.04]'
              }`}
            >
              <Database className="w-3.5 h-3.5" />
              <span>Memory & Storage</span>
            </button>
          </div>

          {/* Settings Content Area */}
          <div className="flex-1 p-6 overflow-y-auto space-y-5">
            {activeTab === 'models' && (
              <div className="space-y-4">
                <div>
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                    Google AI Studio Free-Tier & AI Pro Trial Models
                  </h3>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    Automatic 429 rate-limit failover rotates across Flash-Lite (500 RPD) and Flash/Pro models without dropping your session.
                  </p>
                </div>

                <div className="space-y-2">
                  {MODELS.map((m) => (
                    <button
                      key={m.id}
                      onClick={() => onSelectModel(m.id)}
                      className={`w-full p-3 rounded-xl border text-left transition-all flex items-start justify-between gap-3 ${
                        activeModel === m.id
                          ? 'bg-violet-600/15 border-violet-500/40 text-white'
                          : 'bg-white/[0.02] border-white/[0.06] text-slate-300 hover:bg-white/[0.04]'
                      }`}
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold">{m.name}</span>
                          {m.recommended && (
                            <span className="px-2 py-0.5 rounded-full bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 text-[10px] font-mono">
                              Best Free Quota
                            </span>
                          )}
                        </div>
                        <p className="text-[11px] text-slate-400 leading-relaxed">{m.desc}</p>
                      </div>
                      {activeModel === m.id && (
                        <Check className="w-4 h-4 text-violet-400 flex-shrink-0 mt-1" />
                      )}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {activeTab === 'integrations' && (
              <div className="space-y-5">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                      Connected Services & Unified Google OAuth2 ({integrationsData.connected || 0}/{integrationsData.total || 8} Active)
                    </h3>
                    <p className="text-[11px] text-slate-400 mt-0.5">
                      Authenticate once with Google OAuth2 to unlock Gmail, Calendar, Drive, and Photos together.
                    </p>
                  </div>
                  <button
                    onClick={refreshIntegrations}
                    className="p-2 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.08] text-slate-300"
                    title="Refresh Status"
                  >
                    <RefreshCw className="w-3.5 h-3.5" />
                  </button>
                </div>

                {statusMessage && (
                  <div className="p-3 rounded-xl bg-violet-500/10 border border-violet-500/30 text-violet-200 text-xs flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-violet-400 flex-shrink-0" />
                    <span className="font-mono text-[11px]">{statusMessage}</span>
                  </div>
                )}

                {/* 1. Unified Google OAuth2 SSO Card */}
                <div className="p-4 rounded-xl bg-gradient-to-br from-blue-500/10 via-violet-500/5 to-transparent border border-blue-500/30 space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="text-xs font-bold text-white flex items-center gap-2">
                        <span>One-Click Unified Google Workspace OAuth2</span>
                        <span className="px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-300 text-[10px] font-mono">
                          Gmail + Calendar + Drive + Photos
                        </span>
                      </h4>
                      <p className="text-[11px] text-slate-400 mt-0.5">
                        Sign in via browser using client_secret.json or paste an OAuth2 access token to connect all 4 Google services at once.
                      </p>
                    </div>
                    <button
                      onClick={handleUnifiedGoogleConnect}
                      disabled={busyService === 'google_unified'}
                      className="px-3.5 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-xs font-semibold transition-all"
                    >
                      {busyService === 'google_unified' ? 'Connecting...' : 'Sign In with Google'}
                    </button>
                  </div>

                  <div className="grid grid-cols-2 gap-2 pt-1">
                    <input
                      type="text"
                      value={googleClientSecretPath}
                      onChange={(e) => setGoogleClientSecretPath(e.target.value)}
                      placeholder="Path to client_secret.json"
                      className="px-3 py-1.5 rounded-lg bg-black/40 border border-white/10 text-xs text-white font-mono"
                    />
                    <input
                      type="password"
                      value={googleAccessToken}
                      onChange={(e) => setGoogleAccessToken(e.target.value)}
                      placeholder="Or paste OAuth2 Access Token (optional)"
                      className="px-3 py-1.5 rounded-lg bg-black/40 border border-white/10 text-xs text-white font-mono"
                    />
                  </div>
                </div>

                {/* 2. Quick Credentials Setup for Gmail App Password, Telegram, Slack, WhatsApp, Instagram */}
                <div className="grid grid-cols-1 gap-3">
                  {/* Gmail App Password Fallback */}
                  <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.08] space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-white">Gmail (App Password Optional Fallback)</span>
                      <button
                        onClick={() => handleServiceConnect('google_mail', { email: gmailEmail, app_password: gmailAppPassword })}
                        className="px-3 py-1 rounded-lg bg-white/10 hover:bg-white/20 text-xs text-white"
                      >
                        Save Gmail App Password
                      </button>
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <input
                        type="email"
                        value={gmailEmail}
                        onChange={(e) => setGmailEmail(e.target.value)}
                        placeholder="you@gmail.com"
                        className="px-3 py-1.5 rounded-lg bg-black/40 border border-white/10 text-xs text-white font-mono"
                      />
                      <input
                        type="password"
                        value={gmailAppPassword}
                        onChange={(e) => setGmailAppPassword(e.target.value)}
                        placeholder="16-char Gmail App Password"
                        className="px-3 py-1.5 rounded-lg bg-black/40 border border-white/10 text-xs text-white font-mono"
                      />
                    </div>
                  </div>

                  {/* Telegram & Slack */}
                  <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.08] space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-white">Telegram Bot API</span>
                      <button
                        onClick={() => handleServiceConnect('telegram', { bot_token: telegramToken, chat_id: telegramChatId })}
                        className="px-3 py-1 rounded-lg bg-white/10 hover:bg-white/20 text-xs text-white"
                      >
                        Connect Telegram
                      </button>
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <input
                        type="password"
                        value={telegramToken}
                        onChange={(e) => setTelegramToken(e.target.value)}
                        placeholder="Bot Token (123456:ABC...)"
                        className="px-3 py-1.5 rounded-lg bg-black/40 border border-white/10 text-xs text-white font-mono"
                      />
                      <input
                        type="text"
                        value={telegramChatId}
                        onChange={(e) => setTelegramChatId(e.target.value)}
                        placeholder="Default Chat ID"
                        className="px-3 py-1.5 rounded-lg bg-black/40 border border-white/10 text-xs text-white font-mono"
                      />
                    </div>
                  </div>

                  <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.08] space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-white">Slack Workspace & Instagram Graph</span>
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleServiceConnect('slack', { bot_token: slackToken, webhook_url: slackWebhook })}
                          className="px-3 py-1 rounded-lg bg-white/10 hover:bg-white/20 text-xs text-white"
                        >
                          Connect Slack
                        </button>
                        <button
                          onClick={() => handleServiceConnect('instagram', { access_token: instagramToken })}
                          className="px-3 py-1 rounded-lg bg-white/10 hover:bg-white/20 text-xs text-white"
                        >
                          Connect Instagram
                        </button>
                      </div>
                    </div>
                    <div className="grid grid-cols-3 gap-2">
                      <input
                        type="password"
                        value={slackToken}
                        onChange={(e) => setSlackToken(e.target.value)}
                        placeholder="Slack Bot Token (xoxb-...)"
                        className="px-3 py-1.5 rounded-lg bg-black/40 border border-white/10 text-xs text-white font-mono"
                      />
                      <input
                        type="text"
                        value={slackWebhook}
                        onChange={(e) => setSlackWebhook(e.target.value)}
                        placeholder="Or Slack Webhook URL"
                        className="px-3 py-1.5 rounded-lg bg-black/40 border border-white/10 text-xs text-white font-mono"
                      />
                      <input
                        type="password"
                        value={instagramToken}
                        onChange={(e) => setInstagramToken(e.target.value)}
                        placeholder="Instagram Graph Token"
                        className="px-3 py-1.5 rounded-lg bg-black/40 border border-white/10 text-xs text-white font-mono"
                      />
                    </div>
                  </div>
                </div>

                {/* 3. Live Service Status Matrix */}
                <div className="space-y-2">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                    All 8 Registered Service Integrations
                  </span>
                  <div className="grid grid-cols-2 gap-2.5">
                    {(integrationsData.integrations || []).map((svc: any) => {
                      const isConnected = svc.status === 'connected';
                      return (
                        <div
                          key={svc.id}
                          className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.07] flex items-center justify-between gap-2"
                        >
                          <div className="min-w-0">
                            <div className="flex items-center gap-1.5">
                              {isConnected ? (
                                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
                              ) : (
                                <AlertCircle className="w-3.5 h-3.5 text-slate-500 flex-shrink-0" />
                              )}
                              <span className="text-xs font-semibold text-white truncate">{svc.name}</span>
                              <span className="text-[10px] font-mono text-slate-400">({svc.tools_count} tools)</span>
                            </div>
                            <p className="text-[10px] text-slate-400 truncate mt-0.5">{svc.description}</p>
                          </div>
                          <div className="flex items-center gap-1 flex-shrink-0">
                            {svc.id === 'whatsapp' && !isConnected && (
                              <button
                                onClick={() => handleServiceConnect('whatsapp', {})}
                                className="px-2 py-1 rounded-lg bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 text-[10px] font-mono"
                              >
                                Pair QR
                              </button>
                            )}
                            {isConnected && (
                              <>
                                <button
                                  onClick={() => handleServiceSync(svc.id)}
                                  className="px-2 py-1 rounded-lg bg-white/[0.06] hover:bg-white/[0.12] text-slate-200 text-[10px] font-mono"
                                >
                                  Sync
                                </button>
                                <button
                                  onClick={() => handleServiceDisconnect(svc.id)}
                                  className="px-2 py-1 rounded-lg bg-red-500/15 hover:bg-red-500/25 text-red-300 text-[10px] font-mono"
                                >
                                  Disconnect
                                </button>
                              </>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {whatsappQr && (
                    <div className="p-4 rounded-xl bg-black/40 border border-emerald-500/30 text-center space-y-2">
                      <p className="text-xs text-emerald-300 font-semibold">Scan with WhatsApp on your phone to link Dione:</p>
                      <img src={whatsappQr} alt="WhatsApp QR" className="w-44 h-44 mx-auto rounded-lg bg-white p-2" />
                    </div>
                  )}
                </div>
              </div>
            )}

            {activeTab === 'safety' && (
              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 rounded-xl bg-white/[0.03] border border-white/[0.08]">
                  <div>
                    <h4 className="text-xs font-bold text-white">Turbo Autonomous Mode (Auto-Approve Tier 4)</h4>
                    <p className="text-[11px] text-slate-400 mt-0.5">
                      By default, Dione auto-executes all read/search actions, desktop automation, and user-requested messages (Tier 0-3), while pausing for 1-click confirmation on file deletions or unprompted sends (Tier 4).
                    </p>
                  </div>
                  <button
                    onClick={onToggleTurbo}
                    className={`px-3 py-1.5 rounded-xl text-xs font-bold border transition-all ${
                      isTurboMode
                        ? 'bg-amber-500/20 border-amber-500/40 text-amber-300'
                        : 'bg-white/[0.05] border-white/[0.1] text-slate-400'
                    }`}
                  >
                    {isTurboMode ? 'Turbo ON' : 'Standard Intent Gate'}
                  </button>
                </div>
              </div>
            )}

            {activeTab === 'voice' && (
              <div className="space-y-3 text-xs text-slate-300">
                <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.08] space-y-1">
                  <div className="font-bold text-white">Gemini Live Native Audio Frontman (Aoede 24kHz)</div>
                  <p className="text-[11px] text-slate-400">
                    Full-duplex low-latency voice conversation with background task handoff to DioneEngine.
                  </p>
                </div>
              </div>
            )}

            {activeTab === 'storage' && (
              <div className="space-y-4">
                <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] space-y-2.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-300">Active Saved Threads</span>
                    <span className="font-mono text-white">{threadCount}</span>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-300">Disk Persistence Path</span>
                    <span className="font-mono text-[10px] text-slate-400">./data/memory/threads.json</span>
                  </div>
                </div>

                <div className="pt-2 flex items-center gap-3">
                  <button
                    onClick={() => {
                      const data = localStorage.getItem('dione_threads_store_v1');
                      if (data) {
                        const blob = new Blob([data], { type: 'application/json' });
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = `dione_chat_history_${Date.now()}.json`;
                        a.click();
                      }
                    }}
                    className="px-3 py-2 rounded-xl bg-white/[0.06] hover:bg-white/[0.1] border border-white/[0.08] text-white text-xs font-medium flex items-center gap-2 transition-all"
                  >
                    <Download className="w-3.5 h-3.5 text-violet-400" />
                    <span>Export History (JSON)</span>
                  </button>

                  <button
                    onClick={onClearAllThreads}
                    className="px-3 py-2 rounded-xl bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 text-red-300 text-xs font-medium flex items-center gap-2 transition-all"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    <span>Reset All Threads</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Modal Footer */}
        <div className="p-3 px-6 border-t border-white/[0.08] bg-black/30 flex items-center justify-between text-[11px] font-mono text-slate-400">
          <span>Dione AI Sovereign Station &bull; Port 8900</span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-xl bg-violet-600 hover:bg-violet-500 text-white text-xs font-semibold shadow-md shadow-violet-600/30 transition-all"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
};
