import React from "react"
import { NavLink } from "react-router-dom"
import {
  BarChart3,
  Bot,
  Database,
  History,
  LayoutDashboard,
  Settings,
  Sparkles,
} from "lucide-react"
import { cn } from "@/lib/utils"

interface SidebarProps {
  collapsed: boolean
  setCollapsed: (val: boolean) => void
}

export const Sidebar: React.FC<SidebarProps> = ({ collapsed, setCollapsed }) => {
  const navItems = [
    { to: "/", label: "Overview", icon: LayoutDashboard },
    { to: "/agent", label: "AI Copilot", icon: Bot },
    { to: "/data", label: "Data Quality", icon: Database },
    { to: "/forecast", label: "Forecast Studio", icon: BarChart3 },
    { to: "/runs", label: "Model Registry", icon: History },
    { to: "/settings", label: "Settings", icon: Settings },
  ]

  return (
    <aside
      className={cn(
        "h-screen border-r border-border bg-card flex flex-col justify-between transition-all duration-200 z-40 select-none",
        collapsed ? "w-16" : "w-64"
      )}
    >
      <div>
        {/* Brand */}
        <div className="h-16 flex items-center px-4 border-b border-border justify-between">
          <NavLink to="/" className="flex items-center gap-2.5 overflow-hidden">
            <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center text-white shadow-sm flex-shrink-0">
              <Sparkles className="h-5 w-5" />
            </div>
            {!collapsed && (
              <div className="flex flex-col">
                <span className="font-semibold text-sm tracking-tight text-foreground">Forecastly</span>
                <span className="text-[10px] text-muted-foreground uppercase tracking-widest font-mono">Phase 2 AI</span>
              </div>
            )}
          </NavLink>
        </div>

        {/* Navigation Links */}
        <nav className="p-3 space-y-1.5">
          {navItems.map((item) => {
            const Icon = item.icon
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors",
                    isActive
                      ? "bg-primary text-primary-foreground shadow-sm"
                      : "text-muted-foreground hover:bg-secondary hover:text-foreground"
                  )
                }
                title={collapsed ? item.label : undefined}
              >
                <Icon className="h-4 w-4 flex-shrink-0" />
                {!collapsed && <span>{item.label}</span>}
              </NavLink>
            )
          })}
        </nav>
      </div>

      {/* Collapse Toggle */}
      <div className="p-3 border-t border-border">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="w-full py-2 px-3 flex items-center justify-center rounded-xl text-xs text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
        >
          {collapsed ? "→" : "← Collapse"}
        </button>
      </div>
    </aside>
  )
}
