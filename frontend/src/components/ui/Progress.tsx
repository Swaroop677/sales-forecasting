import React from "react"
import { cn } from "@/lib/utils"

export interface ProgressProps {
  value: number // 0 to 100
  className?: string
  indicatorClassName?: string
}

export const Progress: React.FC<ProgressProps> = ({ value, className, indicatorClassName }) => {
  const clamped = Math.max(0, Math.min(100, value))
  return (
    <div
      role="progressbar"
      aria-valuenow={clamped}
      aria-valuemin={0}
      aria-valuemax={100}
      className={cn("relative h-2 w-full overflow-hidden rounded-full bg-secondary", className)}
    >
      <div
        className={cn(
          "h-full w-full flex-1 bg-gradient-to-r from-indigo-500 to-violet-600 transition-all duration-300 ease-out",
          indicatorClassName
        )}
        style={{ transform: `translateX(-${100 - clamped}%)` }}
      />
    </div>
  )
}
