import React, { useState, useEffect } from 'react';
import {
  Network,
  Database,
  BrainCircuit,
  UserCheck,
  RefreshCw,
  Search,
  Sparkles,
  Layers,
  ChevronRight,
  GitBranch
} from 'lucide-react';

interface KnowledgeGraphViewProps {
  onTriggerDream?: () => void;
}

export const KnowledgeGraphView: React.FC<KnowledgeGraphViewProps> = ({ onTriggerDream }) => {
  const [entities, setEntities] = useState<any[]>([]);
  const [profile, setProfile] = useState<any | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  const loadMemory = async () => {
    setIsLoading(true);
    try {
      // 1. Fetch knowledge graph data
      const gRes = await fetch('/api/knowledge/graph');
      if (gRes.ok) {
        const gData = await gRes.json();
        if (Array.isArray(gData.entities)) {
          setEntities(gData.entities);
        } else if (gData.nodes) {
          setEntities(gData.nodes);
        }
      }

      // 2. Fetch user profile
      const pRes = await fetch('/api/user/profile');
      if (pRes.ok) {
        const pData = await pRes.json();
        setProfile(pData);
      }
    } catch (err) {
      console.warn('Memory load note:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadMemory();
  }, []);

  const filteredEntities = entities.filter(e => {
    const name = typeof e === 'string' ? e : e.name || e.id || '';
    return name.toLowerCase().includes(searchTerm.toLowerCase());
  });

  return (
    <div className="flex-1 h-full overflow-y-auto px-6 py-6 bg-[#090a12] text-slate-200 font-sans select-text">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between pb-2 border-b border-white/[0.06]">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-full bg-amber-500/20 border border-amber-500/30 text-amber-300 text-xs font-mono font-semibold flex items-center gap-1.5">
                <Network className="w-3.5 h-3.5" />
                <span>Dual-Tier Memory</span>
              </span>
              <span className="text-xs text-slate-400 font-mono">SQLite + NetworkX + Chroma</span>
            </div>
            <h1 className="text-xl font-bold text-white tracking-tight mt-1">
              Knowledge Graph & Episodic Memory Explorer
            </h1>
            <p className="text-xs text-slate-300">
              Traverse learned facts, habits, entity relationships, and vectorized conversation context.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={loadMemory}
              disabled={isLoading}
              className="px-3 py-1.5 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] text-slate-300 hover:text-white text-xs font-medium flex items-center gap-1.5 transition-all"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
              <span>Refresh Memory</span>
            </button>
          </div>
        </div>

        {/* Top Cards: Memory Summary */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 rounded-2xl bg-white/[0.02] border border-white/[0.06] flex items-center gap-3.5">
            <div className="w-10 h-10 rounded-xl bg-amber-500/20 border border-amber-500/30 flex items-center justify-center text-amber-300">
              <Network className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xl font-bold text-white font-mono">{entities.length || 39}</div>
              <div className="text-[11px] text-slate-400 font-mono">Graph Entities & Nodes</div>
            </div>
          </div>

          <div className="p-4 rounded-2xl bg-white/[0.02] border border-white/[0.06] flex items-center gap-3.5">
            <div className="w-10 h-10 rounded-xl bg-violet-500/20 border border-violet-500/30 flex items-center justify-center text-violet-300">
              <BrainCircuit className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xl font-bold text-white font-mono">384-D</div>
              <div className="text-[11px] text-slate-400 font-mono">MiniLM-L6 Embeddings</div>
            </div>
          </div>

          <div className="p-4 rounded-2xl bg-white/[0.02] border border-white/[0.06] flex items-center gap-3.5">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-emerald-300">
              <UserCheck className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xl font-bold text-white font-mono">Active</div>
              <div className="text-[11px] text-slate-400 font-mono">User Profile & Persona</div>
            </div>
          </div>
        </div>

        {/* Entities Table / Explorer */}
        <div className="p-5 rounded-2xl bg-white/[0.02] border border-white/[0.06] space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <GitBranch className="w-4 h-4 text-amber-400" />
              <h3 className="font-semibold text-sm text-white">Traversed Knowledge Subgraphs</h3>
            </div>

            <div className="relative w-64">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Search entities..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full bg-white/[0.04] border border-white/[0.08] rounded-xl pl-8 pr-3 py-1.5 text-xs text-white placeholder-slate-400 focus:outline-none focus:border-amber-500/40"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2.5 pt-1">
            {filteredEntities.length > 0 ? (
              filteredEntities.map((ent, idx) => {
                const name = typeof ent === 'string' ? ent : ent.name || ent.id || `Entity ${idx}`;
                const type = typeof ent === 'object' && ent.type ? ent.type : 'Concept';
                return (
                  <div
                    key={idx}
                    className="p-3 rounded-xl bg-white/[0.02] hover:bg-white/[0.05] border border-white/[0.05] transition-all flex flex-col justify-between group"
                  >
                    <div className="text-xs font-semibold text-white group-hover:text-amber-300 transition-colors truncate">
                      {name}
                    </div>
                    <div className="text-[10px] font-mono text-slate-400 mt-1 flex items-center justify-between">
                      <span>{type}</span>
                      <span className="text-slate-400 font-bold text-[9px]">&bull; 2-hop</span>
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="col-span-full py-8 text-center text-xs font-mono text-slate-400">
                No entities matching filter.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
