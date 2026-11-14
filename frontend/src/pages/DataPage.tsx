import React, { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import {
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Database,
  Edit2,
  FileCheck2,
  History,
  Info,
  Sparkles,
  Wand2,
} from "lucide-react"
import { toast } from "sonner"
import { api } from "@/api/client"
import { Badge } from "@/components/ui/Badge"
import { Button } from "@/components/ui/Button"
import { Card } from "@/components/ui/Card"
import { Dialog } from "@/components/ui/Dialog"
import { Skeleton } from "@/components/ui/Skeleton"
import { ColumnMappingUpdate, Dataset, DatasetPreview } from "@/types"

interface DataPageProps {
  currentDataset: Dataset | null
  setCurrentDataset: (d: Dataset) => void
}

export const DataPage: React.FC<DataPageProps> = ({ currentDataset, setCurrentDataset }) => {
  const navigate = useNavigate()
  const [preview, setPreview] = useState<DatasetPreview | null>(null)
  const [currentPage, setCurrentPage] = useState(1)
  const [isLoadingPreview, setIsLoadingPreview] = useState(false)
  const [isCleaning, setIsCleaning] = useState(false)

  // Mapping edit dialog
  const [isMappingDialogOpen, setIsMappingDialogOpen] = useState(false)
  const [dateCol, setDateCol] = useState("")
  const [targetCol, setTargetCol] = useState("")
  const [groupCols, setGroupCols] = useState<string[]>([])
  const [regressorCols, setRegressorCols] = useState<string[]>([])

  // Audit log dialog
  const [isAuditDialogOpen, setIsAuditDialogOpen] = useState(false)

  useEffect(() => {
    if (currentDataset) {
      setDateCol(currentDataset.date_col)
      setTargetCol(currentDataset.target_col)
      setGroupCols(currentDataset.group_cols || [])
      setRegressorCols(currentDataset.regressor_cols || [])
      loadPreview(currentDataset.id, 1)
    }
  }, [currentDataset?.id])

  const loadPreview = async (id: string, page: number) => {
    try {
      setIsLoadingPreview(true)
      const data = await api.previewDataset(id, page, 15)
      setPreview(data)
      setCurrentPage(page)
    } catch (e: any) {
      toast.error(e.message || "Failed to load table preview")
    } finally {
      setIsLoadingPreview(false)
    }
  }

  const handleClean = async () => {
    if (!currentDataset) return
    try {
      setIsCleaning(true)
      const updated = await api.cleanDataset(currentDataset.id)
      setCurrentDataset(updated)
      toast.success("Dataset successfully cleaned and sanitized!")
      loadPreview(updated.id, currentPage)
    } catch (e: any) {
      toast.error(e.message || "Failed to clean dataset")
    } finally {
      setIsCleaning(false)
    }
  }

  const handleSaveMapping = async () => {
    if (!currentDataset) return
    try {
      const mapping: ColumnMappingUpdate = {
        date_col: dateCol,
        target_col: targetCol,
        group_cols: groupCols,
        regressor_cols: regressorCols,
      }
      const updated = await api.updateMapping(currentDataset.id, mapping)
      setCurrentDataset(updated)
      setIsMappingDialogOpen(false)
      toast.success("Column roles updated and dataset re-profiled!")
    } catch (e: any) {
      toast.error(e.message || "Failed to update column mapping")
    }
  }

  if (!currentDataset) {
    return (
      <Card className="p-12 text-center max-w-lg mx-auto mt-12">
        <Database className="h-12 w-12 text-muted-foreground mx-auto mb-4 opacity-50" />
        <h2 className="text-lg font-semibold text-foreground">No Dataset Loaded</h2>
        <p className="text-xs text-muted-foreground mt-1.5 mb-6">
          Upload a sales spreadsheet or generate synthetic sample data to inspect data quality.
        </p>
        <Button variant="primary" onClick={() => navigate("/")}>
          <Sparkles className="h-4 w-4 mr-2" />
          Go to Upload / Sample Data
        </Button>
      </Card>
    )
  }

  const report = currentDataset.quality_report
  const issues = report?.issues || []
  const criticalCount = issues.filter((i) => i.severity === "critical").length
  const warningCount = issues.filter((i) => i.severity === "warning").length

  return (
    <div className="space-y-8 animate-in fade-in duration-200">
      {/* Header & Quality Score */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold tracking-tight text-foreground">{currentDataset.name}</h1>
            <Badge variant={report?.is_valid ? "success" : "danger"} size="sm">
              {report?.is_valid ? "Valid for Forecasting" : "Issues Require Attention"}
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Cadence: <span className="font-semibold text-foreground">{currentDataset.frequency === "D" ? "Daily" : currentDataset.frequency}</span> •{" "}
            {currentDataset.row_count.toLocaleString()} rows • {currentDataset.col_count} columns
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          {currentDataset.audit_log && currentDataset.audit_log.length > 0 && (
            <Button variant="outline" size="sm" onClick={() => setIsAuditDialogOpen(true)}>
              <History className="h-4 w-4 mr-1.5" />
              Audit Log ({currentDataset.audit_log.length})
            </Button>
          )}

          <Button
            variant="primary"
            size="sm"
            onClick={handleClean}
            isLoading={isCleaning}
          >
            <Wand2 className="h-4 w-4 mr-1.5" />
            Fix Automatically
          </Button>

          <Button
            variant="secondary"
            size="sm"
            onClick={() => navigate("/forecast")}
          >
            Proceed to Forecast
            <ArrowRight className="h-4 w-4 ml-1.5" />
          </Button>
        </div>
      </div>

      {/* Column Schema Mapping Card */}
      <Card className="p-5">
        <div className="flex items-center justify-between mb-3 border-b border-border pb-2.5">
          <div className="flex items-center gap-2">
            <FileCheck2 className="h-4 w-4 text-primary" />
            <h3 className="text-sm font-semibold text-foreground">Detected Column Roles</h3>
          </div>
          <Button variant="ghost" size="sm" onClick={() => setIsMappingDialogOpen(true)}>
            <Edit2 className="h-3.5 w-3.5 mr-1.5" />
            Edit Roles
          </Button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
          <div className="bg-secondary/40 p-3 rounded-xl border border-border/50">
            <span className="text-muted-foreground block text-[11px] uppercase tracking-wider font-semibold">
              Date Column
            </span>
            <div className="font-mono font-medium text-foreground mt-1">
              <Badge variant="indigo" size="sm">{currentDataset.date_col || "Not Selected"}</Badge>
            </div>
          </div>

          <div className="bg-secondary/40 p-3 rounded-xl border border-border/50">
            <span className="text-muted-foreground block text-[11px] uppercase tracking-wider font-semibold">
              Target (Sales) Column
            </span>
            <div className="font-mono font-medium text-foreground mt-1">
              <Badge variant="success" size="sm">{currentDataset.target_col || "Not Selected"}</Badge>
            </div>
          </div>

          <div className="bg-secondary/40 p-3 rounded-xl border border-border/50">
            <span className="text-muted-foreground block text-[11px] uppercase tracking-wider font-semibold">
              Group / Hierarchy Columns
            </span>
            <div className="flex flex-wrap gap-1 mt-1">
              {currentDataset.group_cols && currentDataset.group_cols.length > 0 ? (
                currentDataset.group_cols.map((g) => (
                  <Badge key={g} variant="secondary" size="sm">{g}</Badge>
                ))
              ) : (
                <span className="text-muted-foreground italic">None (Combined series)</span>
              )}
            </div>
          </div>

          <div className="bg-secondary/40 p-3 rounded-xl border border-border/50">
            <span className="text-muted-foreground block text-[11px] uppercase tracking-wider font-semibold">
              External Regressors
            </span>
            <div className="flex flex-wrap gap-1 mt-1">
              {currentDataset.regressor_cols && currentDataset.regressor_cols.length > 0 ? (
                currentDataset.regressor_cols.map((r) => (
                  <Badge key={r} variant="outline" size="sm">{r}</Badge>
                ))
              ) : (
                <span className="text-muted-foreground italic">None detected</span>
              )}
            </div>
          </div>
        </div>
      </Card>

      {/* Quality Issues Checklist */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-foreground">Data Quality Audit</h2>
          <div className="flex items-center gap-2">
            {criticalCount > 0 && (
              <Badge variant="danger" size="sm">{criticalCount} Critical</Badge>
            )}
            {warningCount > 0 && (
              <Badge variant="warning" size="sm">{warningCount} Warnings</Badge>
            )}
            {issues.length === 0 && (
              <Badge variant="success" size="sm">All Checks Passed</Badge>
            )}
          </div>
        </div>

        {issues.length === 0 ? (
          <Card className="p-6 text-center bg-emerald-500/[0.03] border-emerald-500/20">
            <CheckCircle2 className="h-8 w-8 text-emerald-500 mx-auto mb-2" />
            <h3 className="font-semibold text-sm text-foreground">Perfect Health Score (100/100)</h3>
            <p className="text-xs text-muted-foreground mt-1">
              Timeline is continuous, no duplicates, negatives, or critical outliers detected.
            </p>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {issues.map((issue) => (
              <Card key={issue.id} className="p-4 space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    {issue.severity === "critical" ? (
                      <AlertCircle className="h-4 w-4 text-rose-500 flex-shrink-0" />
                    ) : issue.severity === "warning" ? (
                      <AlertTriangle className="h-4 w-4 text-amber-500 flex-shrink-0" />
                    ) : (
                      <Info className="h-4 w-4 text-indigo-500 flex-shrink-0" />
                    )}
                    <span className="text-xs font-semibold text-foreground capitalize">
                      {issue.issue_type.replace(/_/g, " ")}
                    </span>
                  </div>
                  <Badge
                    variant={
                      issue.severity === "critical"
                        ? "danger"
                        : issue.severity === "warning"
                        ? "warning"
                        : "default"
                    }
                    size="sm"
                  >
                    {issue.severity}
                  </Badge>
                </div>

                <p className="text-xs text-muted-foreground leading-relaxed">{issue.message}</p>

                <div className="bg-secondary/40 p-2.5 rounded-lg border border-border/40 text-[11px] text-foreground flex items-start gap-1.5">
                  <span className="font-semibold text-primary">Fix:</span>
                  <span>{issue.suggested_fix}</span>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Raw Data Preview Table */}
      <Card className="p-0 overflow-hidden">
        <div className="p-4 border-b border-border flex items-center justify-between">
          <h3 className="text-sm font-semibold text-foreground">Dataset Records Preview</h3>
          {preview && (
            <span className="text-xs text-muted-foreground">
              Showing page {currentPage} of {Math.ceil(preview.total_rows / preview.page_size)}
            </span>
          )}
        </div>

        <div className="overflow-x-auto">
          {isLoadingPreview ? (
            <div className="p-6 space-y-2">
              <Skeleton className="h-6 w-full" />
              <Skeleton className="h-6 w-full" />
              <Skeleton className="h-6 w-full" />
            </div>
          ) : preview ? (
            <table className="w-full text-xs text-left border-collapse">
              <thead>
                <tr className="bg-secondary/60 border-b border-border">
                  {preview.columns.map((col) => (
                    <th key={col} className="p-3 font-semibold text-foreground whitespace-nowrap">
                      <div>{col}</div>
                      <span className="text-[10px] text-muted-foreground font-mono font-normal">
                        {preview.dtypes[col]}
                      </span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {preview.rows.map((row, idx) => (
                  <tr key={idx} className="hover:bg-secondary/30 transition-colors">
                    {preview.columns.map((col) => (
                      <td key={col} className="p-3 text-muted-foreground whitespace-nowrap tabular-nums">
                        {String(row[col])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          ) : null}
        </div>

        {/* Pagination Controls */}
        {preview && (
          <div className="p-3 border-t border-border flex items-center justify-between text-xs">
            <span className="text-muted-foreground">
              Total {preview.total_rows.toLocaleString()} entries
            </span>
            <div className="flex items-center gap-1.5">
              <Button
                variant="outline"
                size="sm"
                disabled={currentPage <= 1}
                onClick={() => loadPreview(currentDataset.id, currentPage - 1)}
              >
                <ChevronLeft className="h-3.5 w-3.5 mr-1" />
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={currentPage * preview.page_size >= preview.total_rows}
                onClick={() => loadPreview(currentDataset.id, currentPage + 1)}
              >
                Next
                <ChevronRight className="h-3.5 w-3.5 ml-1" />
              </Button>
            </div>
          </div>
        )}
      </Card>

      {/* Edit Column Mapping Dialog */}
      <Dialog
        open={isMappingDialogOpen}
        onClose={() => setIsMappingDialogOpen(false)}
        title="Edit Column Mapping"
        description="Override automatically detected column roles."
      >
        <div className="space-y-4 text-xs">
          <div>
            <label className="font-semibold block mb-1">Date Column</label>
            <select
              value={dateCol}
              onChange={(e) => setDateCol(e.target.value)}
              className="w-full bg-secondary border border-border rounded-xl px-3 py-2 text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            >
              {preview?.columns.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="font-semibold block mb-1">Target Sales Column</label>
            <select
              value={targetCol}
              onChange={(e) => setTargetCol(e.target.value)}
              className="w-full bg-secondary border border-border rounded-xl px-3 py-2 text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            >
              {preview?.columns.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="font-semibold block mb-1">Group Columns (Store, Product, Category)</label>
            <div className="space-y-1 max-h-32 overflow-y-auto border border-border p-2 rounded-xl">
              {preview?.columns.map((c) => (
                <label key={c} className="flex items-center gap-2 cursor-pointer hover:text-foreground">
                  <input
                    type="checkbox"
                    checked={groupCols.includes(c)}
                    onChange={(e) => {
                      if (e.target.checked) setGroupCols([...groupCols, c])
                      else setGroupCols(groupCols.filter((col) => col !== c))
                    }}
                    className="rounded text-primary"
                  />
                  <span>{c}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-border">
            <Button variant="outline" size="sm" onClick={() => setIsMappingDialogOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" onClick={handleSaveMapping}>
              Apply Changes
            </Button>
          </div>
        </div>
      </Dialog>

      {/* Audit Log Dialog */}
      <Dialog
        open={isAuditDialogOpen}
        onClose={() => setIsAuditDialogOpen(false)}
        title="Data Cleaning Audit Log"
        description="Every automated adjustment made to sanitize your historical records."
      >
        <div className="space-y-3 max-h-[60vh] overflow-y-auto text-xs">
          {currentDataset.audit_log && currentDataset.audit_log.length > 0 ? (
            currentDataset.audit_log.map((entry, idx) => (
              <div key={idx} className="p-3 rounded-xl border border-border bg-secondary/30 space-y-1">
                <div className="flex items-center justify-between font-semibold text-foreground">
                  <span>{entry.action}</span>
                  <Badge variant="outline" size="sm">{entry.rows_affected} rows affected</Badge>
                </div>
                <p className="text-muted-foreground">{entry.details}</p>
                <span className="text-[10px] text-muted-foreground/80 block">
                  {new Date(entry.timestamp).toLocaleString()}
                </span>
              </div>
            ))
          ) : (
            <p className="text-muted-foreground">No cleaning actions taken yet.</p>
          )}
        </div>
      </Dialog>
    </div>
  )
}
