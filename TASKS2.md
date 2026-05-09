# TASKS2.md



## Current Phase

Tier 5 — Advanced / Future Roadmap



## Current Gap

Gap 62 - ML-Based Demand Forecasting Engine



## In Progress

Not started yet.



## Completed in Last Run

Gap 61 - IoT / Real-Time Machine Data Streaming

Gap 60 - Kenya Localization Expansion

Gap 59 - Secondary Sales / Distributor Sell-Through Expansion

Gap 58 - Trade Promotion Management Expansion



## Implemented Gap Items

1-61 implemented.



## Remaining Gap Items

62. ML-Based Demand Forecasting Engine

63. Blockchain-Based Traceability

64. Carbon Footprint Per Product

65. AI-Powered Receipt OCR

66. Natural Language ERP Control

67. AI Agent Governance Framework

68. Predictive Maintenance

69. ESG Intelligence & Sustainability Optimization

70. Plugin / App Marketplace Architecture



## Next Immediate Task

Implement Gap 62 - ML-Based Demand Forecasting Engine properly.

Inspect first:
- Check backend/app/models/mrp.py — MRP has basic demand planning
- Check backend/app/api/v1/endpoints/mrp.py — existing forecasting endpoints
- Check frontend/src/app/dashboard/mrp/ — existing MRP/planning pages

Gap 62 what's genuinely missing:
- Time-series ML models (ARIMA / Prophet / LSTM) — Python-based, implement rule-based + moving average as functional core
- Seasonality detection (compare same period last year)
- Promotion uplift modeling (adjust forecast when promotion scheduled)
- Cross-SKU demand correlation
- Forecast accuracy tracking (MAPE, RMSE)
- Continuous model retraining trigger
- Forecast override with audit trail

Build plan:
1. Inspect existing MRP/forecasting models + endpoints.
2. Add ForecastModel model (sku/product_id, model_type: MOVING_AVG/SEASONAL/PROMOTION_ADJUSTED, parameters JSONB, last_trained_at, accuracy_mape, accuracy_rmse, is_active).
3. Add ForecastRun model (forecast_model_id, run_date, forecast_period, forecast_qty, confidence_interval_low/high, actual_qty nullable, override_qty nullable, override_reason, override_by).
4. Add ForecastAccuracyLog model (model_id, period, forecast_qty, actual_qty, mape, rmse, created_at).
5. Endpoints: POST /forecasting/models (create model config), GET /forecasting/models, POST /forecasting/models/{id}/run (compute forecast from sales history using moving average), GET /forecasting/runs, PATCH /forecasting/runs/{id}/override, GET /forecasting/accuracy (MAPE/RMSE tracking).
6. Frontend: Demand Forecasting hub — model config, forecast table with override capability, accuracy dashboard.
7. Nav under Planning.



## Blockers

No schema migration blocker: app uses create_all.

Validation environment blocker: python not found on PATH.



## Files Changed in Last Run

Gap 61 additions:
backend/app/models/iot.py - NEW: SensorDataPoint, MachineStateEvent, IoTAlertThreshold, IoTAlert models
backend/app/api/v1/endpoints/iot.py - NEW: Full IoT ingest + state + alerts + dashboard endpoints
backend/app/api/v1/router.py - MODIFIED: iot route
frontend/src/app/dashboard/iot/page.tsx - NEW: IoT Dashboard — 5 tabs
frontend/src/components/nav-config.tsx - MODIFIED: IoT Machine Data nav link



## Validation Results

Frontend TypeScript: PASS (npm.cmd run type-check, 0 errors — verified after Gap 61)

Backend Python compile: BLOCKED (python not found)



## Notes for Next Claude Run

Gap 61 notes:
- SensorDataPoint.ingest: no auth (device push). Other endpoints require auth.
- Alert auto-triggered on ingest if value breaches threshold.
- MQTT: external bridge → POST /api/v1/iot/ingest.

Gap 62 start:
- Check MRP models first. mrp.py likely has DemandForecast or similar.
- Do NOT duplicate existing MRP demand planning.
- Add what's genuinely NEW: ML model config tracking, MAPE/RMSE accuracy, forecast override with audit trail, seasonality-aware computation.
- Moving average implementation in pure Python (no scikit-learn) — compute from SalesOrder history.
