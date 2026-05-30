---
date: 2026-05-30
dispatch: COPY BLOCK VALIDATION-OF-PIF-01
type: read-only recon (schema read)
status: complete — blocking finding
chat-name: VALIDATION-OF-PIF
relates-to: PIF-Trigamma Validation & Constraint Model scope (§7)
---

# VALIDATION-OF-PIF-01 — Schema Read

Read-only recon answering the six schema questions in §7 of the
*PIF-Trigamma Validation & Constraint Model* scope. The read determines
whether the constraint layers are **additions** to an existing grammar,
**structural extensions** of it, or something else.

## Scope of the read

- Repository: `cwodennissmith-beep/pif-dxf-adjuster` (the only repo in scope;
  access is restricted to it).
- Files read in full: `pif_dxf_adjuster.py`, `app.py`, `test_suite.py`,
  `requirements.txt`, `.streamlit/config.toml`.
- Commit: `aae909c` on `main`.

## Headline finding (blocking)

**There is no PIF-Trigamma grammar in this repository.**

In this codebase, "PIF" expands to **Parametric Interaction Framework**, and the
program it names is a **DXF material-thickness adjuster** — a tool that scans a
single DXF file's modelspace and rescales geometry whose size matches a *nominal*
material thickness to an *actual* thickness. Concretely it does three things:

1. **Line pairs** — finds parallel `LINE` pairs whose gap ≈ design thickness and
   shifts one line so the gap becomes the actual thickness (slots / dados).
2. **Rectangular `LWPOLYLINE`s** — finds a 4-point closed rectangle with an edge
   ≈ design thickness and resizes that dimension (tabs).
3. **`CIRCLE` / `ARC`** — finds radius ≈ design thickness / 2 and rescales it
   (relief cuts).

The entire data model is:
- `COMMON_THICKNESSES`: a flat `dict[str, float]` of label → inches.
- `LogEntry` / `AdjustmentLog`: reporting structures (entity_type, layer,
  description, original_value, new_value + counters).
- Otherwise it operates directly on raw `ezdxf` entities.

There is **no part vocabulary, no primitives, no modifiers, no object/assembly
model, and no reference tables.** There is nothing for the six validation layers
to attach to.

## Answers to the six §7 questions

| # | Question | Answer | Detail |
|---|----------|--------|--------|
| 1 | Interior vs. outer dimensions stored? | **N/A** | No "cabinet", "part", "depth", or "opening" concept exists. The tool measures geometric quantities (parallel-line gap, polyline edge length, circle radius) at runtime and discards them. No stored dimension model of any kind — interior *or* outer. |
| 2 | Named, summable gaps? | **No** | Gaps are detected geometrically (`_parallel_line_distance`) and never stored. No component/gap data structure exists. Conservation (Layer 2) has nothing to close over. |
| 3 | Assembly / grouping ("used together")? | **No** | No object model and no notion of objects used together. The unit of work is one DXF file's modelspace, treated as a flat bag of entities. No groups, no sets. The ergonomic chain (Layer 4) has no inputs. |
| 4 | Derived fields (computed from sibling fields)? | **No** | The only computed values are transient geometry calcs used immediately and thrown away. There are no part fields at all, so no stored-vs-derived distinction exists. |
| 5 | Arbitrary named modifiers / features? | **No** | No part with a field set, fixed or extensible. Closest structures are `LogEntry` / `AdjustmentLog`, which exist only for reporting. |
| 6 | Material *type* (stick vs. sheet)? | **No** | Material is a **scalar thickness in inches** only (`design_thickness`, `actual_thickness`, `COMMON_THICKNESSES`). No type attribute, no stock table, no discrete-vs-continuous distinction. Layer 6 has no input to read. |

## Consequence

§7 states: "If 4, 5, or 6 is 'no,' that is a structural schema extension, not a
constraint addition." Here the answer is stronger: **1, 2, 3, 4, 5, and 6 are all
"no" / N/A.** There is no grammar to extend. Adding the six-layer model to *this*
repository is not a constraint addition and not even a schema extension — it is
**building the grammar from zero.**

The §1 "hybrid migrate" framing (old model → new model) is also moot against this
codebase: there is no prior furniture/cabinet model here to migrate from. If this
repo is the intended home, the framing decision is a **new-project ECP**, not a
migration.

## Relevant connection (not a finding, but worth noting)

The adjuster already does the *mechanical* part of Layer 6 (snapping a feature to a
thickness), but it does so **blindly**: it treats every material as continuously
adjustable and will happily rescale a slot to a non-stock thickness on a sheet good.
That is precisely the failure Layer 6 (material discretization / NOT-SOURCEABLE) is
meant to prevent. If a PIF-Trigamma grammar is built elsewhere, this tool is a
natural *consumer* of a Layer-6 decision (it executes the thickness change once the
grammar has decided the thickness is legal), not a place to host the grammar itself.

## Where does PIF-Trigamma actually live? (driver decision)

The schema read cannot proceed further until this is resolved. Three possibilities:

- **(a) Different repo/project.** The grammar lives somewhere not accessible from
  here (scope is restricted to `pif-dxf-adjuster`). → Re-point the recon at that repo.
- **(b) Greenfield here.** This repo is the intended home and the grammar is to be
  built from scratch. → New-project ECP + `/docs/decisions/` entry; the six layers
  become the initial spec, not validation bolted onto existing parts.
- **(c) Consumer relationship.** The DXF adjuster is meant to be *driven by* a
  future PIF-Trigamma (e.g. as the Layer-6 thickness executor), with the grammar
  authored separately.

**Recommendation:** do not scaffold the validation framework against this codebase
until the driver confirms which of (a)/(b)/(c) holds. The adjuster shares only a
*name* with PIF-Trigamma; folding a furniture grammar into a DXF rescaler would be an
architecture mistake.
