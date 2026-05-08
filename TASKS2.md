# TASKS2.md



## Current Phase

Phase 3 - Medium Importance (Tier 3)



## Current Gap

Gap 29 - Employee Survey & Engagement Module



## In Progress

Not started yet.



## Completed in Last Run

Gap 28 - Knowledge Base / Internal Wiki

Gap 27 - Quality System Completion

Gap 26 - Warehouse Execution Layer

Gap 25 - Sales Order to Cash Full Lifecycle

Gap 24 - Procurement System Depth



## Implemented Gap Items

1-28 (all previous gaps implemented — see TASKS2.md history)

Key: Gap 28 = Knowledge Base / Internal Wiki



## Remaining Gap Items

29. Employee Survey & Engagement Module

30. VoIP / Call Center Integration

31. Customer Loyalty Program

32. Recurring Billing / Auto-Invoicing

33. Video Meeting Integration

34. Customer / Product NPS Tracking

35. Native Mobile Apps Support Layer

36. API Developer Portal / GraphQL Layer

37. Real-Time Notification Center

38. Reporting & BI Layer

39. Document Management System

40. Customer / Supplier Portal Expansion

41. Audit Logs & Compliance Trail

42. Mobile-First Field Sales Expansion

43. Resource & Calendar Scheduling System

44. Integration Marketplace / Connector Hub

45. Returnable Packaging / Container Management

46. New Product Development Workflow

47. Route Optimization for Van Sales

48. Consumer Complaint Management Linked to Batch

49. Regulatory Certificate Tracking

50. Dynamic / AI Pricing Engine

51. Brand Asset / Label Design Management

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

Implement Gap 29 - Employee Survey & Engagement Module.

Inspect first:
- backend/app/models/ess.py - existing ESS model (self-service)
- frontend/src/app/dashboard/ess/ - existing ESS pages
- Check if any survey/engagement model exists

Expected: ESS module exists (leave, payslip, expenses). No survey/engagement module.

Build next coherent slice:
1. Add EmployeeSurvey model (title, type: PULSE/ENGAGEMENT/EXIT, questions_json, status, anonymous_flag, start_date, end_date).
2. Add SurveyResponse model (survey_id, respondent_id or null-if-anonymous, answers_json, submitted_at).
3. Add schema + CRUD endpoints under /api/v1/surveys.
4. Add frontend: survey dashboard, survey list, survey creation form, response form (for employees to fill), results/analytics page.
5. Wire nav under HR & Workforce section.



## Blockers

No schema migration blocker: app uses create_all.

Validation environment blocker: this shell has no python/py launcher on PATH.



## Files Changed in Last Run

Gap 28 additions:
backend/app/models/knowledge_base.py - NEW: KBCategory model (slug, name, description, parent_id for hierarchy, display_order, icon); KBArticle model (slug, title, summary, content_md, category_id, tags JSON, status DRAFT/PUBLISHED/ARCHIVED, version, author_id, last_editor_id, published_at, view_count, is_featured, access_level); KBArticleRevision model (article_id, version_no, title, content_md, change_summary, changed_by_id)
backend/app/api/v1/endpoints/knowledge_base.py - NEW: GET/POST /kb/categories + PATCH /kb/categories/{id}; GET /kb/articles (with full-text LIKE search, category filter, status filter, pagination) + GET /kb/articles/{id} (increments view_count) + POST /kb/articles + PATCH /kb/articles/{id} (auto-saves revision when content changes) + DELETE /kb/articles/{id} (archives); GET /kb/articles/{id}/revisions; GET /kb/search; GET /kb/stats
backend/app/api/v1/router.py - MODIFIED: Added knowledge_base import + /kb prefix route registration
frontend/src/lib/knowledge_base.ts - NEW: KBCategory, KBArticle, KBArticleDetail, KBRevision, KBStats interfaces; kbApi with all CRUD + search + stats methods
frontend/src/app/dashboard/knowledge-base/page.tsx - NEW: KB home - search bar with live results, stats row, category sidebar, featured/recent articles panel, top-viewed chips
frontend/src/app/dashboard/knowledge-base/articles/page.tsx - NEW: Article list with search, category filter, status filter, table with actions (view/edit/archive)
frontend/src/app/dashboard/knowledge-base/articles/new/page.tsx - NEW: Article editor - markdown textarea (24 rows), sidebar with slug/category/tags/access-level/featured, Save Draft + Publish buttons, markdown tips panel
frontend/src/app/dashboard/knowledge-base/[id]/page.tsx - NEW: Article viewer - renders markdown to HTML with basic regex transform, version history toggle, featured/status badges, tags display
frontend/src/components/nav-config.tsx - MODIFIED: Added Knowledge Base + KB Articles under Admin & System nav section



## Validation Results

Frontend TypeScript: PASS (npm.cmd run type-check, 0 errors)

Backend Python compile: BLOCKED (python not found)



## Notes for Next Claude Run

Gap 28 implementation notes:
- KBArticle.slug must be unique across all articles. Auto-generated from title (lowercase + hyphens).
- Version history: KBArticleRevision saved on every content_md change. version increments on each save.
- view_count incremented on every GET /kb/articles/{id} call.
- Markdown rendering in frontend: simple regex-based without external lib. Handles H1/H2/H3, bold, italic, inline code, bullet lists. For richer rendering, consider adding react-markdown in future.
- Article access_level: stored as string ("all", "management", "hr", etc.). Currently stored but not enforced at API level. Future: check user department/role against access_level.
- Full-text search: LIKE-based on title, summary, content_md. For large KB, replace with PostgreSQL FTS or Elasticsearch.

Gap 29 start: Check backend/app/models/ess.py to see if any survey tables exist. Check existing ESS nav entries. Fresh survey module implementation likely needed.
