export interface ToolCall {
  id: string;
  tool: string;
  agent?: string;
  safetyTier?: string;
  latencyMs?: number;
  params: Record<string, any>;
  result?: string;
  status: 'running' | 'completed' | 'error' | 'blocked';
  timestamp: string;
}

export interface OrchestrationNode {
  id: string;
  badge: string;
  agentName: string;
  title: string;
  tool: string;
  status: 'pending' | 'running' | 'completed' | 'blocked' | 'error';
  latency: number;
  tier: string;
  output: string;
}

export interface AgentHandoff {
  from: string;
  to: string;
  msg: string;
  time: string;
}

export interface SafetyApprovalRequest {
  confirmation_id: string;
  tool: string;
  params: Record<string, any>;
  thought?: string;
  risk_level?: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'filler';
  content: string;
  timestamp: string;
  isStreaming?: boolean;
  toolCalls?: ToolCall[];
  dagNodes?: OrchestrationNode[];
  handoffs?: AgentHandoff[];
  approvalRequest?: SafetyApprovalRequest;
  approvalStatus?: 'pending' | 'approved' | 'denied';
}

export interface Thread {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messages: Message[];
}

export interface ComputerUseState {
  enabled: boolean;
  screenshotUrl: string | null;
  lastCaptureTime?: string;
  isCapturing?: boolean;
  uiaBoxesVisible?: boolean;
  failSafeTripped?: boolean;
}

export interface VoiceTalkState {
  enabled: boolean;
  isConnected: boolean;
  isListening: boolean;
  isSpeaking: boolean;
  volume: number;
  statusText: string;
}

export interface SystemControlSettings {
  turboMode: boolean; // Fast-track low/mid-tier actions
  computerUse: boolean;
  visionPreview: boolean;
  autonomousDream: boolean;
}
