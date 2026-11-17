import React, { useEffect, useState } from "react"
import {
  ArrowRight,
  BarChart3,
  Bot,
  Check,
  Sparkles,
  X,
} from "lucide-react"
import { Button } from "@/components/ui/Button"
import { Card } from "@/components/ui/Card"

export const OnboardingTour: React.FC = () => {
  const [isVisible, setIsVisible] = useState(false)
  const [step, setStep] = useState(0)

  useEffect(() => {
    const hasSeen = localStorage.getItem("forecastly_onboarding_completed")
    if (!hasSeen) {
      setIsVisible(true)
    }
  }, [])

  const handleDismiss = () => {
    localStorage.setItem("forecastly_onboarding_completed", "true")
    setIsVisible(false)
  }

  if (!isVisible) return null

  const steps = [
    {
      title: "Welcome to Forecastly",
      icon: Sparkles,
      desc: "Automated sales forecasting for retail and operations. Start by clicking 'Try sample data' or uploading your sales CSV.",
    },
    {
      title: "Zero-Leakage Backtesting",
      icon: BarChart3,
      desc: "Forecastly evaluates Seasonal Naive, Holt-Winters, LightGBM, and XGBoost across expanding backtest folds and picks the best model by out-of-sample WAPE.",
    },
    {
      title: "AI Forecasting Copilot",
      icon: Bot,
      desc: "Press ⌘K or click 'Ask AI' anytime. Ask questions, simulate what-if pricing scenarios, or inspect statistical safety stocks.",
    },
  ]

  const current = steps[step]
  const Icon = current.icon

  return (
    <div className="fixed bottom-20 left-6 z-40 max-w-sm animate-in slide-in-from-bottom-4 duration-300">
      <Card className="p-4 space-y-3 shadow-2xl border-primary/20 bg-card/95 backdrop-blur-md">
        <div className="flex items-center justify-between pb-2 border-b border-border">
          <div className="flex items-center gap-2">
            <div className="h-6 w-6 rounded-md bg-primary/10 flex items-center justify-center text-primary">
              <Icon className="h-3.5 w-3.5" />
            </div>
            <span className="text-xs font-semibold text-foreground">{current.title}</span>
          </div>
          <button onClick={handleDismiss} className="text-muted-foreground hover:text-foreground">
            <X className="h-3.5 w-3.5" />
          </button>
        </div>

        <p className="text-xs text-muted-foreground leading-relaxed">{current.desc}</p>

        <div className="flex items-center justify-between pt-2">
          <div className="flex gap-1">
            {steps.map((_, i) => (
              <span
                key={i}
                className={`h-1.5 rounded-full transition-all ${
                  step === i ? "w-4 bg-primary" : "w-1.5 bg-secondary"
                }`}
              />
            ))}
          </div>

          <div className="flex items-center gap-1.5">
            {step < steps.length - 1 ? (
              <Button
                size="sm"
                variant="outline"
                onClick={() => setStep((s) => s + 1)}
                className="h-7 text-xs gap-1"
              >
                <span>Next</span>
                <ArrowRight className="h-3 w-3" />
              </Button>
            ) : (
              <Button size="sm" onClick={handleDismiss} className="h-7 text-xs gap-1">
                <span>Get Started</span>
                <Check className="h-3 w-3" />
              </Button>
            )}
          </div>
        </div>
      </Card>
    </div>
  )
}
