import React, { useEffect, useState } from "react"
import {
  Cpu,
  ExternalLink,
  HardDrive,
  Server,
  ShieldCheck,
  Zap,
} from "lucide-react"
import { Badge } from "@/components/ui/Badge"
import { Button } from "@/components/ui/Button"
import { Card } from "@/components/ui/Card"

export const SettingsPage: React.FC = () => {
  const [healthInfo, setHealthInfo] = useState<any>(null)

  useEffect(() => {
    fetch("/api/health")
      .then((res) => res.json())
      .then(setHealthInfo)
      .catch(() => {})
  }, [])

  return (
    <div className="space-y-8 animate-in fade-in duration-200 max-w-4xl">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">System & Hosting Settings</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Runtime specifications, free-tier hosting limits, and Phase 1 architecture details.
        </p>
      </div>

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
