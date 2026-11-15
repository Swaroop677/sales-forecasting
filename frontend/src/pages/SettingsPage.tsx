import React, { useEffect, useState } from "react"
import {
  AlertTriangle,
  Bot,
  CheckCircle2,
  Cpu,
  ExternalLink,
  Eye,
  EyeOff,
  HardDrive,
  KeyRound,
  RotateCcw,
  Save,
  Server,
  ShieldCheck,
  Sparkles,
  Zap,
} from "lucide-react"
import { toast } from "sonner"
import { api } from "@/api/client"
import { Badge } from "@/components/ui/Badge"
import { Button } from "@/components/ui/Button"
import { Card } from "@/components/ui/Card"
import { LLMSettings } from "@/types"

export const SettingsPage: React.FC = () => {
  const [healthInfo, setHealthInfo] = useState<any>(null)

  // LLM BYOK settings state
  const [provider, setProvider] = useState<"gemini" | "openai" | "fallback">("gemini")
  const [apiKey, setApiKey] = useState("")
  const [baseUrl, setBaseUrl] = useState("")
  const [model, setModel] = useState("gemini-2.5-flash")
  const [showKey, setShowKey] = useState(false)
  const [isTesting, setIsTesting] = useState(false)
  const [testResult, setTestResult] = useState<{
    success: boolean
    message: string
  } | null>(null)

  useEffect(() => {
    fetch("/api/health")
      .then((res) => res.json())
      .then(setHealthInfo)
      .catch(() => {})

    // Load saved settings from localStorage
    try {
      const stored = localStorage.getItem("forecastly_llm_settings")
      if (stored) {
        const parsed: LLMSettings = JSON.parse(stored)
        if (parsed.provider) setProvider(parsed.provider)
        if (parsed.apiKey) setApiKey(parsed.apiKey)
        if (parsed.baseUrl) setBaseUrl(parsed.baseUrl)
        if (parsed.model) setModel(parsed.model)
      }
    } catch {
      // ignore
    }
  }, [])

  const handleProviderChange = (newProvider: "gemini" | "openai" | "fallback") => {
    setProvider(newProvider)
    setTestResult(null)
    if (newProvider === "gemini") {
      if (!model || model === "gpt-4o-mini" || model === "rule-based-v2") {
        setModel("gemini-2.5-flash")
      }
      setBaseUrl("")
    } else if (newProvider === "openai") {
      if (!model || model === "gemini-2.5-flash" || model === "rule-based-v2") {
        setModel("gpt-4o-mini")
      }
      if (!baseUrl) {
        setBaseUrl("https://api.openai.com/v1")
      }
    } else if (newProvider === "fallback") {
      setModel("rule-based-v2")
      setBaseUrl("")
    }
  }

  const handleSaveSettings = () => {
    const settings: LLMSettings = {
      provider,
      apiKey: apiKey.trim(),
      baseUrl: baseUrl.trim(),
      model: model.trim(),
    }
    localStorage.setItem("forecastly_llm_settings", JSON.stringify(settings))
    toast.success("AI Agent settings saved to browser storage")
  }

  const handleResetSettings = () => {
    localStorage.removeItem("forecastly_llm_settings")
    setProvider("gemini")
    setApiKey("")
    setBaseUrl("")
    setModel("gemini-2.5-flash")
    setTestResult(null)
    toast.info("Settings reset to defaults")
  }

  const handleTestConnection = async () => {
    setIsTesting(true)
    setTestResult(null)
    try {
      const res = await api.testConnection({
        provider,
        apiKey: apiKey.trim(),
        baseUrl: baseUrl.trim(),
        model: model.trim(),
      })
      if (res.success) {
        setTestResult({ success: true, message: res.message })
        toast.success("Connection test succeeded!")
      } else {
        setTestResult({ success: false, message: res.message })
        toast.error(`Test failed: ${res.message}`)
      }
    } catch (err: any) {
      setTestResult({ success: false, message: err.message || "Failed to reach endpoint" })
      toast.error(`Test failed: ${err.message}`)
    } finally {
      setIsTesting(false)
    }
  }

  return (
    <div className="space-y-8 animate-in fade-in duration-200 max-w-4xl pb-12">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">Settings & Configuration</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Configure Phase 2 AI Agent providers, Bring-Your-Own-Key (BYOK), and inspect runtime specifications.
        </p>
      </div>

      {/* AI Agent LLM Provider Card */}
      <Card className="p-6 space-y-6 border-indigo-500/20 shadow-sm">
        <div className="flex items-center justify-between pb-3 border-b border-border">
          <div className="flex items-center gap-2.5">
            <div className="h-8 w-8 rounded-lg bg-indigo-500/10 flex items-center justify-center text-indigo-500">
              <Bot className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-foreground">AI Copilot & LLM Provider</h2>
              <p className="text-xs text-muted-foreground">
                Configure the LLM engine powering conversational forecasting, what-if simulations, and executive summaries.
              </p>
            </div>
          </div>
          <Badge variant="outline" className="text-xs font-medium border-indigo-500/30 text-indigo-500">
            Phase 2
          </Badge>
        </div>

        {/* Provider Selection */}
        <div className="space-y-2">
          <label className="text-xs font-semibold text-foreground">Select LLM Provider</label>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <button
              type="button"
              onClick={() => handleProviderChange("gemini")}
              className={`p-3.5 rounded-xl border text-left transition-all ${
                provider === "gemini"
                  ? "border-primary bg-primary/5 text-foreground ring-1 ring-primary"
                  : "border-border hover:bg-secondary/40 text-muted-foreground"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-semibold text-xs text-foreground">Google Gemini</span>
                <Sparkles className="h-3.5 w-3.5 text-indigo-500" />
              </div>
              <p className="text-[11px] text-muted-foreground mt-1">
                Official Google GenAI. Fast streaming & tool-calling.
              </p>
            </button>

            <button
              type="button"
              onClick={() => handleProviderChange("openai")}
              className={`p-3.5 rounded-xl border text-left transition-all ${
                provider === "openai"
                  ? "border-primary bg-primary/5 text-foreground ring-1 ring-primary"
                  : "border-border hover:bg-secondary/40 text-muted-foreground"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-semibold text-xs text-foreground">OpenAI-Compatible</span>
                <Server className="h-3.5 w-3.5 text-violet-500" />
              </div>
              <p className="text-[11px] text-muted-foreground mt-1">
                Groq, OpenRouter, Ollama, OpenAI, or local vLLM.
              </p>
            </button>

            <button
              type="button"
              onClick={() => handleProviderChange("fallback")}
              className={`p-3.5 rounded-xl border text-left transition-all ${
                provider === "fallback"
                  ? "border-primary bg-primary/5 text-foreground ring-1 ring-primary"
                  : "border-border hover:bg-secondary/40 text-muted-foreground"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-semibold text-xs text-foreground">Rule-Based Fallback</span>
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
              </div>
              <p className="text-[11px] text-muted-foreground mt-1">
                Zero API key required. Never fails or runs out of quota.
              </p>
            </button>
          </div>
        </div>

        {/* Provider Details & Inputs */}
        {provider !== "fallback" && (
          <div className="space-y-4 pt-1">
            {/* API Key */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                  <KeyRound className="h-3.5 w-3.5 text-muted-foreground" />
                  <span>API Key</span>
                </label>
                <span className="text-[11px] text-muted-foreground">
                  (Optional if server environment has key configured)
                </span>
              </div>
              <div className="relative">
                <input
                  type={showKey ? "text" : "password"}
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder={
                    provider === "gemini" ? "AIzaSy... (Your Google AI Studio Key)" : "sk-... (Your API Key)"
                  }
                  className="w-full px-3 py-2 pr-10 text-xs rounded-lg border border-border bg-background focus:outline-none focus:ring-1 focus:ring-primary font-mono"
                />
                <button
                  type="button"
                  onClick={() => setShowKey(!showKey)}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  {showKey ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                </button>
              </div>
              <p className="text-[11px] text-muted-foreground">
                Stored strictly in your local browser storage (<span className="font-mono">localStorage</span>). Sent per-request in the <span className="font-mono">x-api-key</span> header. Never saved to backend database or logs.
              </p>
            </div>

            {/* Base URL (for OpenAI compatible) */}
            {provider === "openai" && (
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-foreground">Base URL</label>
                <input
                  type="text"
                  value={baseUrl}
                  onChange={(e) => setBaseUrl(e.target.value)}
                  placeholder="https://api.openai.com/v1 (or https://api.groq.com/openai/v1, http://localhost:11434/v1)"
                  className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-background focus:outline-none focus:ring-1 focus:ring-primary font-mono"
                />
              </div>
            )}

            {/* Model Name */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-foreground">Model Name</label>
              <input
                type="text"
                value={model}
                onChange={(e) => setModel(e.target.value)}
                placeholder={provider === "gemini" ? "gemini-2.5-flash" : "gpt-4o-mini"}
                className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-background focus:outline-none focus:ring-1 focus:ring-primary font-mono"
              />
              <p className="text-[11px] text-muted-foreground">
                {provider === "gemini"
                  ? "Configurable via GEMINI_MODEL env or custom string (e.g. gemini-2.5-flash, gemini-1.5-pro)."
                  : "E.g. gpt-4o-mini, llama-3.3-70b-versatile, mistral-small, etc."}
              </p>
            </div>
          </div>
        )}

        {/* Privacy Callout */}
        <div className="p-3.5 rounded-xl border border-amber-500/20 bg-amber-500/5 text-amber-600 dark:text-amber-400 text-xs flex items-start gap-2.5">
          <AlertTriangle className="h-4 w-4 flex-shrink-0 mt-0.5" />
          <div className="leading-relaxed">
            <span className="font-semibold">Privacy & Non-Sensitive Data Notice:</span> If utilizing third-party free-tier LLM endpoints (e.g. Google AI Studio, Groq Free), prompts may be processed according to the provider’s terms to evaluate or improve products. For sensitive internal financial metrics, use sample data, your verified enterprise API keys, or switch to the Rule-Based Fallback provider.
          </div>
        </div>

        {/* Test Result Callout if available */}
        {testResult && (
          <div
            className={`p-3 rounded-lg text-xs flex items-center gap-2 ${
              testResult.success
                ? "bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400"
                : "bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400"
            }`}
          >
            {testResult.success ? (
              <CheckCircle2 className="h-4 w-4 flex-shrink-0" />
            ) : (
              <AlertTriangle className="h-4 w-4 flex-shrink-0" />
            )}
            <span>{testResult.message}</span>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-border">
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleTestConnection}
              disabled={isTesting}
            >
              {isTesting ? "Testing Connection..." : "Test Connection"}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleResetSettings}
              className="text-muted-foreground hover:text-foreground"
            >
              <RotateCcw className="h-3.5 w-3.5 mr-1.5" />
              Reset Defaults
            </Button>
          </div>

          <Button size="sm" onClick={handleSaveSettings} className="gap-1.5">
            <Save className="h-3.5 w-3.5" />
            Save Settings
          </Button>
        </div>
      </Card>

      {/* Free Hosting Constraints Card */}
      <Card className="p-6 space-y-4">
        <div className="flex items-center gap-2.5 pb-2 border-b border-border">
          <Server className="h-5 w-5 text-primary" />
          <h2 className="text-base font-semibold text-foreground">Free-Host Runtime Architecture</h2>
        </div>

        <p className="text-xs text-muted-foreground leading-relaxed">
          Forecastly is architected to operate efficiently on ephemeral, CPU-only 1–2 GB RAM instances
          (e.g., Render, Railway, Fly.io, Cloud Run) without requiring external message brokers or Redis.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
          <div className="p-4 rounded-xl border border-border bg-secondary/30 space-y-1.5">
            <div className="flex items-center gap-2 font-semibold text-foreground">
              <Cpu className="h-4 w-4 text-indigo-500" />
              <span>CPU & Concurrency Limit</span>
            </div>
            <p className="text-muted-foreground">
              ML thread pools are strictly capped at <span className="font-mono font-medium text-foreground">n_jobs ≤ 2</span> to avoid memory exhaustion on multi-core burst hosts.
            </p>
          </div>

          <div className="p-4 rounded-xl border border-border bg-secondary/30 space-y-1.5">
            <div className="flex items-center gap-2 font-semibold text-foreground">
              <HardDrive className="h-4 w-4 text-emerald-500" />
              <span>Upload Quota</span>
            </div>
            <p className="text-muted-foreground">
              Hard-capped at <span className="font-mono font-medium text-foreground">10 MB / 200,000 rows</span> with SHA-256 fingerprinting and automatic type inference.
            </p>
          </div>

          <div className="p-4 rounded-xl border border-border bg-secondary/30 space-y-1.5">
            <div className="flex items-center gap-2 font-semibold text-foreground">
              <Zap className="h-4 w-4 text-amber-500" />
              <span>In-Process Job Runner</span>
            </div>
            <p className="text-muted-foreground">
              Uses FastAPI <span className="font-mono font-medium text-foreground">BackgroundTasks</span> and SQLite job queue with polling, eliminating Celery/Redis dependencies.
            </p>
          </div>

          <div className="p-4 rounded-xl border border-border bg-secondary/30 space-y-1.5">
            <div className="flex items-center gap-2 font-semibold text-foreground">
              <ShieldCheck className="h-4 w-4 text-violet-500" />
              <span>Ephemeral Disk Recovery</span>
            </div>
            <p className="text-muted-foreground">
              If an instance restarts and disk is wiped, the UI gracefully displays a friendly notice offering instant re-upload or sample data.
            </p>
          </div>
        </div>
      </Card>

      {/* Prophet Optional Status */}
      <Card className="p-6 space-y-3">
        <div className="flex items-center justify-between pb-2 border-b border-border">
          <div className="flex items-center gap-2">
            <Zap className="h-5 w-5 text-amber-500" />
            <h3 className="text-sm font-semibold text-foreground">Prophet Integration Status</h3>
          </div>
          <Badge variant={healthInfo?.prophet_enabled ? "success" : "secondary"} size="sm">
            {healthInfo?.prophet_enabled ? "Enabled" : "Disabled (Default)"}
          </Badge>
        </div>

        <p className="text-xs text-muted-foreground leading-relaxed">
          Prophet relies on Stan/C++ compilation and requires substantial memory during warm starts. It is lazy-loaded and only activated when <span className="font-mono bg-secondary px-1.5 py-0.5 rounded text-foreground">ENABLE_PROPHET=true</span> is present in the deployment environment.
        </p>
      </Card>

      {/* Documentation and OpenAPI */}
      <Card className="p-6 flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-foreground">REST API & Documentation</h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            Interactive OpenAPI Swagger specs and test endpoints under <span className="font-mono">/docs</span>.
          </p>
        </div>

        <a href="/docs" target="_blank" rel="noopener noreferrer">
          <Button variant="outline" size="sm">
            OpenAPI Docs
            <ExternalLink className="h-3.5 w-3.5 ml-1.5" />
          </Button>
        </a>
      </Card>
    </div>
  )
}
