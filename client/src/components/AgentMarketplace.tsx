import React from 'react';
import {
  Sparkles,
  Bot,
  Monitor,
  Network,
  Cpu,
  BookOpen,
  FolderGit2,
  Terminal,
  ShieldAlert,
  ArrowRight,
  CheckCircle2,
  Zap,
  Play
} from 'lucide-react';

export interface AgentSpecialist {
  id: string;
  name: string;
  role: string;
  badge: string;
  tagline: string;
  description: string;
  systemPromptModifier: string;
  safetyTier: string;
  gradient: string;
  borderHover: string;
  icon: React.ReactNode;
  tools: string[];
  suggestedPrompts: string[];
}

export const SPECIALIST_AGENTS: AgentSpecialist[] = [
  {
    id: 'executive-orchestrator',
    name: 'Executive Meta-Planner',
    role: 'Supervisor & Task Decomposer',
    badge: 'ORCH',
    tagline: 'Multi-Agent Supervisor & Autonomous ReAct Engine',
    description: 'Decomposes complex requests into directed acyclic graphs (DAGs), delegates to specialized kernels, and acts as your proactive executive assistant.',
    systemPromptModifier: 'You are the Executive Meta-Planner. You prioritize high-level task decomposition, delegation to sub-specialists, and disciplined execution.',
    safetyTier: 'Tier 4: Supervised Execution',
    gradient: 'from-violet-600 to-indigo-600',
    borderHover: 'hover:border-violet-500/50',
    icon: <Sparkles className="w-5 h-5 text-violet-300" />,
    tools: ['meta_planner', 'handoff_agent', 'dag_orchestrator', 'action_approval'],
    suggestedPrompts: [
      'Decompose my engineering project into a multi-phase implementation roadmap',
      'Conduct a safety audit of active background processes and file privileges',
      'Synthesize today’s workstation activity and schedule automated follow-ups'
    ]
  },
  {
    id: 'computer-use-specialist',
    name: 'Computer-Use Visionary',
    role: 'Windows 11 OS Operator',
    badge: 'CU-OS',
    tagline: 'High-Precision 0-100% Percentage Grid & Win32 Controls',
    description: 'Captures screen frames via 64-bit GDI BitBlt, inspects UI elements via Windows UIA, clicks percentages, types, and automates desktop applications.',
    systemPromptModifier: 'You are the Windows 11 Computer-Use Specialist. You never guess window positions; you always inspect the screen and use coordinates or percentage clicks.',
    safetyTier: 'Tier 5: Autonomous Win32 OS',
    gradient: 'from-cyan-600 to-blue-600',
    borderHover: 'hover:border-cyan-500/50',
    icon: <Monitor className="w-5 h-5 text-cyan-300" />,
    tools: ['launch_app', 'vision_inspect_screen', 'mouse_click_percentage', 'type_text', 'launch_and_play_game'],
    suggestedPrompts: [
      'Take a screenshot of the active desktop and identify all open application windows',
      'Launch Google Chrome and navigate to the project dashboard',
      'Launch Valorant or my active game in high-priority fullscreen mode'
    ]
  },
  {
    id: 'deep-research-specialist',
    name: 'Deep Web & arXiv Scout',
    role: 'Academic & Literature Researcher',
    badge: 'WEB-AI',
    tagline: 'Real-Time DuckDuckGo & Academic Paper Synthesis',
    description: 'Queries arXiv and live search engines without mocks, extracts abstract concepts, cross-references citations, and compiles research briefings.',
    systemPromptModifier: 'You are the Deep Research Specialist. You synthesize rigorous scientific findings, reference paper citations, and provide structured analyses.',
    safetyTier: 'Tier 1: Read-Only Web',
    gradient: 'from-pink-600 to-rose-600',
    borderHover: 'hover:border-pink-500/50',
    icon: <BookOpen className="w-5 h-5 text-pink-300" />,
    tools: ['search_web', 'arxiv_query', 'extract_paper_summary', 'cross_reference_citations'],
    suggestedPrompts: [
      'Search recent arXiv papers on multi-agent safety poset lattices and hierarchical ReAct',
      'Find the latest benchmarks for multimodal computer-use agents on Windows',
      'Synthesize current literature on memory retention and episodic subgraphs in LLMs'
    ]
  },
  {
    id: 'code-architect',
    name: 'Filesystem & Code Architect',
    role: 'Local Repository & Code Engineer',
    badge: 'SYS-CODE',
    tagline: 'AST Inspection, Refactoring & Production Scripts',
    description: 'Navigates local directory hierarchies, inspects Python/TypeScript codebases, writes verified scripts, and audits codebase integrity.',
    systemPromptModifier: 'You are the Filesystem & Code Architect. You inspect code structure, follow zero-mock rules, and build production-grade modules.',
    safetyTier: 'Tier 3: Local Workspace Read/Write',
    gradient: 'from-amber-600 to-orange-600',
    borderHover: 'hover:border-amber-500/50',
    icon: <FolderGit2 className="w-5 h-5 text-amber-300" />,
    tools: ['read_file', 'write_file', 'edit_file', 'run_command', 'list_directory'],
    suggestedPrompts: [
      'Inspect the server directory and list all registered FastAPI endpoint routes',
      'Audit client components for styling consistency and accessible keyboard controls',
      'Run TypeScript compilation and verify production Vite build bundle sizes'
    ]
  },
  {
    id: 'system-admin',
    name: 'System & Hardware Admin',
    role: 'Telemetry & Audio Endpoint Controller',
    badge: 'SYS-ADMIN',
    tagline: 'psutil Process Telemetry & NirCmd Audio Routing',
    description: 'Monitors workstation CPU, RAM, and GPU memory, adjusts master volume, switches default audio playback/recording devices, and listens for global hotkeys.',
    systemPromptModifier: 'You are the System & Hardware Admin. You control low-level OS utilities, NirCmd device switching, and workstation telemetry.',
    safetyTier: 'Tier 3: OS Controls',
    gradient: 'from-emerald-600 to-teal-600',
    borderHover: 'hover:border-emerald-500/50',
    icon: <Cpu className="w-5 h-5 text-emerald-300" />,
    tools: ['system_telemetry', 'switch_audio_device', 'adjust_volume', 'media_control', 'manage_tasks'],
    suggestedPrompts: [
      'Inspect current CPU, RAM, and background Python processes',
      'List all connected audio output endpoints and switch to primary headphones',
      'Check system volume level and set to optimal 65%'
    ]
  },
  {
    id: 'dream-gardener',
    name: 'Dream & Scout Gardener',
    role: 'Autonomous Inactivity Learner',
    badge: 'DREAM',
    tagline: 'Background Memory Consolidator & Morning Briefing Engine',
    description: 'Activates during workstation idle periods, scouts arXiv, prunes stale memory nodes, and drafts proactive briefings for your return.',
    systemPromptModifier: 'You are the Dream & Scout Gardener. You operate on background memory, find serendipitous research connections, and prepare briefings.',
    safetyTier: 'Tier 2: Background Memory & Graph',
    gradient: 'from-purple-600 to-fuchsia-600',
    borderHover: 'hover:border-purple-500/50',
    icon: <Terminal className="w-5 h-5 text-purple-300" />,
    tools: ['trigger_dream_cycle', 'harvest_arxiv_papers', 'consolidate_subgraphs', 'stage_commitments'],
    suggestedPrompts: [
      'Trigger an immediate Dream cycle to scout arXiv and update knowledge memory',
      'View staged executive drafts and while-you-were-away commitments',
      'Review memory graph connectivity and prune redundant episodic nodes'
    ]
  }
];

