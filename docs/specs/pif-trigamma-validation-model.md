---
date: 2026-05-30
topic: PIF-Trigamma Validation & Constraint Model
status: scope-draft
chat-name: VALIDATION-OF-PIF
tags: [piftrigamma, validation, constraints, slot-grammar, furniture, ergonomics, material]
schema-read: docs/decisions/VALIDATION-OF-PIF-01-schema-read.md
---

# PIF-Trigamma Validation & Constraint Model — Scope

> **In-repo note (2026-05-30).** This is the canonical KB copy of the model,
> captured from the dispatch text. (The driver's locally-saved
> `pif-trigamma-validation-model.md` did not reach this ephemeral container —
> there is no `Downloads` folder or zip here — so the content was reconstructed
> from the dispatch and placed at the expected `/docs/specs/` path.)
> The schema read it depends on (§7) has been performed against this
> repository — see `docs/decisions/VALIDATION-OF-PIF-01-schema-read.md`. Its
> blocking finding: **this repo contains no PIF-Trigamma grammar.** "PIF" here is
> the *Parametric Interaction Framework* DXF material-thickness adjuster, which
> has no part vocabulary, object model, or reference tables. The model below is
> therefore captured for the record and is **not yet implemented anywhere in this
> codebase**; whether/where it gets built is a pending driver decision (§8 + the
> "where does the grammar live" question in the schema-read report).

**Purpose.** Define the validation and constraint framework PIF-Trigamma needs so
that generated plans are physically buildable, internally complete,
standards-aware, ergonomically sound, professionally formed, and sourceable from
real stock. Numeric ranges marked *(verify)* are placeholders pending sourcing.

---

## 1. Framing decision (pending driver approval)

**Old mental model.** Add validation constraints to PIF-Trigamma for cabinet parts
(drawer / slide / face-frame relationships).

**New mental model.** PIF-Trigamma is a *general furniture/project definition
language*: a small set of primitives that compose (via modifiers) into any
buildable thing — cabinets, chairs, tables, and future project types. The
validation layers below are universal; they apply to every project type.

**Recommendation: hybrid migrate.** Design the layers and the primitive+modifier
vocabulary as universal from the start, but prove them on the cabinet case first.
Cabinet validation becomes the first *instance* of the general system, not a
separate thing. Chair/table/furniture follow as additional vocabularies on the
same foundation.

**If accepted:** file a META-project ECP (old model → new model, date, trigger)
and a `/docs/decisions/` entry.

> Schema-read caveat: against *this* repo there is no prior model to migrate from,
> so "hybrid migrate" reduces to a new-project ECP if this repo is the home.

---

## 2. Severity tiers

Every check emits a finding at one of these levels. Nothing silently passes or
silently fails.

| Tier | Meaning | Behavior |
|------|---------|----------|
| **HARD** | Physically impossible | Blocks the build. Cannot proceed. |
| **SOFT** | Functional but degraded | Warns, proceeds. |
| **ADVISORY** | Buildable but non-standard | Notifies, requires acknowledged override, records it. |
| **NOT-SOURCEABLE** | Buildable in geometry, but no real stock exists | Blocks unless user declares a non-standard source (recorded). |

**Override ledger.** SOFT, ADVISORY, and NOT-SOURCEABLE overrides attach a record
to the plan itself: the value chosen, the standard/limit it departed from, and the
fact of user acknowledgment. The ledger travels *with the plan* (recommended; an
external audit log may mirror it).

---

## 3. The six validation layers

### Layer 1 — Relational constraints
Pairwise relationships between two parts within one object. Tiered HARD/SOFT.

### Layer 2 — Conservation (closure) checks
All components on one axis of one object must sum to that object's total dimension,
with **no unaccounted gap and no overlap**. Every fraction of an inch is assigned
to a named component or a named gap. Runs per axis: X (width), Y (depth),
Z (height). Requires gaps/reveals to be **named, summable entities**.

### Layer 3 — Standards / advisory checks
Single value compared against the **Standards Table**. Out of band → ADVISORY +
recorded override. One shared table; no optimizer carries its own private notion
of "standard."

