import React, { useEffect, useState } from "react"
import { BrowserRouter, Route, Routes } from "react-router-dom"
import { Sparkles } from "lucide-react"
import { Toaster } from "sonner"
import { ChatDrawer } from "@/components/agent/ChatDrawer"
import { Header } from "@/components/layout/Header"
import { Sidebar } from "@/components/layout/Sidebar"
import { AgentPage } from "@/pages/AgentPage"
import { DataPage } from "@/pages/DataPage"
import { ForecastPage } from "@/pages/ForecastPage"
import { OverviewPage } from "@/pages/OverviewPage"
import { RunsPage } from "@/pages/RunsPage"
import { SettingsPage } from "@/pages/SettingsPage"
import { Dataset, RunResult } from "@/types"

export const App: React.FC = () => {
  const [currentDataset, setCurrentDataset] = useState<Dataset | null>(null)
  const [activeRun, setActiveRun] = useState<RunResult | null>(null)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [isChatOpen, setIsChatOpen] = useState(false)
  const [darkMode, setDarkMode] = useState(() => {
    return window.matchMedia("(prefers-color-scheme: dark)").matches
  })

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add("dark")
    } else {
      document.documentElement.classList.remove("dark")
    }
  }, [darkMode])

  // Listen for custom trigger event to open the chat drawer
  useEffect(() => {
    const handleOpenChat = () => setIsChatOpen(true)
    window.addEventListener("open-forecastly-chat", handleOpenChat)
    return () => window.removeEventListener("open-forecastly-chat", handleOpenChat)
  }, [])

  // Global Cmd+K / Ctrl+K shortcut
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault()
        setIsChatOpen((prev) => !prev)
      }
    }
    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [])

  return (
    <BrowserRouter>
      <div className="flex h-screen w-screen overflow-hidden bg-background text-foreground relative">
        {/* Sidebar */}
        <Sidebar collapsed={sidebarCollapsed} setCollapsed={setSidebarCollapsed} />

        {/* Main Content Area */}
        <div className="flex flex-1 flex-col overflow-hidden">
          <Header
            currentDataset={currentDataset}
            darkMode={darkMode}
            setDarkMode={setDarkMode}
          />

          <main className="flex-1 overflow-y-auto p-6 sm:p-8">
            <Routes>
              <Route
                path="/"
                element={
                  <OverviewPage
                    currentDataset={currentDataset}
                    setCurrentDataset={setCurrentDataset}
                    latestRun={activeRun}
                    isLoadingLatestRun={false}
                  />
                }
              />
              <Route
                path="/agent"
                element={
                  <AgentPage
                    currentDataset={currentDataset}
                    activeRun={activeRun}
                  />
                }
              />
              <Route
                path="/data"
                element={
                  <DataPage
                    currentDataset={currentDataset}
                    setCurrentDataset={setCurrentDataset}
                  />
                }
              />
              <Route
                path="/forecast"
                element={
                  <ForecastPage
                    currentDataset={currentDataset}
                    activeRun={activeRun}
                    setActiveRun={setActiveRun}
                  />
                }
              />
              <Route
                path="/runs"
                element={
                  <RunsPage
                    onSelectRun={(run) => {
                      setActiveRun(run)
                    }}
                  />
                }
              />
              <Route path="/settings" element={<SettingsPage />} />
            </Routes>
          </main>
        </div>

        {/* Floating Slide-over Chat Drawer available on every page */}
        <ChatDrawer
          isOpen={isChatOpen}
          onClose={() => setIsChatOpen(false)}
          currentDataset={currentDataset}
          activeRun={activeRun}
        />

        {/* Global Floating Pill to toggle AI Chat */}
        {!isChatOpen && (
          <button
            onClick={() => setIsChatOpen(true)}
            className="fixed bottom-6 right-6 z-30 flex items-center gap-2 rounded-full bg-gradient-to-r from-indigo-600 to-violet-600 px-4 py-2.5 text-xs font-semibold text-white shadow-lg shadow-indigo-500/25 hover:shadow-xl hover:scale-105 active:scale-95 transition-all"
            title="Ask AI Forecasting Copilot (⌘K)"
          >
            <Sparkles className="h-4 w-4 animate-pulse" />
            <span className="tracking-wide">Ask AI</span>
            <kbd className="hidden sm:inline-block rounded bg-white/20 px-1.5 py-0.5 text-[10px] font-mono">
              ⌘K
            </kbd>
          </button>
        )}

        {/* Global Toast Notifications */}
        <Toaster richColors position="bottom-right" />
      </div>
    </BrowserRouter>
  )
}
export default App
