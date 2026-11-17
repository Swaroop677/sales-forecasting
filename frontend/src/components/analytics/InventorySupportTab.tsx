import React, { useEffect, useState } from "react"
import {
  AlertTriangle,
  CheckCircle2,
  Download,
  Info,
  RefreshCw,
  Truck,
} from "lucide-react"
import { api } from "@/api/client"
import { Badge } from "@/components/ui/Badge"
import { Button } from "@/components/ui/Button"
import { Card } from "@/components/ui/Card"
import { formatNumber } from "@/lib/utils"
import { InventorySupportResponse, RunResult } from "@/types"

interface InventorySupportTabProps {
  activeRun: RunResult
}

export const InventorySupportTab: React.FC<InventorySupportTabProps> = ({ activeRun }) => {
  const [data, setData] = useState<InventorySupportResponse | null>(null)
  const [leadTime, setLeadTime] = useState(7)
  const [serviceLevel, setServiceLevel] = useState("95%")
  const [currentStock, setCurrentStock] = useState(300)

  const fetchInventory = () => {
    if (!activeRun.id) return
    api
      .getInventorySupport(activeRun.id, leadTime, serviceLevel, currentStock)
      .then(setData)
      .catch(() => {})
  }

  useEffect(() => {
    fetchInventory()
  }, [activeRun.id, leadTime, serviceLevel])

  return (
    <div className="space-y-6">
      {/* Disclaimer Callout */}
      <div className="p-3.5 rounded-xl border border-border bg-secondary/30 text-xs text-muted-foreground leading-relaxed flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Info className="h-4 w-4 text-primary flex-shrink-0" />
          <span>
            <strong className="text-foreground">Statistical Decision Support:</strong> Calculations use forecast error variance $\sigma_e$ and Poisson/normal lead-time demand. This is decision support, not financial or trading advice.
          </span>
        </div>
        <a
          href={api.getInventoryExportUrl(activeRun.id, leadTime, serviceLevel, currentStock)}
          target="_blank"
          rel="noopener noreferrer"
        >
          <Button variant="outline" size="sm" className="gap-1.5 text-xs h-8">
            <Download className="h-3.5 w-3.5" />
            CSV
          </Button>
        </a>
      </div>

      {/* Input Parameter Controls */}
      <Card className="p-4 bg-card/60 space-y-4">
        <div className="flex items-center justify-between border-b border-border pb-2">
          <h4 className="text-xs font-semibold text-foreground flex items-center gap-1.5">
            <Truck className="h-4 w-4 text-primary" />
            <span>Supply Chain Assumptions</span>
          </h4>
          <Button variant="ghost" size="sm" onClick={fetchInventory} className="h-7 text-xs">
            <RefreshCw className="h-3 w-3 mr-1" />
            Recalculate
          </Button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
          <div>
            <label className="text-muted-foreground block mb-1">Lead Time (Days)</label>
            <div className="flex gap-2">
              {[7, 14, 30].map((lt) => (
                <button
                  key={lt}
                  type="button"
                  onClick={() => setLeadTime(lt)}
                  className={`px-3 py-1.5 rounded-lg border text-xs font-mono transition-all ${
                    leadTime === lt
                      ? "border-primary bg-primary/10 text-primary font-semibold"
                      : "border-border hover:bg-secondary text-muted-foreground"
                  }`}
                >
                  {lt}d
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="text-muted-foreground block mb-1">Target Service Level</label>
            <div className="flex gap-2">
              {["90%", "95%", "99%"].map((sl) => (
                <button
                  key={sl}
                  type="button"
                  onClick={() => setServiceLevel(sl)}
                  className={`px-3 py-1.5 rounded-lg border text-xs font-mono transition-all ${
                    serviceLevel === sl
                      ? "border-primary bg-primary/10 text-primary font-semibold"
                      : "border-border hover:bg-secondary text-muted-foreground"
                  }`}
                >
                  {sl}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="text-muted-foreground block mb-1">Current On-Hand Stock</label>
            <input
              type="number"
              value={currentStock}
              onChange={(e) => setCurrentStock(Math.max(0, parseInt(e.target.value) || 0))}
              className="w-full text-xs bg-background border border-border rounded-lg px-3 py-1.5 text-foreground font-mono"
            />
          </div>
        </div>
      </Card>

      {/* Decision Support Cards */}
      {data && (
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 text-xs">
          <Card className="p-4 space-y-1">
            <div className="text-muted-foreground">Inventory Status</div>
            <div className="pt-1">
              <Badge
                variant={
                  data.status === "Reorder now"
                    ? "danger"
                    : data.status === "Overstock risk"
                    ? "warning"
                    : "success"
                }
                size="md"
              >
                {data.status === "Reorder now" && <AlertTriangle className="h-3.5 w-3.5 mr-1" />}
                {data.status === "OK" && <CheckCircle2 className="h-3.5 w-3.5 mr-1" />}
                {data.status}
              </Badge>
            </div>
            <div className="text-[11px] text-muted-foreground mt-1">
              {data.days_of_supply} days supply on hand
            </div>
          </Card>

          <Card className="p-4 space-y-1">
            <div className="text-muted-foreground">Safety Stock (SS)</div>
            <div className="text-lg font-bold font-mono text-foreground">
              {formatNumber(data.safety_stock)} units
            </div>
            <div className="text-[11px] text-muted-foreground">
              z = {data.z_factor} buffer
            </div>
          </Card>

          <Card className="p-4 space-y-1">
            <div className="text-muted-foreground">Reorder Point (ROP)</div>
            <div className="text-lg font-bold font-mono text-foreground">
              {formatNumber(data.reorder_point)} units
            </div>
            <div className="text-[11px] text-muted-foreground">
              Lead time demand: {formatNumber(data.lead_time_demand)}
            </div>
          </Card>

          <Card className="p-4 space-y-1">
            <div className="text-muted-foreground">Suggested Order</div>
            <div className="text-lg font-bold font-mono text-primary">
              {formatNumber(data.suggested_order_qty)} units
            </div>
            <div className="text-[11px] text-muted-foreground">
              Est. cost: ${formatNumber(data.estimated_order_cost)}
            </div>
          </Card>
        </div>
      )}
    </div>
  )
}
