import React, { useEffect, useState } from "react"
import { BrowserRouter, Route, Routes } from "react-router-dom"
import { Toaster } from "sonner"
import { Header } from "@/components/layout/Header"
import { Sidebar } from "@/components/layout/Sidebar"
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

  return (
    <BrowserRouter>
      <div className="flex h-screen w-screen overflow-hidden bg-background text-foreground">
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

        {/* Global Toast Notifications */}
        <Toaster richColors position="bottom-right" />
      </div>
    </BrowserRouter>
  )
}
export default App
