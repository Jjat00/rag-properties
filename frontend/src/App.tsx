import { useState, useEffect } from "react"
import { Activity, Search as SearchIcon, BarChart3, GitCompare, RotateCcw, MessageSquare, FlaskConical } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { TooltipProvider } from "@/components/ui/tooltip"
import { SearchBar } from "@/components/search/search-bar"
import { ModelSelector } from "@/components/search/model-selector"
import { FilterChips } from "@/components/search/filter-chips"
import { IdleState } from "@/components/search/idle-state"
import { ResultsGrid } from "@/components/results/results-grid"
import { LoadingSkeleton } from "@/components/results/loading-skeleton"
import { ScoreGauge } from "@/components/analytics/score-gauge"
import { TimingBreakdown } from "@/components/analytics/timing-breakdown"
import { ScoreDistribution } from "@/components/analytics/score-distribution"
import { SimilarityGraph } from "@/components/analytics/similarity-graph"
import { ModelComparison } from "@/components/analytics/model-comparison"
import { ChatView } from "@/components/chat/chat-view"
import { useSearch } from "@/hooks/use-search"
import { useModels } from "@/hooks/use-models"
import { fetchHealth } from "@/lib/api"

type AppView = "chat" | "playground"

function App() {
  const { models, defaultModel } = useModels()
  const [selectedModel, setSelectedModel] = useState("")
  const [topK, setTopK] = useState(10)
  const [healthy, setHealthy] = useState<boolean | null>(null)
  const [query, setQuery] = useState("")
  const [activeDisambig, setActiveDisambig] = useState<Record<string, string>>({})
  const [selectedState, setSelectedState] = useState<string | null>(null)
  const [view, setView] = useState<AppView>("chat")
  const { status, data, error, search, reset } = useSearch()

  useEffect(() => {
    if (defaultModel && !selectedModel) setSelectedModel(defaultModel)
  }, [defaultModel, selectedModel])

  useEffect(() => {
    fetchHealth()
      .then(() => setHealthy(true))
      .catch(() => setHealthy(false))
  }, [])

  const handleSearch = (q: string) => {
    setActiveDisambig({})
    setSelectedState(null)
    search(q, selectedModel, topK)
  }

  const handleSuggestion = (q: string) => {
    setQuery(q)
    setActiveDisambig({})
    setSelectedState(null)
    search(q, selectedModel, topK)
  }

  const handleReset = () => {
    setQuery("")
    setActiveDisambig({})
    setSelectedState(null)
    reset()
  }

  const handleDisambigClick = (field: string, value: string) => {
    setActiveDisambig(prev =>
      prev[field] === value ? { ...prev, [field]: "" } : { ...prev, [field]: value }
    )
  }

  const handleStateClick = (state: string) => {
    setSelectedState(prev => prev === state ? null : state)
  }

  const baseResults = selectedState
    ? (data?.state_results[selectedState] ?? [])
    : data?.results ?? []

  const filteredResults = baseResults.filter(r => {
    for (const [field, value] of Object.entries(activeDisambig)) {
      if (!value) continue
      const fieldKey = field as keyof typeof r
      if (r[fieldKey] !== value) return false
    }
    return true
  })

  return (
    <TooltipProvider>
      <div className="min-h-screen bg-background">
        {/* Nav */}
        <nav className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <SearchIcon className="h-5 w-5 text-primary" />
              <span className="font-semibold text-foreground">RAG Properties</span>
            </div>

            {/* View toggle */}
            <div className="flex items-center gap-1 bg-muted rounded-lg p-0.5">
              <button
                onClick={() => setView("chat")}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                  view === "chat"
                    ? "bg-background text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <MessageSquare className="h-3.5 w-3.5" />
                Chat
              </button>
              <button
                onClick={() => setView("playground")}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                  view === "playground"
                    ? "bg-background text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <FlaskConical className="h-3.5 w-3.5" />
                Playground
              </button>
            </div>

            <Badge
              variant="outline"
              className={
                healthy === true
                  ? "bg-green-500/15 text-green-400 border-green-500/30"
                  : healthy === false
                    ? "bg-red-500/15 text-red-400 border-red-500/30"
                    : "bg-muted text-muted-foreground border-border"
              }
            >
              <Activity className="h-3 w-3 mr-1" />
              {healthy === true ? "Online" : healthy === false ? "Offline" : "Checking..."}
            </Badge>
          </div>
        </nav>

        {/* Chat view */}
        {view === "chat" && (
          <ChatView models={models} defaultModel={defaultModel} />
        )}

        {/* Playground view */}
        {view === "playground" && (
          <main className="max-w-7xl mx-auto px-4 py-8 space-y-6">
            {/* Search */}
            <div className="flex flex-col sm:flex-row items-stretch sm:items-start gap-3">
              <div className="flex-1">
                <SearchBar
                  value={query}
                  onChange={setQuery}
                  onSearch={handleSearch}
                  loading={status === "loading"}
                />
              </div>
              {(status === "success" || status === "error") && (
                <Button
                  variant="outline"
                  onClick={handleReset}
                  className="h-12 shrink-0 gap-2 border-border text-muted-foreground hover:text-foreground"
                >
                  <RotateCcw className="h-4 w-4" />
                  Nueva busqueda
                </Button>
              )}
            </div>

            {/* Model + TopK selector */}
            <ModelSelector
              models={models}
              selectedModel={selectedModel}
              onModelChange={setSelectedModel}
              topK={topK}
              onTopKChange={setTopK}
            />

            {/* Filter chips */}
            {data && (
              <FilterChips
                filters={data.parsed_filters}
                results={baseResults}
                disambiguation={data.disambiguation}
                activeDisambig={activeDisambig}
                selectedState={selectedState}
                onDisambigClick={handleDisambigClick}
                onStateClick={handleStateClick}
              />
            )}

            {/* Error */}
            {error && (
              <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
                Error: {error}
              </div>
            )}

            {/* Loading skeleton */}
            {status === "loading" && <LoadingSkeleton />}

            {/* Results tabs */}
            {data && (
              <Tabs defaultValue="results" className="w-full">
                <TabsList className="bg-card border border-border">
                  <TabsTrigger value="results" className="gap-1.5">
                    <SearchIcon className="h-3.5 w-3.5" />
                    Resultados ({filteredResults.length}{filteredResults.length !== data.total ? ` de ${data.total}` : ""})
                  </TabsTrigger>
                  <TabsTrigger value="analytics" className="gap-1.5">
                    <BarChart3 className="h-3.5 w-3.5" />
                    Analytics
                  </TabsTrigger>
                  <TabsTrigger value="compare" className="gap-1.5">
                    <GitCompare className="h-3.5 w-3.5" />
                    Comparar
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="results" className="mt-4">
                  <ResultsGrid results={filteredResults} />
                </TabsContent>

                <TabsContent value="analytics" className="mt-4 space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <ScoreGauge metrics={data.metrics} />
                    <TimingBreakdown metrics={data.metrics} />
                    <ScoreDistribution results={data.results} />
                  </div>
                  <SimilarityGraph results={data.results} />
                </TabsContent>

                <TabsContent value="compare" className="mt-4">
                  <ModelComparison models={models} currentQuery={data.query} topK={topK} />
                </TabsContent>
              </Tabs>
            )}

            {/* Idle state */}
            {status === "idle" && (
              <IdleState modelCount={models.length} onSuggestion={handleSuggestion} />
            )}
          </main>
        )}
      </div>
    </TooltipProvider>
  )
}

export default App
