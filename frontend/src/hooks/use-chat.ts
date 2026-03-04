import { useCallback, useRef, useState } from "react";
import type {
  ChatMessage,
  PropertyResult,
  ParsedQuery,
  DisambiguationInfo,
  SearchMetrics,
} from "@/types/api";
import { streamChat } from "@/lib/chat-api";

let messageIdCounter = 0;
function nextId() {
  return `msg-${++messageIdCounter}`;
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [currentResults, setCurrentResults] = useState<PropertyResult[]>([]);
  const [currentFilters, setCurrentFilters] = useState<ParsedQuery | null>(null);
  const [currentDisambiguation, setCurrentDisambiguation] = useState<DisambiguationInfo[]>([]);
  const [currentStateResults, setCurrentStateResults] = useState<Record<string, PropertyResult[]>>({});
  const [currentMetrics, setCurrentMetrics] = useState<SearchMetrics | null>(null);
  const [totalResults, setTotalResults] = useState<number>(0);
  const abortRef = useRef<AbortController | null>(null);
  const assistantIdRef = useRef<string>("");

  const sendMessage = useCallback(
    (content: string, model: string, topK: number = 10) => {
      // Cancel any in-flight stream
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      // Add user message
      const userMsg: ChatMessage = {
        id: nextId(),
        role: "user",
        content,
      };

      // Add placeholder assistant message
      const assistantId = nextId();
      assistantIdRef.current = assistantId;
      const assistantMsg: ChatMessage = {
        id: assistantId,
        role: "assistant",
        content: "",
        isStreaming: true,
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setIsStreaming(true);
      setIsSearching(false);

      streamChat(
        {
          message: content,
          session_id: sessionId,
          model,
          top_k: topK,
        },
        {
          onSession: (sid) => {
            setSessionId(sid);
          },
          onToken: (token) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantIdRef.current
                  ? { ...m, content: m.content + token }
                  : m,
              ),
            );
          },
          onToolStart: () => {
            setIsSearching(true);
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantIdRef.current
                  ? { ...m, isSearching: true }
                  : m,
              ),
            );
          },
          onResults: (results, total) => {
            setCurrentResults(results);
            setTotalResults(total);
            setIsSearching(false);
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantIdRef.current
                  ? { ...m, results, isSearching: false }
                  : m,
              ),
            );
          },
          onFilters: (filters) => {
            setCurrentFilters(filters);
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantIdRef.current
                  ? { ...m, filters }
                  : m,
              ),
            );
          },
          onDisambiguation: (disambiguation) => {
            setCurrentDisambiguation(disambiguation);
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantIdRef.current
                  ? { ...m, disambiguation }
                  : m,
              ),
            );
          },
          onStateResults: (stateResults) => {
            setCurrentStateResults(stateResults);
          },
          onMetrics: (metrics) => {
            setCurrentMetrics(metrics);
          },
          onDone: () => {
            setIsStreaming(false);
            setIsSearching(false);
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantIdRef.current
                  ? { ...m, isStreaming: false, isSearching: false }
                  : m,
              ),
            );
          },
          onError: (error) => {
            setIsStreaming(false);
            setIsSearching(false);
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantIdRef.current
                  ? {
                      ...m,
                      content: m.content || `Error: ${error}`,
                      isStreaming: false,
                      isSearching: false,
                    }
                  : m,
              ),
            );
          },
        },
        controller.signal,
      );
    },
    [sessionId],
  );

  const resetChat = useCallback(() => {
    abortRef.current?.abort();
    setMessages([]);
    setSessionId(null);
    setIsStreaming(false);
    setIsSearching(false);
    setCurrentResults([]);
    setTotalResults(0);
    setCurrentFilters(null);
    setCurrentDisambiguation([]);
    setCurrentStateResults({});
    setCurrentMetrics(null);
  }, []);

  return {
    messages,
    sessionId,
    isStreaming,
    isSearching,
    currentResults,
    totalResults,
    currentFilters,
    currentDisambiguation,
    currentStateResults,
    currentMetrics,
    sendMessage,
    resetChat,
  };
}
