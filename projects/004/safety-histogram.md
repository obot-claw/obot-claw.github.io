---
layout: default
title: P004 Safety Histogram Deep Dive
permalink: /projects/004/safety-histogram.html
---

# Safety Histogram Deep Dive

> 📦 **Legacy project catalog.** Projects were superseded by Requirement issues in July 2026; this page is kept as reference. Current status lives on the [Roadmap](/roadmap/) and [Dashboard](/dashboard/).


## Why start here

Safety Histogram is a good first migration target because it is clinically useful, structurally simpler than the linked AE displays, and representative of the dependency pattern we need to replace:

- `d3` v3 for data utilities and DOM work
- `webcharts` for chart, controls, table, and small-multiple orchestration
- Rollup/Babel v1-era build tooling
- browser examples using global `d3`, `webcharts`, and the bundled renderer

The display is a distribution review for lab, vital sign, ECG, or other safety measures with optional filters, grouping, normal-range overlays, bin boundary annotation, normality tests, distribution comparison, small multiples, and click-through listings.

## Current code structure

| Area | Current files | Notes |
|---|---|---|
| Public entrypoint | `src/index.js` | Merges settings, builds Webcharts controls/chart/table, attaches callbacks, returns the Webcharts chart object. |
| Settings | `src/configuration/*`, `settings-schema.json` | Splits renderer settings from Webcharts settings, then syncs them before render. |
| Layout | `src/layout.js`, `src/styles.js` | Creates fixed containers for controls, main chart, small multiples, and listing. |
| Data lifecycle | `src/callbacks/onInit.js`, `src/callbacks/onPreprocess.js` | Cleans data, validates variables, defines measures, calculates domains/statistics/binning. |
| Rendering lifecycle | `src/callbacks/onDraw.js`, `src/callbacks/onResize.js` | Relies on Webcharts callbacks, then customizes bars, normal ranges, hover areas, listings, and small multiples. |
| Statistics | `src/util/stats/*` | Local implementations for Shapiro-Wilk and Kolmogorov-Smirnov tests. |
| Example | `test-page/*` | Loads CSV from RhoInc data-library and renders the bundled `safetyHistogram.js`. |
| Tests | `test/*` | Node scripts compare statistical test outputs to R-generated results. |

## Current dependency risks

- `webcharts` is the core rendering dependency and controls the chart lifecycle.
- `d3` v3 is old and used across utility, layout, formatting, binning, nesting, and SVG selection code.
- `npm run build` currently runs `npm audit fix`, which is unsafe for deterministic builds.
- Rollup/Babel/Prettier versions are old and should be updated only after baseline behavior is protected.
- Browser-level behavior is mostly untested.

## Migration target

A modernized renderer should expose a stable API independent of Webcharts:

```js
import { createSafetyHistogram } from '@safetygraphics/safety-histogram';

const histogram = createSafetyHistogram('#container', settings);
histogram.init(data);
histogram.setSettings(nextSettings);
histogram.setData(nextData);
histogram.destroy();
```

Internally, split into explicit modules:

- `data/prepareData.js`
- `data/validateData.js`
- `data/binData.js`
- `data/statistics.js`
- `state/createState.js`
- `controls/renderControls.js`
- `charts/renderHistogram.js`
- `charts/renderSmallMultiples.js`
- `listing/renderListing.js`
- `api/createSafetyHistogram.js`

## Chart.js feasibility

Chart.js can handle the core histogram display if we treat bins as categorical labels or a linear x scale with bar geometry. It should be evaluated for:

- histogram bars
- grouped histograms or small multiples
- normal-range overlays via plugin annotation/custom drawing
- selection/highlight behavior
- click events mapping from bar element to bin data
- responsive resize behavior

Potential issue: small multiples and custom normal-range overlays may be cleaner with a thin custom Canvas/SVG layer around Chart.js rather than forcing all behavior into Chart.js configuration.

## Proposed implementation steps

### Step 1: Baseline branch

- Update repository metadata to staging ownership.
- Add CI for install, lint/build, and current statistical tests.
- Remove `npm audit fix` from the build script.
- Add a deterministic example data fixture checked into the repo.
- Add browser smoke test infrastructure if Playwright can run in the target CI/dev environment.

### Step 2: Preserve current API with seams

- Wrap the current Webcharts renderer behind a `createSafetyHistogram()` API.
- Move settings sync and data prep into functions that can be tested without DOM/Webcharts.
- Add unit tests for data validation, measure filtering, bin calculation, normal range flags, and statistics.

### Step 3: Extract pure data/statistics layer

- Remove D3 dependencies from pure data/stat functions where practical.
- Replace `d3.nest`, `d3.set`, `d3.extent`, `d3.quantile`, and formatting helpers with modern JS or small local utilities.
- Keep statistical outputs compared against the existing R-generated references.

### Step 4: Prototype Chart.js renderer

- Render the primary histogram using Chart.js.
- Implement controls and listing without Webcharts.
- Recreate bin hover/click selection and listing behavior.
- Recreate normal range and bin boundary annotations.
- Evaluate small multiples with one Chart.js instance per group.

### Step 5: Compatibility and release path

- Keep the old API available during transition if feasible.
- Document setting differences and migration notes.
- Publish an initial prerelease from the `obot-claw` fork for review before transfer.

## Review questions for Jeremy

1. Should the first PR be only baseline maintenance/CI cleanup, or should it include the new wrapper API seam?
2. Should we preserve the legacy `safetyHistogram(element, settings).init(data)` call exactly, or allow a clean new API with a compatibility alias?
3. Should Chart.js be a hard requirement for Safety Histogram, or can we use custom SVG/Canvas for pieces where Chart.js fights the clinical display?
4. Do you want this package renamed before or after transfer to SafetyGraphics?
