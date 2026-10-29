# Research workbench design verification

final result: passed

## Evidence and state

- Source visual truth: selected concept 3, `/Users/kay/.codex/generated_images/01a183a9-cdc9-7df1-992e-1ba283e0f59c/exec-6069b6fd-6335-46d2-b9d8-a2406c2fcc4b.png`.
- Rendered implementation: `docs/images/main-synthetic.png`; expanded table: `docs/images/table-synthetic.png`.
- Source: 1448 × 1086 pixels, normalized to 1280 × 960 for comparison. Actual Qt widget capture: 1280 × 960 pixels, device pixel ratio 1. This is a native desktop application; CSS viewport is not applicable.
- State: automatic demo retrieval complete, Europe/Zurich, 72 synthetic records, fictional DEMO-001, 15 January 2026. No live API requests.
- Combined full-view evidence: `/tmp/vitals-design-comparison.png`; focused controls/summary evidence: `/tmp/vitals-design-details.png`. Both source and implementation were opened together in each comparison.

## Findings and comparison history

1. Initial rendered view: P2, date/time and timezone controls extended beyond the fixed sidebar. Fixed by bounding combo-box content hints and the time-control widths. New screenshots and a regression test confirm all controls fit at the minimum 1000 × 800 window size.
2. Initial badge lost its background to a more specific header selector. Fixed the selector and verified the final mint badge.
3. Screenshot automation could capture twice after initial placeholder and Plotly page loads, overwriting the overview after expanding the table. Added a single-capture guard and verified the final overview includes all six plots.
4. Post-fix combined comparison: no remaining actionable P0/P1/P2 findings. Header, left sample panel, loaded summary, six-chart grid and chart/table splitter follow the selected hierarchy. Table presentation starts with local time and the six measurements.

## Required fidelity surfaces

- Typography: system sans-serif in Qt and Plotly, clear title/section/control hierarchy, wrapping dataset timezone and coverage. Native rasterization and control weights differ slightly from the generated concept (P3).
- Layout: 258-pixel scrollable sidebar; right workspace with a two-thirds chart region and one-third table region. Minimum-size regression passed. Table overflow is deliberately horizontally scrollable so auxiliary metadata stays available.
- Colors: white chart/header surfaces, slate text, pale blue sidebar/table, teal primary action and mint demo badge. Disabled demo controls remain legible.
- Assets: existing original waveform icon reused, no generated replacement. Standard Qt action icons retain native platform appearance. The actual plots are data-driven Plotly output, not images from the concept.
- Copy/content: fixed fictional sample, explicit synthetic badge, accurate worker-produced counts/coverage, inferred-interval caveat. CSV column names and chronological export order stay unchanged.

## Expected implementation differences

- Separate existing date and time widgets remain usable in live mode; the concept visually combined them.
- A single Plotly toolbar controls the linked subplot figure. The concept's six separate toolbars were not existing functionality.
- Actual synthetic curves are preserved rather than copying the approximate concept curves. Existing reference ranges remain in the figure with muted styling.
- Native Qt dialog/control icons replace the concept's illustrative toolbar icons; no extra icon dependency is introduced.

## Verification

74 automated tests passed, including real Qt tests for minimum-size layout, automatic demo loading, timezone changes, typed sorting, export provenance, failed/empty subsequent requests and responsive shutdown. Ruff, compileall, shell syntax and whitespace checks passed. Launcher smoke selected the checkout's virtual environment and loaded the demo. Screenshot workflow exported 72 synthetic CSV rows. Recording workflow verified chart zoom, sorting and owned export/success dialogs; FFprobe confirmed 30 seconds, H.264, 1280 × 960, yuv420p. Publication-file secret scan: zero candidates; historical numeric identifier comparison: zero matching outgoing files. No live API verification is claimed.

## Follow-up polish

P3: platform font rasterization and standard Qt icon appearance can differ on Windows/Linux. Native Windows/macOS/Linux visual parity has not been exhaustively checked.

## Normal-range follow-up

Restored visible green normal-range areas and dotted lower/upper boundaries in all
six charts, with the existing bounds unchanged. Plotly had silently skipped shapes
added before their subplot traces. A regression now checks all six rectangles,
twelve boundary lines and their subplot references. The updated actual-widget
screenshot was opened and visually checked: green regions and bounds are visible
behind all six traces. Screenshot automation now waits for Plotly's full layout,
rather than treating the initial placeholder page load as a rendered chart.

Recording startup now waits for an actual six-trace Plotly layout, allowing variable desktop rendering time while keeping the output at 30 seconds. The refreshed recording completed chart zoom, sorting and CSV export verification.
