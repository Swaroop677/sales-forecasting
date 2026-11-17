# Forecastly System Architecture

Forecastly is designed as a modular, low-overhead automated sales forecasting platform adhering strictly to free-hosting limits (<= 2 GB RAM, CPU-only).

---

## 1. End-to-End Architecture

```mermaid
flowchart TD
    subgraph Client["Frontend (React 18 + TypeScript + Vite)"]
        UI["Modern Dashboard (Tailwind + shadcn)"]
        Chat["AI Copilot Drawer & Page (SSE Stream)"]
        Charts["Forecast Chart with Conformal Bands"]
        Analytics["Explainability, Segments, Inventory Tabs"]
    end

    subgraph API["FastAPI Application Layer"]
        Router["API Router (/api)"]
        SecHeaders["Security Headers & Timing Middleware"]
        HealthReady["/health & /ready Probes"]
        SSEStream["SSE Streaming /api/agent/chat"]
    end

    subgraph Engine["Deterministic Services & ML Layer"]
        Profiler["Data Profiler & Quality Report"]
        Cleaner["Sanitizer & Audit Log"]
        Backtest["Rolling-Origin Expanding-Window Backtest"]
        Conformal["Split-Conformal Calibration (80% & 95%)"]
        SHAP["TreeSHAP & Decomposition Explainability"]
        Inventory["Inventory Decision Support (SS / ROP)"]
        Drift["PSI & KS Drift Monitor"]
    end

    subgraph LLM["Agent & LLM Provider Layer"]
        Orchestrator["Tool-Calling Loop (Max 6 turns)"]
        Gemini["Google Gemini Provider (REST)"]
        OpenAI["OpenAI-Compatible Provider"]
        Fallback["Rule-Based Fallback (Zero Key)"]
        Grounding["Numeric Grounding Verifier"]
    end

    subgraph Persistence["Storage Layer"]
        SQLite[("SQLite / Optional Postgres (SQLModel)")]
        DiskStorage["Ephemeral Disk / Artifacts"]
    end

    UI --> Router
    Chat --> SSEStream
    Router --> Engine
    SSEStream --> Orchestrator
    Orchestrator --> Engine
    Orchestrator --> Gemini
    Orchestrator --> OpenAI
    Orchestrator --> Fallback
    Orchestrator --> Grounding
    Engine --> SQLite
    Engine --> DiskStorage
```

---

## 2. Zero-Leakage Rolling-Origin Backtesting

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant API as FastAPI Router
    participant Backtest as Backtest Engine
    participant Model as Forecaster Models
    participant Conformal as Conformal Evaluator

    User->>API: POST /api/runs (horizon=30, n_folds=3)
    API->>Backtest: Split timeline into expanding folds
    loop For each Fold k (1 to 3)
        Backtest->>Model: Fit on historical train window ONLY
        Backtest->>Model: Predict next horizon days
        Backtest->>Backtest: Compute out-of-sample WAPE, MAE, RMSE, MASE
        Backtest->>Backtest: Accumulate absolute residuals |y - y_hat|
    end
    Backtest->>Conformal: Calibrate nonconformity quantiles (q80, q95)
    Conformal->>Backtest: Return finite-sample corrected bands & empirical coverage
    Backtest->>Model: Refit winning champion model on 100% data
    Backtest->>User: Leaderboard + Forecast points with conformal intervals
```

---

## 3. Conversational AI Agent Grounding Architecture

```mermaid
flowchart LR
    UserQuery["User Prompt"] --> Agent["Agent Orchestrator"]
    Agent --> Provider{"LLM Provider"}
    Provider -->|Gemini API| Gemini["Google GenAI"]
    Provider -->|OpenAI API| OAI["Groq / Ollama / OpenAI"]
    Provider -->|No Key| RuleBased["Rule-Based Fallback"]
    
    Provider --> ToolCall["Tool Call Request"]
    ToolCall --> DeterministicCode["Whitelisted Deterministic Tool"]
    DeterministicCode --> ToolOutput["Tool JSON Result & Chart Spec"]
    ToolOutput --> Verifier["Numeric Grounding Verifier"]
    Verifier --> Badge["Numbers verified ✓ Badge"]
    Badge --> UI["Streamed SSE Markdown Response"]
```
