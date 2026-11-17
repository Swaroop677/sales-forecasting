# Forecastly 📈

[![CI Pipeline](https://github.com/Swaroop677/sales-forecasting/actions/workflows/ci.yml/badge.svg)](https://github.com/Swaroop677/sales-forecasting/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![React: 18](https://img.shields.io/badge/react-18-61dafb.svg)](https://react.dev/)
[![Status: Phase 3 Complete](https://img.shields.io/badge/status-Phase%203%20Complete-emerald.svg)]()

> **Automated Sales Forecasting, Conversational AI Intelligence, and Inventory Optimization.**  
> Transforms historical transactions into calibrated multi-step forecasts with model leaderboard comparison, TreeSHAP explainability, and split-conformal uncertainty intervals in 3 clicks.

---

## 🌟 Key Highlights

- **Multi-Model Rolling-Origin Backtesting**: Automatically evaluates Seasonal Naive, Holt-Winters, LightGBM, and XGBoost across expanding test folds with zero data leakage. Selects the champion model by out-of-sample WAPE.
- **Split-Conformal Prediction Intervals**: Model-agnostic 80% and 95% uncertainty bands calibrated from backtest residuals with empirical coverage tracking.
- **Conversational AI Forecasting Copilot (⌘K)**: Streamed SSE agent powered by Google Gemini, OpenAI-compatible APIs (Groq/Ollama/OpenRouter), or a zero-key Rule-Based Fallback. All numbers are strictly verified against deterministic pipeline results.
- **TreeSHAP & Decomposition Explainability**: Global driver importance and local "Why this number?" waterfall breakdowns.
- **Inventory Decision Support**: Safety stocks ($SS = z \cdot \sigma_e \cdot \sqrt{L}$), reorder point (ROP), and suggested replenishment sizes with status chips and CSV export.
- **Data Drift Monitoring**: Population Stability Index (PSI) and Kolmogorov-Smirnov (KS) test for feature staleness alerts.
- **Multi-Sheet Excel & Printable PDF Reports**: One-click professional multi-sheet Excel exports and `@media print` formatted executive reports.
- **Free-Host Constraints**: Strictly adheres to $\le$ 2 GB RAM, CPU-only instances with background in-process jobs.

---

## 📸 Screenshots

| Overview & KPI Dashboard | Forecast Studio & Conformal Bands |
|:---:|:---:|
| *(Screenshot Placeholder: Overview)* | *(Screenshot Placeholder: Forecast Studio)* |

| AI Copilot Drawer (⌘K) | TreeSHAP Driver Explainability |
|:---:|:---:|
| *(Screenshot Placeholder: AI Copilot)* | *(Screenshot Placeholder: Explainability)* |

---

## 🏗️ System Architecture

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

## ⚡ Quick Start

### 1. Local Development

```bash
# 1. Clone repository
git clone https://github.com/Swaroop677/sales-forecasting.git
cd sales-forecasting

# 2. Setup Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# 3. Start Backend
uvicorn backend.app.main:app --host 0.0.0.0 --port 8080 --reload

# 4. In a second terminal, start Frontend
cd frontend
npm install
npm run dev
```
Open **[http://localhost:5173](http://localhost:5173)** in your browser.

---

### 2. Single-Container Production Run

```bash
docker build -t forecastly .
docker run -p 8080:8080 forecastly
```
Visit **[http://localhost:8080](http://localhost:8080)**.

---

## 🛠️ Tech Stack

| Layer | Technologies |
|---|---|
| **Backend** | Python 3.11, FastAPI, SQLModel (SQLite / PostgreSQL), Pydantic v2 |
| **Forecasting & ML** | LightGBM, XGBoost, Statsmodels, Scikit-learn, OpenMP |
| **Explainability** | TreeSHAP (native contributions), Classical Decomposition |
| **Frontend** | React 18, TypeScript (strict), Vite, Tailwind CSS, shadcn/ui, Recharts |
| **AI Copilot** | Google GenAI REST, OpenAI-compatible API, Deterministic Fallback, SSE |
| **Packaging** | Multi-stage Dockerfile, Cloud Run, Render, GitHub Pages |

---

## 👥 Project Contributions

| Team Member | Role | Key Contributions |
|---|---|---|
| *Member 1* | *Full-Stack / ML Lead* | Forecasting pipeline, rolling-origin backtest, conformal intervals |
| *Member 2* | *AI & Agent Systems* | Tool-calling agent, provider integration, numeric grounding verification |
| *Member 3* | *Frontend & UI/UX* | Dashboard aesthetics, chart components, interactive tabs, accessibility |
| *Member 4* | *MLOps & DevOps* | Multi-stage Dockerfile, CI/CD workflows, Cloud Run / Render deployment |

---

## 📄 License
This project is licensed under the [MIT License](LICENSE).