### Layer 4 — Anthropometric checks
Values reconciled against the **Anthropometric Table**. Includes the
**assembly/ergonomic chain**: values spanning *multiple objects* reconciled
against a human dimension at the point of use (e.g., table + chair + sitter).
ADVISORY.

### Layer 5 — Form / craft knowledge
The named geometric features of a well-built part, with accepted ranges and the
relationships between them. Vocabulary is well-established; numeric ranges seed
from published sources, override with SC house values.

### Layer 6 — Material availability / discretization
What the material can *physically be*. Reads the part's **material type** against
the **Stock/Material Table**.
- **Stick / solid lumber:** thickness continuous (plane to any value within stock).
- **Sheet goods (plywood, MDF, melamine, particleboard):** thickness **discrete**,
  snapped to manufactured stock. Cannot be planed to a custom thickness.
  Off-stock thickness on a sheet good → NOT-SOURCEABLE.

---

## 4. Shared reference tables

Three tables, consulted by all option generators and the manual designer. A value
can be standard-but-uncomfortable, or non-standard-but-ergonomic, or
geometrically-fine-but-not-sourceable — hence kept separate.

### 4.1 Standards Table — "what the industry conventionally builds"
Each entry: name, standard value/band, axis. Candidates *(verify)*:
- Counter height ~36" (base), ~34.5" to deck
- Counter depth ~24"–25.5"
- Toe-kick height ~3.5"–4.5", depth ~3"
- Seat height (adult) ~17"–19"
- Standard drawer-face gaps / reveals
- Upper-cabinet height above counter ~18"
- Standard cabinet depths: 12" upper, 24" base

### 4.2 Anthropometric Table — "what the body requires"
Each entry: name, body-derived value/band, axis. Candidates *(verify)*:
- Seated thigh clearance (seat top to underside of table/apron) ~7"–9" min
- Seated work-surface differential (chair-to-table) ~10"–12"
- Standing work height (counter), elbow-relative ~36"
- Seat height (adult) ~17"–19"
- Knee-to-toe clearance depth under a table
- Reach height to uppers/shelves
- Standing toe/knee clearance at toe-kick

### 4.3 Stock / Material Table — "what stock actually exists"
Each entry: material name, type (stick | sheet). If sheet, available thicknesses
with nominal-vs-actual where it matters (e.g., nominal 3/4" plywood ≈ 23/32").
Primary consumer: the material optimizer.

---

## 5. Cabinet constraint set (first instance — the live need)

### Depth chain (Y)
1. **Drawer depth ≤ cabinet interior depth.** HARD. Interior, after back panel +
   rear clearance.
2. **Slide length ≈ drawer depth.** SOFT. Tolerance band; outside band warns.
3. **Slide length ≤ cabinet interior depth − rear clearance.** HARD. Rule of
   thumb: slide length = cabinet depth − 2" *(verify per slide type)*.

### Width chain (X)
1. **Drawer box width ≤ opening width − (2 × side clearance).** HARD. Side-mount
   ~1/2" total, undermount ~3/16"–5/16" total *(verify)*.
2. **Face frame clear opening ≥ drawer box width + slide clearance.** HARD.
3. **Face frame setback ≤ slide front clearance.** HARD (face-frame cabinets).

### Height chain (Z)
1. **Drawer box height ≤ opening height − slide vertical clearance.** HARD.
   Undermount ≥3/4" reduction, side-mount ≥1/4" *(verify)*.

### Structural / cross-cutting
1. **Slide type compatible with cabinet construction** (face-frame vs frameless).
2. **Slide weight capacity ≥ expected load.** SOFT. *(Candidate to defer.)*
3. **Drawer stack: cumulative heights + reveals ≤ opening height.** HARD (if
   grammar allows stacks).

---

## 6. Chair geometry (form/craft + ergonomic, second instance)

### 6.1 Dining-chair part vocabulary
- **Seat assembly** — seat (plank or frame); features: saddle/dish, slope/pitch,
  waterfall front edge.
- **Front legs** / **rear legs** (rear legs typically continue up as back posts).
  Each leg: rake, splay, length; derived: resultant (bore angle), sightline.
