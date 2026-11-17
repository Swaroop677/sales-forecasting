# Future Work & Roadmap

Potential avenues for continuing Forecastly development:

---

## 1. Deep Learning & Foundation Time-Series Models
- Integrate lightweight pretrained time-series foundation models (e.g., Chronos-Bolt, TimeGPT, or PatchTST) with ONNX Runtime CPU inference.
- Support intermittent demand architectures (Croston's method, TSB) for slow-moving spare parts.

## 2. Multi-Echelon Supply Chain Optimization
- Expand inventory decision support from single-echelon safety stock to multi-echelon network allocation across regional fulfillment centers.
- Integer linear programming (PuLP / SciPy Optimize) for constrained pallet and shipping container bin packing.

## 3. Real-Time Streaming Ingestion
- Webhooks for direct POS (Square, Shopify, Stripe) inventory decrement synchronization.
- Automated drift re-calibration triggering background retrains automatically upon PSI threshold breaches.

## 4. Multi-Modal Visual Agent Interaction
- Enable the AI copilot to visually inspect uploaded receipt scans and promotional campaign flyers to extract future discount schedules.
