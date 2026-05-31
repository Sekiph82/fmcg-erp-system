# Graph Report - scripts  (2026-05-31)

## Corpus Check
- Corpus is ~18,481 words - fits in a single context window. You may not need a graph.

## Summary
- 222 nodes · 303 edges · 17 communities
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Import Graph Auditor|Import Graph Auditor]]
- [[_COMMUNITY_ERP Health Audit (Python)|ERP Health Audit (Python)]]
- [[_COMMUNITY_Action Card Source Auditor|Action Card Source Auditor]]
- [[_COMMUNITY_Restored Routes Quality Check|Restored Routes Quality Check]]
- [[_COMMUNITY_Page Count Auditor|Page Count Auditor]]
- [[_COMMUNITY_ERP Manuals PDF Generator|ERP Manuals PDF Generator]]
- [[_COMMUNITY_Workspace Tabs Checker|Workspace Tabs Checker]]
- [[_COMMUNITY_Route Redirects Checker|Route Redirects Checker]]
- [[_COMMUNITY_Broken Action Cards Finder|Broken Action Cards Finder]]
- [[_COMMUNITY_Manual Screenshot Verifier|Manual Screenshot Verifier]]
- [[_COMMUNITY_Manual PDF Checker|Manual PDF Checker]]
- [[_COMMUNITY_Expected PDF Verifier|Expected PDF Verifier]]
- [[_COMMUNITY_Missing Manual Screenshots|Missing Manual Screenshots]]
- [[_COMMUNITY_Redirect Converter|Redirect Converter]]
- [[_COMMUNITY_Broken Targets Finder|Broken Targets Finder]]
- [[_COMMUNITY_Redirect Stubs Finder|Redirect Stubs Finder]]
- [[_COMMUNITY_Wave 1C Route Restorer|Wave 1C Route Restorer]]

## God Nodes (most connected - your core abstractions)
1. `Path` - 32 edges
2. `find()` - 14 edges
3. `run_audit()` - 13 edges
4. `read()` - 12 edges
5. `main()` - 7 edges
6. `check_unbounded_queries()` - 7 edges
7. `check_for_update_locks()` - 6 edges
8. `check_create_all()` - 6 edges
9. `check_localstorage_token()` - 6 edges
10. `classifyTarget()` - 5 edges

## Surprising Connections (you probably didn't know these)
- None detected - all connections are within the same source files.

## Import Cycles
- None detected.

## Communities (17 total, 0 thin omitted)

### Community 0 - "Import Graph Auditor"
Cohesion: 0.05
Nodes (42): allTargets, broken, brokenUniq, brokenWithGit, byMod, BYPASS_PREFIX_REDIRECT, ccItems, checkFileInGit() (+34 more)

### Community 1 - "ERP Health Audit (Python)"
Cohesion: 0.28
Nodes (23): bool, int, Path, check_create_all(), check_dev_server_in_prod_dockerfile(), check_env_file_mismatch(), check_for_update_locks(), check_health_endpoint_caching() (+15 more)

### Community 2 - "Action Card Source Auditor"
Cohesion: 0.13
Nodes (11): clean, fs, inventory, middlewareContent, middlewareRoutes, mwItems, pages, path (+3 more)

### Community 3 - "Restored Routes Quality Check"
Cohesion: 0.13
Nodes (14): docsDir, FRONTEND, fs, m, md, MIDDLEWARE, missing, mw (+6 more)

### Community 4 - "Page Count Auditor"
Cohesion: 0.21
Nodes (13): classify(), collectWorkspaceImports(), DASH_DIR, FRONTEND, fs, getSidebarWorkspaceHrefs(), isCoveredByMiddleware(), main() (+5 more)

### Community 5 - "ERP Manuals PDF Generator"
Cohesion: 0.19
Nodes (13): addImageCaptions(), { chromium }, coverHtml(), __dirname, embedImages(), FRONTEND_NM, generatePdf(), main() (+5 more)

### Community 6 - "Workspace Tabs Checker"
Cohesion: 0.23
Nodes (10): DASH_DIR, extractWorkspaceTabKeys(), FRONTEND, fs, isKebabCase(), main(), OUT_DIR, parseMiddlewareRedirects() (+2 more)

### Community 7 - "Route Redirects Checker"
Cohesion: 0.25
Nodes (10): DASH_DIR, FRONTEND, fs, main(), OUT_DIR, parseMiddleware(), parseRedirectMap(), path (+2 more)

### Community 8 - "Broken Action Cards Finder"
Cohesion: 0.20
Nodes (7): broken, fs, pages, path, stubMap, stubRoutes, tsxFiles

### Community 9 - "Manual Screenshot Verifier"
Cohesion: 0.20
Nodes (9): fs, manualResults, MANUALS_DIR, path, PLACEHOLDER_PATTERNS, report, REPORT_JSON, REPORT_MD (+1 more)

### Community 10 - "Manual PDF Checker"
Cohesion: 0.22
Nodes (8): fs, MANUALS_DIR, path, REPORT_JSON, REPORT_MD, results, SLUGS, totalImgs

### Community 11 - "Expected PDF Verifier"
Cohesion: 0.22
Nodes (8): EXPECTED_PDFS, fs, MANUALS_DIR, path, report, REPORT_JSON, REPORT_MD, results

### Community 12 - "Missing Manual Screenshots"
Cohesion: 0.25
Nodes (6): CAPTURES, __dirname, GOLIIVE_CAPTURES, GOLIIVE_DIR, PAYROLL_DIR, REPO_ROOT

### Community 13 - "Redirect Converter"
Cohesion: 0.29
Nodes (4): APP, fs, path, redirects

### Community 14 - "Broken Targets Finder"
Cohesion: 0.29
Nodes (5): byTarget, fs, pages, path, stubs

### Community 15 - "Redirect Stubs Finder"
Cohesion: 0.33
Nodes (4): fs, pages, path, stubs

### Community 16 - "Wave 1C Route Restorer"
Cohesion: 0.40
Nodes (4): { execSync }, fs, path, routes

## Knowledge Gaps
- **136 isolated node(s):** `fs`, `path`, `pages`, `stubMap`, `middlewareContent` (+131 more)
  These have ≤1 connection - possible missing edges or undocumented components.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Path` connect `ERP Health Audit (Python)` to `Import Graph Auditor`, `Action Card Source Auditor`, `Restored Routes Quality Check`, `Page Count Auditor`, `ERP Manuals PDF Generator`, `Workspace Tabs Checker`, `Route Redirects Checker`, `Broken Action Cards Finder`, `Manual Screenshot Verifier`, `Manual PDF Checker`, `Expected PDF Verifier`, `Missing Manual Screenshots`, `Redirect Converter`, `Broken Targets Finder`, `Redirect Stubs Finder`, `Wave 1C Route Restorer`?**
  _High betweenness centrality (0.917) - this node is a cross-community bridge._
- **What connects `fs`, `path`, `pages` to the rest of the system?**
  _136 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Import Graph Auditor` be split into smaller, more focused modules?**
  _Cohesion score 0.05217391304347826 - nodes in this community are weakly interconnected._
- **Should `Action Card Source Auditor` be split into smaller, more focused modules?**
  _Cohesion score 0.13333333333333333 - nodes in this community are weakly interconnected._
- **Should `Restored Routes Quality Check` be split into smaller, more focused modules?**
  _Cohesion score 0.13333333333333333 - nodes in this community are weakly interconnected._