# System Limitations & Engineering Caveats

Forecastly strives to be transparent about its theoretical and operational boundaries.

---

## 1. Conformal Prediction Assumptions
- **Exchangeability Assumption**: Split-conformal intervals assume that out-of-sample test residuals and future forecast errors are roughly exchangeable. In the presence of acute structural regime shifts (e.g. abrupt economic lockdowns or extreme black-swan shortages), empirical coverage may temporarily diverge from nominal 80% or 95% levels.
- **Horizon Uncertainty Fan-Out**: Forecastly applies an expansion factor $\sqrt{t}$ to prevent over-optimistic narrow bands across long horizons, but long horizons (> 90 days) inherently carry compounding error.

## 2. Free-Tier Ephemeral Hosting Constraints
- **Ephemeral Storage**: When deployed on free tiers (Render, Fly.io, Cloud Run scale-to-zero), disk storage resets upon container sleep or cold restarts. Forecastly guards against this with friendly 404 recovery alerts and the ability to connect persistent external databases via `DATABASE_URL`.
- **Memory Ceiling**: Worker threads are hard-capped at `OMP_NUM_THREADS=1` and `n_jobs <= 2` to prevent out-of-memory kills on 1–2 GB RAM instances. Prophet is lazy-loaded and disabled by default.

## 3. Synthetic Sample Data Caveats
- The bundled sample dataset (`data/sample/sales.csv`) models realistic trends, 7-day cyclicality, annual holiday spikes, and promotional discounts. However, real-world retail timelines frequently exhibit messy sparse demand, sudden stockouts, and irregular store openings that require domain-specific feature engineering.

## 4. LLM & Conversational Agent Caveats
- **Decision Support, Not Advice**: What-if simulations and inventory recommendations provide statistical heuristics (e.g., safety stocks $SS = z \cdot \sigma_e \cdot \sqrt{L}$), not financial, legal, or guaranteed commercial advice.
- **Strict Grounding Boundaries**: The agent is restricted from free-form calculations to eliminate hallucination. If a query requests figures not supported by deterministic tools, the agent gracefully clarifies what calculations are possible.
