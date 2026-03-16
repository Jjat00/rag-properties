import { useEffect, useState } from "react"
import { BrowserRouter, Routes, Route, NavLink, Navigate } from "react-router-dom"
import { Activity, Search as SearchIcon, MessageSquare, FlaskConical, Images } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { TooltipProvider } from "@/components/ui/tooltip"
import { ChatView } from "@/components/chat/chat-view"
import { PlaygroundView } from "@/components/playground/playground-view"
import { MultimodalView } from "@/components/multimodal/multimodal-view"
import { useModels } from "@/hooks/use-models"
import { fetchHealth } from "@/lib/api"

const NAV_ITEMS = [
  { to: "/chat", label: "Chat", icon: MessageSquare },
  { to: "/playground", label: "Playground", icon: FlaskConical },
  { to: "/multimodal", label: "Multimodal", icon: Images },
] as const

function Layout() {
  const { models, defaultModel } = useModels()
  const [healthy, setHealthy] = useState<boolean | null>(null)

  useEffect(() => {
    fetchHealth()
      .then(() => setHealthy(true))
      .catch(() => setHealthy(false))
  }, [])

  return (
    <div className="min-h-screen bg-background">
      {/* Nav */}
      <nav className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <SearchIcon className="h-5 w-5 text-primary" />
            <span className="font-semibold text-foreground">RAG Properties</span>
          </div>

          {/* Route-based nav toggle */}
          <div className="flex items-center gap-1 bg-muted rounded-lg p-0.5">
            {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                    isActive
                      ? "bg-background text-foreground shadow-sm"
                      : "text-muted-foreground hover:text-foreground"
                  }`
                }
              >
                <Icon className="h-3.5 w-3.5" />
                {label}
              </NavLink>
            ))}
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

      {/* Routes */}
      <Routes>
        <Route path="/chat" element={<ChatView models={models} defaultModel={defaultModel} />} />
        <Route path="/playground" element={<PlaygroundView />} />
        <Route path="/multimodal" element={<MultimodalView />} />
        <Route path="*" element={<Navigate to="/chat" replace />} />
      </Routes>
    </div>
  )
}

function App() {
  return (
    <BrowserRouter>
      <TooltipProvider>
        <Layout />
      </TooltipProvider>
    </BrowserRouter>
  )
}

export default App
