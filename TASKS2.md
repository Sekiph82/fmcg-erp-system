# TASKS2.md



## Current Phase

Tier 4 — FMCG-Specific & Regulatory



## Current Gap

Gap 52 - Market Intelligence / Competitor Tracking



## In Progress

Not started yet.



## Completed in Last Run

Gap 51 - Brand Asset / Label Design Management

Gap 50 - Dynamic / AI Pricing Engine



## Implemented Gap Items

1-51 implemented.



## Remaining Gap Items

52. Market Intelligence / Competitor Tracking

53. Co-Packing / Toll Manufacturing

54. HACCP System Expansion

55. Allergen & Nutrition Management

56. GS1 Barcode & Labeling Advanced

57. Shelf-Life / FEFO Control Expansion

58. Trade Promotion Management Expansion

59. Secondary Sales / Distributor Sell-Through Expansion

60. Kenya Localization Expansion

61. IoT / Real-Time Machine Data Streaming

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

Implement Gap 52 - Market Intelligence / Competitor Tracking.

Note: Gap 50 (Dynamic Pricing) added CompetitorPrice model for price tracking. Gap 52 is broader — field-level market intelligence: shelf share, volume estimates, promotions observed, market share.

What's needed:
- Competitor price monitoring (already in Gap 50 dp_competitor_prices — link/extend rather than duplicate)
- Market share tracking (% estimates per category)
- Shelf share tracking (field data: how many facings we have vs competitor)
- Promotion effectiveness vs market
- External data integration stub (Nielsen/IRI)

Build plan:
1. MarketObservation model (observer_name, outlet_name, outlet_type, location, observation_date, category, our_brand_facings, total_facings, our_shelf_share_pct, notes).
2. MarketShareEstimate model (category, period_month, our_share_pct, competitor_shares JSONB, source, notes).
3. Endpoints: CRUD observations, shelf share analytics, market share tracker.
4. Frontend: Market Intelligence hub page with shelf share table + market share tracker.
5. Nav under Sales & Distribution or AI/Analytics.



## Blockers

No schema migration blocker: app uses create_all.

Validation environment blocker: python not found on PATH.



## Files Changed in Last Run

Gap 51 additions:
backend/app/models/brand_assets.py - NEW: BrandAsset model (asset_ref, name, asset_type LABEL/ARTWORK/PACKAGING_DESIGN/LOGO/BRAND_GUIDELINE/PRODUCT_PHOTO/MARKETING_MATERIAL, brand, product_sku, version int, is_latest, previous_version_id FK, bom_version, bom_id, bom_change_flag, file_url/thumbnail_url/file_format, compliance_checklist JSONB, status DRAFT/IN_REVIEW/APPROVED/REJECTED/PRINT_READY/ARCHIVED); AssetApprovalStage model (asset_id FK, stage_name, stage_order, status PENDING/APPROVED/REJECTED/SKIPPED, approved_by, approved_at)
backend/app/api/v1/endpoints/brand_assets.py - NEW: POST /brand-assets/ (seeds 4 approval stages R&D/Regulatory/Marketing/Print); GET /brand-assets/ (filter type/status/sku/bom_change_flag); GET /brand-assets/stats; GET /brand-assets/{id} (with approval_stages); POST /brand-assets/{id}/stages/{stage_id}/approve (auto-sets PRINT_READY if all approved); POST /brand-assets/{id}/stages/{stage_id}/reject; PATCH /brand-assets/{id}/compliance; POST /brand-assets/{id}/new-version; POST /brand-assets/{id}/flag-bom-change
backend/app/api/v1/router.py - MODIFIED: brand_assets route
frontend/src/app/dashboard/brand-assets/page.tsx - NEW: Brand Asset hub — KPI strip, type/status/BOM-alert filters, asset grid (thumbnail/icon, compliance bar, version badge, BOM changed alert), upload form
frontend/src/app/dashboard/brand-assets/[id]/page.tsx - NEW: Asset detail — approval pipeline (approve/reject per stage, auto Print Ready when all approved), compliance checklist toggle, BOM change flag button, file link
frontend/src/components/nav-config.tsx - MODIFIED: Brand Assets / DAM under Quality Control

Gap 50 additions:
backend/app/models/dynamic_pricing.py - NEW: CompetitorPrice (product_name, competitor_name, price, channel MODERN_TRADE/DISTRIBUTOR/EXPORT/VAN_SALES/ONLINE/WHOLESALE, observed_date, source); PriceRecommendation (current_price, recommended_price, floor_price, avg_competitor_price, margin_pct, confidence_score, trigger, status PENDING/APPLIED/REJECTED/EXPIRED)
backend/app/api/v1/endpoints/dynamic_pricing.py - NEW: POST/GET /dynamic-pricing/competitor-prices; GET /dynamic-pricing/competitor-prices/summary (avg/min/max per product×channel); POST /dynamic-pricing/recommendations/generate (rule engine: COMPETITOR_UNDERCUT if competitor avg < current×0.92, LOW_MARGIN if margin < floor); GET /dynamic-pricing/recommendations; POST /dynamic-pricing/recommendations/{id}/apply|reject; GET /dynamic-pricing/dashboard
backend/app/api/v1/router.py - MODIFIED: dynamic_pricing route
frontend/src/app/dashboard/dynamic-pricing/page.tsx - NEW: 4-tab page: Price Recommendations (apply/reject cards), Competitor Data (table), Log Price, Generate Recommendation (rule engine form with result)
frontend/src/components/nav-config.tsx - MODIFIED: AI Pricing Engine under Sales & Distribution



## Validation Results

Frontend TypeScript: PASS (npm.cmd run type-check, 0 errors — verified after Gap 51)

Backend Python compile: BLOCKED (python not found)



## Notes for Next Claude Run

Gap 51 notes:
- Approval stages seeded on create: R&D (order 1) → Regulatory (2) → Marketing (3) → Print (4). Auto-set PRINT_READY when all 4 approved.
- compliance_checklist default keys: allergen_declared, nutrition_label, ingredient_list, net_weight, manufacturer_details, expiry_date_format, barcode_present, kebs_mark.
- bom_change_flag: manual flag (POST /flag-bom-change) alerts team that BOM changed and label needs review.
- new-version creates new asset (version=prev+1, previous_version_id=prev.id, prev.is_latest=False), seeds fresh approval stages.
- Asset grid shows compliance progress bar colored by pct: green=100%, amber≥60%, red<60%.

Gap 50 notes:
- Rule engine: COMPETITOR_UNDERCUT → recommend competitor_avg × 0.98. LOW_MARGIN → floor = cost / (1 - floor_margin_pct/100). Confidence: 80 for undercut, 95 for margin breach.
- CompetitorPrice and PriceRecommendation are separate models from pricing.py and price_list.py (which handle static price lists/rules).

Gap 52 start: Distinct from Gap 50 (price tracking). Gap 52 = broader market intelligence: shelf share (our facings vs total), market share estimates, promotion observation. Create new market_intelligence.py model + endpoint.