- **Back assembly** — back posts/stiles, crest rail, lumbar rail/splat; back rake,
  back splay, lumbar curve.
- **Stretchers** — side, front/back, or H-stretcher; height off floor.
- **Aprons/rails** — front/back/side (if seat is frame-built).

### 6.2 Form-feature terms (layer 5 vocabulary)
- **Saddling / dishing** — carved hollow that cups the body.
- **Waterfall front edge** — rounded front edge relieving pressure behind knees.
- **Seat slope / pitch** — slight backward tilt.
- **Rake** — leg angle from the side. **Splay** — leg angle from the front
  (outward; never inward).
- **Resultant angle** — function of rake AND splay; angle to bore the mortise.
- **Sightline angle** — function of rake AND splay; layout angle.
  *Identity: if rake = splay, sightline = 45°.*
- **Back rake** — recline from vertical. **Lumbar curve** — forward bulge.

### 6.3 Leg splay — the real relationship (NOT a height ratio)
There is **no published height-to-splay ratio.** Splay is governed by **footprint
vs. force**, not height:
- Splay exists so a leaning sitter's force line still lands **inside the footprint
  of the feet**.
- Same angles do not produce the same footprint at different heights — leg length
  and angle trade off. *This is why no fixed degrees-per-inch rule can exist.*
- Professional workflow is the inverse of "height → angle": pick a target
  foot-landing footprint, then work back through leg length to get
  rake/splay/resultant/sightline.

**Encode as (advisory), not a ratio:**
- Inputs: seat height (Z), target foot footprint (X/Y), leg length.
- Derived: rake, splay → resultant (bore) + sightline (layout), via inverse-tangent
  trig.
- Constraint: footprint must extend beyond the seat edge enough that a leaning
  sitter's force line stays inside it; extreme-angle warning where leg-tenon
  failure becomes a risk.
- Numeric source: Drew Langsner, *The Chairmaker's Workshop*.

### 6.4 Ergonomic chain example (table + chair)
`tabletop height − apron depth − seat height = available legroom gap`. If gap <
anthropometric thigh-clearance minimum (~7"–9" *(verify)*) → ADVISORY: "this table
height forces a non-standard chair height for an adult to sit comfortably."

---

## 7. Schema questions for CC — ANSWERED

Dispatched as **COPY BLOCK VALIDATION-OF-PIF-01** (read-only recon). Full report:
`docs/decisions/VALIDATION-OF-PIF-01-schema-read.md`.

**Result against this repo: there is no grammar.** All six questions answer
"no" / N/A — the codebase is a DXF thickness adjuster with no part schema.

1. **Interior vs. outer dimensions** — N/A (no dimension model at all).
2. **Named gaps** — No (gaps detected geometrically, never stored).
3. **Assembly / grouping** — No (flat bag of DXF entities; no object model).
4. **Derived fields** — No (no part fields; transient calcs only).
5. **Modifiers / features** — No (no part with a field set).
6. **Material type** — No (material = scalar thickness in inches only).

Per §7's own rule, 4/5/6 = "no" means structural schema extension. Here 1–6 are
*all* "no," so it is stronger: building the grammar from zero, not extending one.
Recommended schema shape if/when built: **form features as composable modifiers on
base primitives** (a leg = post + rake + splay; a seat = board + saddle + slope +
waterfall).

---

## 8. Open decisions (driver)

- **Where does the grammar live?** (a) another repo, (b) greenfield here,
  (c) this adjuster as a Layer-6 consumer. *Blocks everything else — see
  schema-read report.*
- **Framing:** accept hybrid migrate (§1)? → META ECP + decision doc. (Reduces to
  new-project ECP against this repo.)
- **Slide-vs-drawer (constraint 2):** HARD-within-tolerance vs SOFT-warn.
  Recommendation: SOFT.
- **Override ledger location:** on the plan (recommended), external log, or both.
- **Anthropometric data source:** published seed (default) + SC house overrides.
- **Schema shape:** modifiers-on-primitives (recommended) vs. bespoke part types.
