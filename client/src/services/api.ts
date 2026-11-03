export interface AgUiStreamCallbacks {
  onRunStart?: (data: { threadId?: string; runId?: string }) => void;
  onToolStart?: (data: { toolCallId: string; toolCallName: string }) => void;
  onToolArgs?: (data: { toolCallId: string; delta: string }) => void;
  onToolResult?: (data: { toolCallId: string; content: string; success?: boolean; error?: string }) => void;
  onToolEnd?: (data: { toolCallId: string }) => void;
  onTextDelta?: (delta: string, messageId: string) => void;
  onTextEnd?: (data: { messageId: string }) => void;
  onRunFinished?: (data: { threadId?: string; runId?: string }) => void;
  onError?: (error: string) => void;
  onCustom?: (data: { name: string; value: any }) => void;
}

export async function runAgUiAgentStream(
  message: string,
  threadId: string,
  callbacks: AgUiStreamCallbacks,
  signal?: AbortSignal,
  recentMessages?: Array<{ role: string; content: string }>,
  model?: string
): Promise<void> {
  const res = await fetch('/api/ag-ui/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      thread_id: threadId,
      messages: recentMessages,
      parameters: model ? { model } : undefined,
    }),
    signal,
  });

  if (!res.ok) {
    const errText = await res.text();
    if (res.status === 502 || res.status === 504) {
      throw new Error(`Dione backend service reconnecting (${res.status}). Please check http://localhost:8900.`);
    }
    throw new Error(`AG-UI Stream failed (${res.status}): ${errText || res.statusText}`);
  }

  const reader = res.body?.getReader();
  if (!reader) throw new Error('ReadableStream not supported.');

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith(':')) continue;

      if (trimmed.startsWith('data: ')) {
        const rawJson = trimmed.slice(6);
        try {
          const event = JSON.parse(rawJson);
          switch (event.type) {
            case 'RUN_STARTED':
              callbacks.onRunStart?.(event);
              break;
            case 'CUSTOM':
              callbacks.onCustom?.(event);
              break;
            case 'TOOL_CALL_START':
              callbacks.onToolStart?.(event);
              break;
            case 'TOOL_CALL_ARGS':
              callbacks.onToolArgs?.(event);
              break;
            case 'TOOL_CALL_RESULT':
              callbacks.onToolResult?.(event);
              break;
            case 'TOOL_CALL_END':
              callbacks.onToolEnd?.(event);
              break;
            case 'TEXT_MESSAGE_CONTENT':
              callbacks.onTextDelta?.(event.delta, event.messageId);
              break;
            case 'TEXT_MESSAGE_END':
              callbacks.onTextEnd?.(event);
              break;
            case 'RUN_FINISHED':
              callbacks.onRunFinished?.(event);
              break;
            case 'RUN_ERROR':
              callbacks.onError?.(event.message || 'Unknown agent error');
              break;
          }
        } catch {
          // ignore parsing error on raw event
        }
      }
    }
  }
}

export async function fetchDesktopScreenshot(withGrid: boolean = false): Promise<string | null> {
  try {
    const url = withGrid ? '/api/desktop/screenshot?with_grid=true' : '/api/desktop/screenshot';
    const res = await fetch(url);
    if (!res.ok) return null;
    const data = await res.json();
    return data.image || null;
  } catch {
    return null;
  }
}

export async function setDesktopMode(mode: 'computer_use' | 'ambient_cowork'): Promise<boolean> {
  try {
    const res = await fetch('/api/desktop/mode', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode }),
    });
    return res.ok;
  } catch {
    return false;
  }
}

export async function fetchWakeupBriefing(): Promise<{ available: boolean; briefing?: any }> {
  try {
    const res = await fetch('/api/ag-ui/briefing');
    if (!res.ok) return { available: false };
    return res.json();
  } catch {
    return { available: false };
  }
}

export async function triggerDreamCycle(): Promise<any> {
  try {
    const res = await fetch('/api/ag-ui/briefing/trigger', { method: 'POST' });
    if (!res.ok) return { success: false };
    return res.json();
  } catch {
    return { success: false };
  }
}

export async function executeComputerAction(payload: Record<string, any>): Promise<any> {
  try {
    const res = await fetch('/api/ag-ui/computer-action', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return res.json();
  } catch (err: any) {
    return { success: false, error: err.message };
  }
}

export async function submitActionApproval(confirmationId: string, approved: boolean, reason?: string): Promise<any> {
  try {
    const res = await fetch('/api/ag-ui/action-approval', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ confirmation_id: confirmationId, approved, reason }),
    });
    return res.json();
  } catch (err: any) {
    return { success: false, error: err.message };
  }
}

export async function fetchAgUiInfo(): Promise<any> {
  const res = await fetch('/api/ag-ui/info');
  if (!res.ok) throw new Error(`HTTP error ${res.status}`);
  return res.json();
}

export async function fetchIntegrations(): Promise<any> {
  try {
    const res = await fetch('/api/integrations/');
    if (!res.ok) return { total: 0, connected: 0, integrations: [] };
    return res.json();
  } catch {
    return { total: 0, connected: 0, integrations: [] };
  }
}

export async function connectUnifiedGoogle(params: Record<string, any> = {}): Promise<any> {
  try {
    const res = await fetch('/api/integrations/google/connect', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ params }),
    });
    return res.json();
  } catch (err: any) {
    return { success: false, error: err.message };
  }
}

export async function connectIntegration(integrationId: string, params: Record<string, any> = {}): Promise<any> {
  try {
    const res = await fetch(`/api/integrations/${integrationId}/connect`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ params }),
    });
    return res.json();
  } catch (err: any) {
    return { success: false, error: err.message };
  }
}

export async function disconnectIntegration(integrationId: string): Promise<any> {
  try {
    const res = await fetch(`/api/integrations/${integrationId}/disconnect`, {
      method: 'POST',
    });
    return res.json();
  } catch (err: any) {
    return { success: false, error: err.message };
  }
}

export async function syncIntegration(integrationId: string): Promise<any> {
  try {
    const res = await fetch(`/api/integrations/${integrationId}/sync`, {
      method: 'POST',
    });
    return res.json();
  } catch (err: any) {
    return { success: false, error: err.message };
  }
}

export async function fetchWhatsAppQr(): Promise<any> {
  try {
    const res = await fetch('/api/integrations/whatsapp/qr');
    return res.json();
  } catch (err: any) {
    return { success: false, error: err.message };
  }
}
