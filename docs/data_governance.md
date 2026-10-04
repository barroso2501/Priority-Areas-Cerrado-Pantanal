# Data-governance lessons for the next revision cycle

Findings from reconciling the 2nd-update sources (see [findings](findings.md)). Each finding is paired with a recommendation for MMA's new cycle. Findings are evidence; recommendations are the project's proposals.

| # | Finding [E] | Consequence | Recommendation |
|---|---|---|---|
| G1 | The WWF/MMA (2015) report labels biological importance as "priority" (Annex I and text) | Two official documents disagree on the class of every area | Publish one authoritative attribute table; derive every report from it |
| G2 | 22 of 300 areas have no fact sheet; 16 of them touch hybrid areas | Areas edited after the workshop lose their documentation | Regenerate the documentation after any geometric edit |
| G3 | 6 areas from the workshop list are absent from the official layer, absorbed into hybrids without traceable codes | The history of an area cannot be followed | Keep a lineage table (old code → new code(s), operation, date) |
| G4 | Hybrid areas carry no reference to their area(s) of origin | Classes and actions cannot be traced back | Add origin codes to hybrids |
| G5 | No stable identifier across cycles (Ce### in 2006; 1–300 in 2012) | Areas cannot be compared across cycles except geometrically | Adopt persistent IDs with explicit split/merge rules |
| G6 | The official biome limit changed (IBGE 2004 → 2019) between cycles | Area statistics and data queries differ by limit | Record the limit used in each cycle; never clip historical analyses by the current limit |
| G7 | Inputs of the selection (planning units, cost surface, Marxan outputs, goals table) are not published as data | The selection cannot be reproduced or re-evaluated | Publish all inputs and outputs of the prioritization with the final layer |
| G8 | Target lists are historical (2011–2012 threat and endemism lists) | Reuse may be mistaken for the current threat status | Date-stamp target lists and their sources |
| G9 | Class labels are spelled inconsistently in the official layers ("Muita Alta" in areas 203 and 30, "Muito alta"; hybrids use "Extremamente alta") | Filters and counts by class silently split or drop areas | Use controlled vocabularies (coded domains) for importance, priority and action fields |
