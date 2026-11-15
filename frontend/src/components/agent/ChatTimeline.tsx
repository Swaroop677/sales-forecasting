import React, { useState } from "react"
import {
  Activity,
  AlertTriangle,
  BarChart2,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Cpu,
  Database,
  Search,
  Sparkles,
  TrendingUp,
  Wand2,
} from "lucide-react"
import { Badge } from "@/components/ui/Badge"
import { ToolCallItem } from "@/types"

interface ChatTimelineProps {
  toolCalls: ToolCallItem[]
  defaultOpen?: boolean
}

const TOOL_ICONS: Record<string, React.ElementType> = {
  profile_dataset: Database,
  validate_data: CheckCircle2,
  clean_data: Wand2,
  run_forecast: Cpu,
  get_leaderboard: BarChart2,
  get_forecast: TrendingUp,
  compare_periods: Activity,
  find_anomalies: AlertTriangle,
  top_movers: TrendingUp,
  what_if: Sparkles,
  executive_summary: Search,
}

const TOOL_LABELS: Record<string, string> = {
  profile_dataset: "Profiled Dataset Health",
  validate_data: "Validated Model Prerequisites",
  clean_data: "Sanitized & Cleaned Timeline",
  run_forecast: "Trained & Backtested Models",
  get_leaderboard: "Evaluated Out-of-Sample Leaderboard",
  get_forecast: "Retrieved Multi-Step Forecast",
  compare_periods: "Compared Historical Periods",
  find_anomalies: "Audited Historical Anomalies",
  top_movers: "Calculated Top Volume Movers",
  what_if: "Simulated Scenario Impact",
  executive_summary: "Generated Executive Facts",
}

export const ChatTimeline: React.FC<ChatTimelineProps> = ({
  toolCalls,
  defaultOpen = false,
}) => {
  const [isOpen, setIsOpen] = useState(defaultOpen)

  if (!toolCalls || toolCalls.length === 0) return null

  return (
    <div className="rounded-xl border border-border/80 bg-secondary/40 overflow-hidden my-2.5 text-xs">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-3 py-2 flex items-center justify-between text-muted-foreground hover:text-foreground hover:bg-secondary/60 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse" />
          <span className="font-semibold text-foreground">
            What I Did ({toolCalls.length} step{toolCalls.length > 1 ? "s" : ""})
          </span>
          <span className="text-[11px] text-muted-foreground hidden sm:inline">
            {toolCalls.map((t) => TOOL_LABELS[t.name] || t.name).join(" → ")}
          </span>
        </div>
        {isOpen ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
      </button>

      {isOpen && (
        <div className="p-3 border-t border-border/60 space-y-2 bg-card/60">
          {toolCalls.map((tc, idx) => {
            const Icon = TOOL_ICONS[tc.name] || Cpu
            const label = TOOL_LABELS[tc.name] || tc.name
            return (
              <div
                key={idx}
                className="flex items-start gap-2.5 p-2 rounded-lg bg-secondary/30 border border-border/40"
              >
                <div className="h-6 w-6 rounded-md bg-primary/10 text-primary flex items-center justify-center flex-shrink-0 mt-0.5">
                  <Icon className="h-3.5 w-3.5" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium text-foreground">{label}</span>
                    <Badge variant="outline" size="sm">
                      Step {idx + 1}
                    </Badge>
                  </div>
                  {tc.args && Object.keys(tc.args).length > 0 && (
                    <div className="text-[10px] text-muted-foreground font-mono mt-0.5 truncate">
                      args: {JSON.stringify(tc.args)}
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
