export interface ToolCall {
  id: string;
  tool: string;
  params: Record<string, any>;
  status: 'running' | 'completed' | 'failed';
  result?: string;
  durationMs?: number;
  timestamp: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  toolCalls?: ToolCall[];
  isStreaming?: boolean;
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
}
