import { useEffect, useRef } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ChatMessage } from "./chat-message";
import { ChatInput } from "./chat-input";
import type { ChatMessage as ChatMessageType } from "@/types/api";
import { MessageSquare } from "lucide-react";

interface ChatPanelProps {
  messages: ChatMessageType[];
  isStreaming: boolean;
  onSend: (message: string) => void;
}

export function ChatPanel({ messages, isStreaming, onSend }: ChatPanelProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="flex flex-col h-full">
      <ScrollArea className="flex-1 overflow-y-auto">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full py-20 text-muted-foreground">
            <MessageSquare className="h-12 w-12 mb-4 opacity-30" />
            <p className="text-sm">Pregunta por cualquier propiedad...</p>
            <p className="text-xs mt-1 opacity-60">
              Ej: "terreno en el centro", "casa en Polanco con 3 recamaras"
            </p>
          </div>
        ) : (
          <div className="py-4 space-y-1">
            {messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} />
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </ScrollArea>

      <ChatInput onSend={onSend} disabled={isStreaming} />
    </div>
  );
}
