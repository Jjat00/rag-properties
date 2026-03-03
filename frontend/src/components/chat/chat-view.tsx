import { ChatPanel } from "./chat-panel";
import { PropertiesPanel } from "./properties-panel";
import { useChat } from "@/hooks/use-chat";
import { ModelSelector } from "@/components/search/model-selector";
import type { EmbeddingModelInfo } from "@/types/api";
import { RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useState, useEffect } from "react";

interface ChatViewProps {
  models: EmbeddingModelInfo[];
  defaultModel: string;
}

export function ChatView({ models, defaultModel }: ChatViewProps) {
  const [selectedModel, setSelectedModel] = useState("");
  const [topK, setTopK] = useState(10);

  useEffect(() => {
    if (defaultModel && !selectedModel) setSelectedModel(defaultModel);
  }, [defaultModel, selectedModel]);

  const {
    messages,
    isStreaming,
    isSearching,
    currentResults,
    currentFilters,
    currentDisambiguation,
    currentMetrics,
    sendMessage,
    resetChat,
  } = useChat();

  const handleSend = (content: string) => {
    sendMessage(content, selectedModel, topK);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem)]">
      {/* Model selector bar */}
      <div className="flex items-center gap-3 px-4 py-2 border-b border-border bg-card/30">
        <ModelSelector
          models={models}
          selectedModel={selectedModel}
          onModelChange={setSelectedModel}
          topK={topK}
          onTopKChange={setTopK}
        />
        {messages.length > 0 && (
          <Button
            variant="outline"
            size="sm"
            onClick={resetChat}
            className="gap-1.5 text-xs"
          >
            <RotateCcw className="h-3 w-3" />
            Nueva
          </Button>
        )}
      </div>

      {/* Split layout */}
      <div className="flex flex-1 min-h-0">
        {/* Chat panel — 60% on desktop, full width on mobile */}
        <div className="w-full lg:w-3/5 flex flex-col min-h-0">
          <ChatPanel
            messages={messages}
            isStreaming={isStreaming}
            onSend={handleSend}
          />
        </div>

        {/* Properties panel — 40% on desktop, hidden on mobile */}
        <div className="hidden lg:flex lg:w-2/5 min-h-0">
          <PropertiesPanel
            results={currentResults}
            filters={currentFilters}
            disambiguation={currentDisambiguation}
            metrics={currentMetrics}
            isSearching={isSearching}
          />
        </div>
      </div>
    </div>
  );
}
