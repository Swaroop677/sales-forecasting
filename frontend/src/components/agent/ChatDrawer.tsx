import React, { useEffect, useRef, useState } from "react"
import {
  Bot,
  Check,
  Copy,
  CornerDownLeft,
  ShieldCheck,
  StopCircle,
  X,
} from "lucide-react"
import { toast } from "sonner"
import { ChatTimeline } from "@/components/agent/ChatTimeline"
import { MiniChart } from "@/components/agent/MiniChart"
import { Badge } from "@/components/ui/Badge"
import { Button } from "@/components/ui/Button"
import { cn } from "@/lib/utils"
import { ChatMessage, Dataset, GroundingInfo, LLMSettings, RunResult, ToolCallItem } from "@/types"

interface ChatDrawerProps {
  isOpen: boolean
  onClose: () => void
  currentDataset: Dataset | null
  activeRun: RunResult | null
}

const DEFAULT_SUGGESTIONS = [
  "Forecast the next 8 weeks",
  "Why did sales dip in March?",
  "What if I run a 20% promo next month?",
  "Which products need attention?",
]

export const ChatDrawer: React.FC<ChatDrawerProps> = ({
  isOpen,
  onClose,
  currentDataset,
  activeRun,
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome-msg",
      role: "assistant",
      content:
        "Hello! I am **Forecastly AI**, your sales forecasting copilot. Every figure I state is strictly verified from deterministic pipeline calculations.\n\nHow can I help you analyze or forecast your sales today?",
    },
  ])
  const [input, setInput] = useState("")
  const [isStreaming, setIsStreaming] = useState(false)
  const [copiedId, setCopiedId] = useState<string | null>(null)

  const abortControllerRef = useRef<AbortController | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    if (isOpen) {
      scrollToBottom()
    }
  }, [isOpen, messages, isStreaming])

  // Handle Cmd+K / Ctrl+K global shortcut
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault()
        if (isOpen) onClose()
        else {
          // Open drawer
          const event = new CustomEvent("open-forecastly-chat")
          window.dispatchEvent(event)
        }
      }
    }
    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [isOpen, onClose])

  const handleSendMessage = async (textToSend?: string) => {
    const query = (textToSend || input).trim()
    if (!query || isStreaming) return

    setInput("")

    const userMessageId = `user-${Date.now()}`
    const assistantMessageId = `asst-${Date.now()}`

    const userMsg: ChatMessage = {
      id: userMessageId,
      role: "user",
      content: query,
    }

    const placeholderAssistantMsg: ChatMessage = {
      id: assistantMessageId,
      role: "assistant",
      content: "",
      tool_calls: [],
      chart_spec: null,
      grounding_info: null,
      isStreaming: true,
    }

    setMessages((prev) => [...prev, userMsg, placeholderAssistantMsg])
    setIsStreaming(true)

    // Retrieve BYOK settings from localStorage
    let llmSettings: LLMSettings = {
      provider: "fallback",
      apiKey: "",
      baseUrl: "",
      model: "",
    }
    try {
      const stored = localStorage.getItem("forecastly_llm_settings")
      if (stored) {
        llmSettings = JSON.parse(stored)
      }
    } catch {}

    const controller = new AbortController()
    abortControllerRef.current = controller

    try {
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      }
      if (llmSettings.provider) headers["X-LLM-Provider"] = llmSettings.provider
      if (llmSettings.apiKey) headers["X-LLM-API-Key"] = llmSettings.apiKey
      if (llmSettings.baseUrl) headers["X-LLM-Base-URL"] = llmSettings.baseUrl
      if (llmSettings.model) headers["X-LLM-Model"] = llmSettings.model

      const response = await fetch("/api/agent/chat", {
        method: "POST",
        headers,
        signal: controller.signal,
        body: JSON.stringify({
          message: query,
          dataset_id: currentDataset?.id || null,
          run_id: activeRun?.id || null,
          provider: llmSettings.provider,
          api_key: llmSettings.apiKey,
          base_url: llmSettings.baseUrl,
          model: llmSettings.model,
        }),
      })

      if (!response.ok) {
        let errText = "Failed to communicate with AI agent."
        try {
          const errJson = await response.json()
          errText = errJson.detail || errText
        } catch {
          errText = await response.text()
        }
        throw new Error(errText)
      }

      const reader = response.body?.getReader()
      if (!reader) throw new Error("No readable stream response")

      const decoder = new TextDecoder()
      let accumulatedContent = ""
      const accumulatedTools: ToolCallItem[] = []
      let capturedChart: Record<string, any> | null = null
      let capturedGrounding: GroundingInfo | null = null

      let buffer = ""

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const chunks = buffer.split("\n\n")
        buffer = chunks.pop() || ""

        for (const chunk of chunks) {
          const lines = chunk.trim().split("\n")
          let eventType = ""
          let dataStr = ""

          for (const line of lines) {
            if (line.startsWith("event:")) {
              eventType = line.replace("event:", "").trim()
            } else if (line.startsWith("data:")) {
              dataStr = line.replace("data:", "").trim()
            }
          }

          if (eventType === "token" && dataStr) {
            try {
              const data = JSON.parse(dataStr)
              accumulatedContent += data.content || ""
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantMessageId
                    ? { ...msg, content: accumulatedContent }
                    : msg
                )
              )
            } catch {}
          } else if (eventType === "tool_start" && dataStr) {
            try {
              const data = JSON.parse(dataStr)
              accumulatedTools.push({ name: data.name, args: data.args || {} })
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantMessageId
                    ? { ...msg, tool_calls: [...accumulatedTools] }
                    : msg
                )
              )
            } catch {}
          } else if (eventType === "chart" && dataStr) {
            try {
              capturedChart = JSON.parse(dataStr)
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantMessageId
                    ? { ...msg, chart_spec: capturedChart }
                    : msg
                )
              )
            } catch {}
          } else if (eventType === "grounding" && dataStr) {
            try {
              capturedGrounding = JSON.parse(dataStr)
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantMessageId
                    ? { ...msg, grounding_info: capturedGrounding }
                    : msg
                )
              )
            } catch {}
          } else if (eventType === "error" && dataStr) {
            try {
              const err = JSON.parse(dataStr)
              toast.error(err.message || "Agent encountered an error")
            } catch {}
          }
        }
      }

      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMessageId
            ? {
                ...msg,
                isStreaming: false,
                content: accumulatedContent,
                tool_calls: accumulatedTools,
                chart_spec: capturedChart,
                grounding_info: capturedGrounding,
              }
            : msg
        )
      )
    } catch (e: any) {
      if (e.name === "AbortError") {
        toast.info("Generation stopped.")
      } else {
        toast.error(e.message || "Error during chat generation")
      }
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMessageId ? { ...msg, isStreaming: false } : msg
        )
      )
    } finally {
      setIsStreaming(false)
      abortControllerRef.current = null
    }
  }

  const handleStopGeneration = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
  }

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text)
    setCopiedId(id)
    toast.success("Copied to clipboard")
    setTimeout(() => setCopiedId(null), 2000)
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 overflow-hidden pointer-events-none">
      {/* Dimmed backdrop */}
      <div
        className="fixed inset-0 bg-black/40 backdrop-blur-sm transition-opacity pointer-events-auto animate-in fade-in"
        onClick={onClose}
      />

      {/* Slide-over Panel */}
      <div className="fixed inset-y-0 right-0 max-w-full flex pl-10 pointer-events-auto">
        <div className="w-screen max-w-md sm:max-w-lg bg-card border-l border-border shadow-2xl flex flex-col justify-between animate-in slide-in-from-right duration-250">
          {/* Header */}
          <div className="h-16 px-5 border-b border-border flex items-center justify-between bg-card/80 backdrop-blur-md sticky top-0 z-10">
            <div className="flex items-center gap-2.5">
              <div className="h-8 w-8 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center text-white shadow-sm">
                <Bot className="h-4 w-4" />
              </div>
              <div>
                <div className="flex items-center gap-1.5">
                  <h3 className="font-semibold text-sm text-foreground">Forecastly Agent</h3>
                  <Badge variant="indigo" size="sm">
                    Verified
                  </Badge>
                </div>
                <p className="text-[10px] text-muted-foreground">
                  Grounded conversational forecasting copilot
                </p>
              </div>
            </div>

            <div className="flex items-center gap-1">
              <span className="text-[10px] text-muted-foreground font-mono bg-secondary px-1.5 py-0.5 rounded border border-border/60 mr-2 hidden sm:inline">
                ⌘K
              </span>
              <button
                onClick={onClose}
                className="p-1.5 rounded-lg text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>

          {/* Message List */}
          <div className="flex-1 overflow-y-auto p-5 space-y-4">
            {messages.map((m) => {
              const isUser = m.role === "user"
              return (
                <div
                  key={m.id}
                  className={cn(
                    "flex flex-col group",
                    isUser ? "items-end" : "items-start"
                  )}
                >
                  <div
                    className={cn(
                      "rounded-2xl p-4 text-xs max-w-[92%] leading-relaxed space-y-2 shadow-sm transition-all",
                      isUser
                        ? "bg-primary text-primary-foreground rounded-br-sm"
                        : "bg-secondary/40 text-foreground border border-border/80 rounded-bl-sm"
                    )}
                  >
                    {/* Collapsible Timeline of Tool Calls */}
                    {m.tool_calls && m.tool_calls.length > 0 && (
                      <ChatTimeline toolCalls={m.tool_calls} defaultOpen={false} />
                    )}

                    {/* Formatted Markdown Content */}
                    <div className="whitespace-pre-wrap font-sans">
                      {m.content || (m.isStreaming && (
                        <span className="inline-flex items-center gap-1 text-muted-foreground">
                          <span className="h-1.5 w-1.5 rounded-full bg-primary animate-ping" />
                          Thinking & computing figures...
                        </span>
                      ))}
                    </div>

                    {/* Inline Mini Chart */}
                    {m.chart_spec && <MiniChart spec={m.chart_spec} />}

                    {/* Grounding Status Pill */}
                    {!isUser && m.grounding_info && (
                      <div className="pt-2 border-t border-border/40 flex items-center justify-between text-[10px] text-muted-foreground">
                        <div className="flex items-center gap-1">
                          <ShieldCheck
                            className={cn(
                              "h-3 w-3",
                              m.grounding_info.verified ? "text-emerald-500" : "text-amber-500"
                            )}
                          />
                          <span
                            className={
                              m.grounding_info.verified
                                ? "text-emerald-600 dark:text-emerald-400 font-medium"
                                : "text-amber-600 dark:text-amber-400"
                            }
                          >
                            {m.grounding_info.badge_label}
                          </span>
                        </div>
                        <span className="italic opacity-70">
                          {m.grounding_info.disclaimer}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Message actions (copy) */}
                  {!isUser && m.content && (
                    <div className="flex items-center gap-1 mt-1 px-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button
                        onClick={() => handleCopy(m.id, m.content)}
                        className="text-[11px] text-muted-foreground hover:text-foreground p-1 rounded flex items-center gap-1"
                      >
                        {copiedId === m.id ? (
                          <Check className="h-3 w-3 text-emerald-500" />
                        ) : (
                          <Copy className="h-3 w-3" />
                        )}
                        <span>{copiedId === m.id ? "Copied" : "Copy"}</span>
                      </button>
                    </div>
                  )}
                </div>
              )
            })}
            <div ref={messagesEndRef} />
          </div>

          {/* Suggestion Chips */}
          <div className="px-5 py-2 border-t border-border/40 bg-card/60 flex items-center gap-1.5 overflow-x-auto no-scrollbar">
            {DEFAULT_SUGGESTIONS.map((chip, i) => (
              <button
                key={i}
                onClick={() => handleSendMessage(chip)}
                disabled={isStreaming}
                className="whitespace-nowrap px-2.5 py-1 rounded-full text-[11px] bg-secondary hover:bg-secondary/80 border border-border/60 text-muted-foreground hover:text-foreground transition-all flex-shrink-0 disabled:opacity-50"
              >
                {chip}
              </button>
            ))}
          </div>

          {/* Input Box */}
          <div className="p-4 border-t border-border bg-card">
            <form
              onSubmit={(e) => {
                e.preventDefault()
                handleSendMessage()
              }}
              className="relative"
            >
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault()
                    handleSendMessage()
                  }
                }}
                placeholder={
                  currentDataset
                    ? `Ask about ${currentDataset.name}...`
                    : "Ask anything about sales forecasting..."
                }
                rows={2}
                disabled={isStreaming}
                className="w-full resize-none rounded-xl border border-border bg-secondary/30 px-3.5 py-2.5 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50 pr-20"
              />

              <div className="absolute right-2.5 bottom-3.5 flex items-center gap-1.5">
                {isStreaming ? (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleStopGeneration}
                    className="h-7 px-2 text-rose-500 hover:text-rose-600 border-rose-500/30"
                  >
                    <StopCircle className="h-3.5 w-3.5 mr-1" />
                    Stop
                  </Button>
                ) : (
                  <Button
                    type="submit"
                    variant="primary"
                    size="sm"
                    disabled={!input.trim()}
                    className="h-7 w-7 p-0 rounded-lg"
                  >
                    <CornerDownLeft className="h-3.5 w-3.5" />
                  </Button>
                )}
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}
