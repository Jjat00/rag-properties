import type {
  ChatRequest,
  ChatEventType,
  PropertyResult,
  ParsedQuery,
  DisambiguationInfo,
  SearchMetrics,
} from "@/types/api";

const BASE = "/api";

interface ChatCallbacks {
  onSession?: (sessionId: string) => void;
  onToken?: (token: string) => void;
  onToolStart?: (name: string, args: Record<string, unknown>) => void;
  onResults?: (results: PropertyResult[], total: number) => void;
  onFilters?: (filters: ParsedQuery) => void;
  onDisambiguation?: (disambiguation: DisambiguationInfo[]) => void;
  onStateResults?: (stateResults: Record<string, PropertyResult[]>) => void;
  onMetrics?: (metrics: SearchMetrics) => void;
  onDone?: () => void;
  onError?: (error: string) => void;
}

export function streamChat(
  request: ChatRequest,
  callbacks: ChatCallbacks,
  signal?: AbortSignal,
): void {
  const url = `${BASE}/chat`;

  fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
    signal,
  })
    .then(async (res) => {
      if (!res.ok) {
        const text = await res.text();
        callbacks.onError?.(`API error ${res.status}: ${text}`);
        return;
      }

      const reader = res.body?.getReader();
      if (!reader) {
        callbacks.onError?.("No response body");
        return;
      }

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        let currentEvent: ChatEventType | null = null;

        for (const line of lines) {
          if (line.startsWith("event:")) {
            currentEvent = line.slice(6).trim() as ChatEventType;
          } else if (line.startsWith("data:") && currentEvent) {
            const rawData = line.slice(5).trim();
            handleEvent(currentEvent, rawData, callbacks);
            currentEvent = null;
          } else if (line === "") {
            currentEvent = null;
          }
        }
      }

      // Process remaining buffer
      if (buffer.trim()) {
        const lines = buffer.split("\n");
        let currentEvent: ChatEventType | null = null;
        for (const line of lines) {
          if (line.startsWith("event:")) {
            currentEvent = line.slice(6).trim() as ChatEventType;
          } else if (line.startsWith("data:") && currentEvent) {
            handleEvent(currentEvent, line.slice(5).trim(), callbacks);
            currentEvent = null;
          }
        }
      }
    })
    .catch((err) => {
      if (err instanceof DOMException && err.name === "AbortError") return;
      callbacks.onError?.(err instanceof Error ? err.message : "Unknown error");
    });
}

function handleEvent(
  event: ChatEventType,
  rawData: string,
  callbacks: ChatCallbacks,
): void {
  try {
    switch (event) {
      case "session": {
        const data = JSON.parse(rawData);
        callbacks.onSession?.(data.session_id);
        break;
      }
      case "token": {
        const token = JSON.parse(rawData);
        callbacks.onToken?.(token);
        break;
      }
      case "tool_start": {
        const data = JSON.parse(rawData);
        callbacks.onToolStart?.(data.name, data.args);
        break;
      }
      case "results": {
        const data = JSON.parse(rawData);
        callbacks.onResults?.(data.items, data.total);
        break;
      }
      case "filters": {
        const data = JSON.parse(rawData);
        callbacks.onFilters?.(data);
        break;
      }
      case "disambiguation": {
        const data = JSON.parse(rawData);
        callbacks.onDisambiguation?.(data);
        break;
      }
      case "state_results": {
        const data = JSON.parse(rawData);
        callbacks.onStateResults?.(data);
        break;
      }
      case "metrics": {
        const data = JSON.parse(rawData);
        callbacks.onMetrics?.(data);
        break;
      }
      case "done":
        callbacks.onDone?.();
        break;
      case "error": {
        const msg = JSON.parse(rawData);
        callbacks.onError?.(msg);
        break;
      }
    }
  } catch {
    // Parsing error — ignore malformed SSE data
  }
}