interface AgentMarketplaceProps {
  onSelectSpecialist: (specialist: AgentSpecialist, prompt?: string) => void;
}

export const AgentMarketplace: React.FC<AgentMarketplaceProps> = ({ onSelectSpecialist }) => {
  return (
    <div className="flex-1 h-full overflow-y-auto px-6 py-8 bg-[#090a12] text-slate-200 font-sans select-text">
      <div className="max-w-5xl mx-auto space-y-8">
        {/* Header Banner */}
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-1 rounded-full bg-violet-600/20 border border-violet-500/30 text-violet-300 text-xs font-mono font-semibold flex items-center gap-1.5">
              <Bot className="w-3.5 h-3.5" />
              <span>Sovereign Fleet</span>
            </span>
            <span className="text-xs text-slate-400 font-mono">6 Air-Gapped Specialist Kernels</span>
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">
            Dione Agent Fleet & Specialist Marketplace
          </h1>
          <p className="text-sm text-slate-300 max-w-2xl leading-relaxed">
            Select a specialized kernel for focused problem-solving, or engage the full swarm via the Executive Meta-Planner. Each specialist operates with real Win32, psutil, SQLite, and Gemini tool execution.
          </p>
        </div>

        {/* Grid of 6 Specialists */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {SPECIALIST_AGENTS.map((spec) => (
            <div
              key={spec.id}
              className={`p-5 rounded-2xl bg-white/[0.03] border border-white/[0.08] transition-all flex flex-col justify-between group ${spec.borderHover} hover:bg-white/[0.05] hover:shadow-xl`}
            >
              <div className="space-y-3.5">
                {/* Agent Icon + Badge */}
                <div className="flex items-start justify-between">
                  <div className={`w-11 h-11 rounded-xl bg-gradient-to-tr ${spec.gradient} flex items-center justify-center shadow-lg`}>
                    {spec.icon}
                  </div>
                  <span className="px-2 py-0.5 rounded-md bg-white/[0.06] border border-white/[0.1] text-[10px] font-mono font-bold text-slate-300">
                    {spec.badge}
                  </span>
                </div>

                {/* Title & Tagline */}
                <div>
                  <h3 className="font-bold text-sm text-white group-hover:text-violet-300 transition-colors">
                    {spec.name}
                  </h3>
                  <div className="text-[11px] font-mono text-slate-400 mt-0.5">
                    {spec.role}
                  </div>
                </div>

                {/* Description */}
                <p className="text-xs text-slate-300 leading-relaxed min-h-[3.6em]">
                  {spec.description}
                </p>

                {/* Safety Lattice Badge */}
                <div className="flex items-center gap-1.5 text-[10.5px] font-mono text-emerald-300 bg-emerald-950/30 px-2 py-1 rounded-lg border border-emerald-500/20">
                  <CheckCircle2 className="w-3 h-3 flex-shrink-0 text-emerald-400" />
                  <span className="truncate">{spec.safetyTier}</span>
                </div>

                {/* Tools Arsenal */}
                <div className="space-y-1.5 pt-1">
                  <span className="text-[10px] uppercase font-mono tracking-wider text-slate-400">
                    Active Tool Arsenal:
                  </span>
                  <div className="flex flex-wrap gap-1">
                    {spec.tools.map((t) => (
                      <span
                        key={t}
                        className="px-1.5 py-0.5 rounded bg-white/[0.04] text-[10px] font-mono text-slate-300 border border-white/[0.06]"
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Action Button & Quick Prompts */}
              <div className="mt-5 pt-3 border-t border-white/[0.06] space-y-2">
                <button
                  onClick={() => onSelectSpecialist(spec)}
                  className={`w-full py-2 px-3 rounded-xl bg-gradient-to-r ${spec.gradient} text-white font-medium text-xs flex items-center justify-center gap-1.5 shadow-md hover:brightness-110 transition-all`}
                >
                  <span>Chat with Specialist</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>

                {/* 1-Click Starter Prompt */}
                <button
                  onClick={() => onSelectSpecialist(spec, spec.suggestedPrompts[0])}
                  className="w-full text-left p-1.5 rounded-lg bg-black/20 hover:bg-white/[0.06] border border-white/[0.05] text-[11px] text-slate-300 hover:text-white transition-all truncate flex items-center gap-1.5"
                  title={spec.suggestedPrompts[0]}
                >
                  <Play className="w-2.5 h-2.5 text-violet-400 flex-shrink-0" />
                  <span className="truncate">{spec.suggestedPrompts[0]}</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
