import React from "react"
import { Moon, Sun } from "lucide-react"
import { Badge } from "@/components/ui/Badge"
import { Dataset } from "@/types"

interface HeaderProps {
  currentDataset: Dataset | null
  darkMode: boolean
  setDarkMode: (val: boolean) => void
}

export const Header: React.FC<HeaderProps> = ({ currentDataset, darkMode, setDarkMode }) => {
  return (
    <header className="h-16 border-b border-border bg-card/60 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-30">
      <div className="flex items-center gap-3">
        {currentDataset ? (
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground font-medium uppercase tracking-wider">Active Data:</span>
            <span className="text-sm font-medium text-foreground max-w-[200px] truncate sm:max-w-xs">
              {currentDataset.name}
            </span>
            <Badge variant="secondary" size="sm">
              {currentDataset.row_count.toLocaleString()} rows
            </Badge>
          </div>
        ) : (
          <span className="text-sm text-muted-foreground">No active dataset selected</span>
        )}
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={() => setDarkMode(!darkMode)}
          aria-label="Toggle color theme"
          className="p-2 rounded-xl text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
        >
          {darkMode ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </button>
      </div>
    </header>
  )
}
