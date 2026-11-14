import {
  ColumnMappingUpdate,
  Dataset,
  DatasetPreview,
  ModelOption,
  QualityReport,
  RunResult,
  RunStatus,
  RunSummary,
  SeriesOption,
} from "@/types"

const BASE_URL = "/api"

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${BASE_URL}${endpoint}`
  const response = await fetch(url, {
    ...options,
    headers: {
      ...(!options?.body || typeof options.body === "string"
        ? { "Content-Type": "application/json" }
        : {}),
      ...options?.headers,
    },
  })

  if (!response.ok) {
    let errorDetail = "An unexpected error occurred"
    try {
      const errorJson = await response.json()
      errorDetail = errorJson.detail || errorJson.message || errorDetail
    } catch {
      errorDetail = await response.text()
    }
    throw new Error(errorDetail)
  }

  return response.json()
}

export const api = {
  // Datasets
  createSampleDataset: (): Promise<Dataset> => {
    return request<Dataset>("/datasets/sample", { method: "POST" })
  },

  uploadDataset: async (file: File): Promise<Dataset> => {
    const formData = new FormData()
    formData.append("file", file)
    const response = await fetch(`${BASE_URL}/datasets/upload`, {
      method: "POST",
      body: formData,
    })
    if (!response.ok) {
      let err = "Upload failed"
      try {
        const errorJson = await response.json()
        err = errorJson.detail || err
      } catch {
        err = await response.text()
      }
      throw new Error(err)
    }
    return response.json()
  },

  getDataset: (id: string): Promise<Dataset> => {
    return request<Dataset>(`/datasets/${id}`)
  },

  updateMapping: (id: string, mapping: ColumnMappingUpdate): Promise<Dataset> => {
    return request<Dataset>(`/datasets/${id}/mapping`, {
      method: "POST",
      body: JSON.stringify(mapping),
    })
  },

  previewDataset: (id: string, page = 1, pageSize = 25): Promise<DatasetPreview> => {
    return request<DatasetPreview>(`/datasets/${id}/preview?page=${page}&page_size=${pageSize}`)
  },

  getDatasetProfile: (id: string): Promise<QualityReport> => {
    return request<QualityReport>(`/datasets/${id}/profile`)
  },

  cleanDataset: (id: string): Promise<Dataset> => {
    return request<Dataset>(`/datasets/${id}/clean`, { method: "POST" })
  },

  getSeries: (id: string): Promise<SeriesOption[]> => {
    return request<SeriesOption[]>(`/datasets/${id}/series`)
  },

  // Forecast Runs
  getModels: (): Promise<ModelOption[]> => {
    return request<ModelOption[]>("/runs/models")
  },

  createRun: (params: {
    dataset_id: string
    series_id: string
    horizon: number
    models: string[]
    n_folds: number
    metric: string
  }): Promise<RunStatus> => {
    return request<RunStatus>("/runs", {
      method: "POST",
      body: JSON.stringify(params),
    })
  },

  getRunStatus: (id: string): Promise<RunStatus> => {
    return request<RunStatus>(`/runs/${id}`)
  },

  getRunResult: (id: string): Promise<RunResult> => {
    return request<RunResult>(`/runs/${id}/result`)
  },

  listRuns: (): Promise<RunSummary[]> => {
    return request<RunSummary[]>("/runs")
  },

  getDownloadUrl: (id: string): string => {
    return `${BASE_URL}/runs/${id}/download`
  },
}
