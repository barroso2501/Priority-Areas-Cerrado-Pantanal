# D14 — Visual identity of the Product 1 site

**Status:** Decided 2026-10-05 (project lead): keep the current visual; the MapBiomas design system is recorded, not applied.

## Context
After a positive review by MapBiomas technical staff, two resources were suggested for the site interface:
- the MapBiomas component library (Storybook at https://ui.mapbiomas.org/), React components;
- a MapBiomas design system (claude.ai artifact shared by MapBiomas staff), with tokens and usage rules for the platform and for a separate "report / scientific document" layer.

The project lead has **authorization** to use the design system, with the credit line "Visual baseado no design system MapBiomas" and no change in authorship.

## What was tested
A CSS layer applying the design system to the Quarto site without React (`docs/design/mapbiomas_ds_layer.css`): one accent colour (#43798A), Open Sans, the "outside the platform" heading scale, KPI row without cards, 1px borders, no shadows, 12px radius on large surfaces, Badge and SearchInput styles. Data colours (categories, map classes, chart series) were kept, as the design system itself separates data colours from interface colours. No logo.

Limits of the test [L]: the README gives the role of each neutral token but not its hex values (only white and #43798A); the neutral and primary ramps were approximated from the contrast ratios stated in the README. The design-system artifact could not be read from the analysis environment (network restriction), so the component bundle was not inspected.

## Decision
The preview did not bring a gain in aesthetics or clarity over the current visual. The site keeps its current visual. The design system is recorded for a possible later adoption.

## If adopted later
1. Obtain the exact tokens (`components/bundle.css` of the design system) and replace the APPROX block of the CSS layer.
2. Copy the layer to `site/styles.css` in `build_quarto.py` and add the credit line to the footer and home page.
3. Keep the D13 category colours and the validated map palette; keep the logo out unless explicitly authorized.
4. The README of the design system is MapBiomas material: it is kept in the project knowledge base, not redistributed in this public repository.
