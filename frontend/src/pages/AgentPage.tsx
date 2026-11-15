import React, { useEffect, useRef, useState } from "react"
import {
  Bot,
  Check,
  Copy,
  MessageSquare,
  Plus,
  Send,
  ShieldCheck,
  StopCircle,
  Trash2,
} from "lucide-react"
import { toast } from "sonner"
import { api } from "@/api/client"
import { ChatTimeline } from "@/components/agent/ChatTimeline"
import { MiniChart } from "@/components/agent/MiniChart"
import { Badge } from "@/components/ui/Badge"
import { Button } from "@/components/ui/Button"
import { Card } from "@/components/ui/Card"
import { cn } from "@/lib/utils"
import {
  ChatMessage,
  ChatSession,
  Dataset,
  GroundingInfo,
  LLMSettings,
  RunResult,
  ToolCallItem,
} from "@/types"

interface AgentPageProps {
  currentDataset: Dataset | null
  activeRun: RunResult | null
}

const AGENT_SUGGESTIONS = [
  "Forecast the next 8 weeks",
  "Why did sales dip in March?",
  "What if I run a 20% promo next month?",
  "Which products need attention?",
  "Compare last 4 weeks vs prior 4 weeks",
  "Show me the model leaderboard",
]

export const AgentPage: React.FC<AgentPageProps> = ({ currentDataset, activeRun }) => {
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "agent-welcome",
      role: "assistant",
      content:
        "Welcome to **Forecastly AI Agent**!\n\nI am your conversational sales forecasting assistant. Every metric, percentage, and date I cite is grounded in deterministic pipeline computations with zero hallucination.\n\nChoose an action below or ask any question about your data:",
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
    scrollToBottom()
  }, [messages, isStreaming])

  // Load chat sessions on mount
  useEffect(() => {
    api
      .listChatSessions()
      .then(setSessions)
      .catch(() => {})
  }, [])

  const handleSelectSession = async (sId: string) => {
    try {
      const sess = await api.getChatSession(sId)
      setCurrentSessionId(sess.id)
      if (sess.messages && sess.messages.length > 0) {
        setMessages(sess.messages)
      }
    } catch (e: any) {
      toast.error(e.message || "Failed to load session")
    }
  }

  const handleNewSession = () => {
    setCurrentSessionId(null)
    setMessages([
      {
        id: `welcome-${Date.now()}`,
        role: "assistant",
        content:
          "Starting a fresh conversation. How would you like to explore your sales forecasting pipeline?",
      },
    ])
  }

  const handleDeleteSession = async (e: React.MouseEvent, sId: string) => {
    e.stopPropagation()
    try {
      await api.deleteChatSession(sId)
      setSessions((prev) => prev.filter((s) => s.id !== sId))
      if (currentSessionId === sId) {
        handleNewSession()
      }
      toast.success("Deleted session")
    } catch (e: any) {
      toast.error(e.message || "Failed to delete session")
    }
  }

  const handleSendMessage = async (queryText?: string) => {
    const query = (queryText || input).trim()
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
          session_id: currentSessionId,
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
          } else if (eventType === "done" && dataStr) {
            try {
              const doneData = JSON.parse(dataStr)
              if (doneData.session_id) {
                setCurrentSessionId(doneData.session_id)
                api.listChatSessions().then(setSessions).catch(() => {})
              }
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
      if (e.name !== "AbortError") {
        toast.error(e.message || "Chat generation error")
      }
    } finally {
      setIsStreaming(false)
      abortControllerRef.current = null
    }
  }

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text)
    setCopiedId(id)
    toast.success("Copied to clipboard")
    setTimeout(() => setCopiedId(null), 2000)
  }

  return (
    <div className="h-[calc(100vh-8rem)] flex gap-6 animate-in fade-in duration-200">
      {/* Session History Sidebar */}
      <Card className="w-64 p-4 flex flex-col justify-between hidden md:flex border-border/80">
        <div className="space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-border">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Conversations
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={handleNewSession}
              className="h-7 px-2 text-xs"
            >
              <Plus className="h-3.5 w-3.5 mr-1" />
              New
            </Button>
          </div>

          <div className="space-y-1 overflow-y-auto max-h-[60vh]">
            {sessions.map((s) => (
              <div
                key={s.id}
                onClick={() => handleSelectSession(s.id)}
                className={cn(
                  "p-2.5 rounded-xl cursor-pointer text-xs flex items-center justify-between group transition-colors",
                  currentSessionId === s.id
                    ? "bg-primary text-primary-foreground font-medium"
                    : "hover:bg-secondary text-muted-foreground hover:text-foreground"
                )}
              >
                <div className="flex items-center gap-2 truncate">
                  <MessageSquare className="h-3.5 w-3.5 flex-shrink-0" />
                  <span className="truncate">{s.title || "Session"}</span>
                </div>
                <button
                  onClick={(e) => handleDeleteSession(e, s.id)}
                  className="opacity-0 group-hover:opacity-100 p-1 hover:text-rose-500 transition-opacity"
                >
                  <Trash2 className="h-3 w-3" />
                </button>
              </div>
            ))}
          </div>
        </div>

        <div className="pt-3 border-t border-border text-[11px] text-muted-foreground flex items-center gap-2">
          <ShieldCheck className="h-4 w-4 text-emerald-500" />
          <span>Deterministic Tool Grounding</span>
        </div>
      </Card>

      {/* Main Chat Interface */}
      <Card className="flex-1 p-0 flex flex-col justify-between overflow-hidden border-border/80 shadow-md">
        {/* Top Chat Bar */}
        <div className="h-14 px-6 border-b border-border flex items-center justify-between bg-card/60 backdrop-blur-md">
          <div className="flex items-center gap-3">
            <div className="h-7 w-7 rounded-lg bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center text-white shadow-sm">
              <Bot className="h-4 w-4" />
            </div>
            <div>
              <span className="text-xs font-semibold text-foreground">Forecastly Copilot</span>
              <span className="text-[10px] text-muted-foreground block">
                Active: {currentDataset ? currentDataset.name : "Sample Dataset"}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Badge variant="indigo" size="sm">
              <ShieldCheck className="h-3 w-3 mr-1 inline text-indigo-500" />
              100% Grounded
            </Badge>
          </div>
        </div>

        {/* Message Feed */}
        <div className="flex-1 overflow-y-auto p-6 space-y-5">
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
                    "rounded-2xl p-4 text-xs max-w-[85%] leading-relaxed space-y-2.5 shadow-sm transition-all",
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
                  <div className="whitespace-pre-wrap font-sans text-xs">
                    {m.content || (m.isStreaming && (
                      <span className="inline-flex items-center gap-1.5 text-muted-foreground">
                        <span className="h-2 w-2 rounded-full bg-primary animate-ping" />
                        Executing tools and computing factual results...
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
        <div className="px-6 py-2 border-t border-border/40 bg-card/60 flex items-center gap-2 overflow-x-auto no-scrollbar">
          {AGENT_SUGGESTIONS.map((chip, i) => (
            <button
              key={i}
              onClick={() => handleSendMessage(chip)}
              disabled={isStreaming}
              className="whitespace-nowrap px-3 py-1 rounded-full text-xs bg-secondary hover:bg-secondary/80 border border-border/60 text-muted-foreground hover:text-foreground transition-all flex-shrink-0 disabled:opacity-50"
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
              placeholder="Ask anything about sales demand, what-if scenarios, or data anomalies..."
              rows={2}
              disabled={isStreaming}
              className="w-full resize-none rounded-xl border border-border bg-secondary/30 px-4 py-3 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50 pr-24"
            />

            <div className="absolute right-3 bottom-4 flex items-center gap-2">
              {isStreaming ? (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => abortControllerRef.current?.abort()}
                  className="h-8 px-2.5 text-rose-500 border-rose-500/30"
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
                  className="h-8 px-3 rounded-xl gap-1.5"
                >
                  <span>Send</span>
                  <Send className="h-3.5 w-3.5" />
                </Button>
              )}
            </div>
          </form>
        </div>
      </Card>
    </div>
  )
}
