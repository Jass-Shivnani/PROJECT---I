export interface AgUiStreamCallbacks {
  onRunStart?: (data: { threadId?: string; runId?: string }) => void;
  onToolStart?: (data: { toolCallId: string; toolCallName: string }) => void;
  onToolArgs?: (data: { toolCallId: string; delta: string }) => void;
  onToolResult?: (data: { toolCallId: string; content: string }) => void;
  onToolEnd?: (data: { toolCallId: string }) => void;
  onTextDelta?: (delta: string, messageId: string) => void;
  onTextEnd?: (data: { messageId: string }) => void;
  onRunFinished?: (data: { threadId?: string; runId?: string }) => void;
  onError?: (error: string) => void;
}

export async function runAgUiAgentStream(
  message: string,
  threadId: string,
  callbacks: AgUiStreamCallbacks,
  signal?: AbortSignal
): Promise<void> {
  const res = await fetch('/api/ag-ui/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, thread_id: threadId }),
    signal,
  });

  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`AG-UI Stream failed (${res.status}): ${errText}`);
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

export async function fetchDesktopScreenshot(): Promise<string | null> {
  try {
    const res = await fetch('/api/desktop/screenshot');
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

export async function fetchAgUiInfo(): Promise<any> {
  const res = await fetch('/api/ag-ui/info');
  if (!res.ok) throw new Error(`HTTP error ${res.status}`);
  return res.json();
}
