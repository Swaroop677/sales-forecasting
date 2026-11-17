import React, { useEffect, useState } from "react"
import { Keyboard, X } from "lucide-react"
import { Card } from "@/components/ui/Card"

export const ShortcutsModal: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false)

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if typing in input/textarea
      const tag = (e.target as HTMLElement)?.tagName
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return

      if (e.key === "?" && !e.metaKey && !e.ctrlKey) {
        e.preventDefault()
        setIsOpen((prev) => !prev)
      } else if (e.key === "Escape" && isOpen) {
        setIsOpen(false)
      }
    }
    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [isOpen])

  if (!isOpen) return null

  const shortcuts = [
    { key: "⌘ K / Ctrl+K", desc: "Toggle AI Forecasting Copilot drawer" },
    { key: "?", desc: "Show keyboard shortcuts reference" },
    { key: "Esc", desc: "Close drawers, modals, and dialogs" },
    { key: "Tab", desc: "Accessible keyboard navigation focus" },
  ]

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 animate-in fade-in duration-150">
      <Card className="w-full max-w-md p-6 space-y-4 shadow-2xl border-border bg-card">
        <div className="flex items-center justify-between pb-3 border-b border-border">
          <div className="flex items-center gap-2">
            <Keyboard className="h-4 w-4 text-primary" />
            <h3 className="text-sm font-semibold text-foreground">Keyboard Shortcuts</h3>
          </div>
          <button
            onClick={() => setIsOpen(false)}
            className="text-muted-foreground hover:text-foreground p-1 rounded-lg"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-2.5 text-xs">
          {shortcuts.map((s, idx) => (
            <div key={idx} className="flex items-center justify-between py-1.5 border-b border-border/40">
              <span className="text-muted-foreground">{s.desc}</span>
              <kbd className="px-2 py-1 rounded bg-secondary font-mono text-[11px] font-semibold text-foreground border border-border">
                {s.key}
              </kbd>
            </div>
          ))}
        </div>

        <div className="pt-2 text-center text-[11px] text-muted-foreground">
          Press <kbd className="px-1.5 py-0.5 rounded bg-secondary font-mono text-[10px]">Esc</kbd> or click outside to dismiss.
        </div>
      </Card>
    </div>
  )
}
